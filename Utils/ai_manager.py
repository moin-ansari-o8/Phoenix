import json
import logging
import re
from typing import Optional, Dict

DEFAULT_ROUTER_MODEL = "llama3.2:latest"
DEFAULT_ANSWER_MODEL = "gemma4:e2b"


def strip_markdown(text: str, max_chars: int = 600) -> str:
    """Small models leak markdown; output is spoken aloud, so clean it."""
    if not text:
        return ""
    # Models emit typographic punctuation that a cp1252 console renders as "It?s"
    # and that some TTS voices read oddly. Normalise to ASCII.
    for bad, good in (
        ("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
        ("—", " - "), ("–", "-"), ("…", "..."), (" ", " "),
    ):
        text = text.replace(bad, good)
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_chars:
        cut = text[:max_chars]
        for sep in (". ", "! ", "? "):
            idx = cut.rfind(sep)
            if idx > max_chars * 0.5:
                return cut[: idx + 1].strip()
        return cut.rstrip() + "..."
    return text


class AIDecisionMaker:
    """Two-model AI brain.

    router_model  -> picks exactly one tool (needs tool-calling capability)
    answer_model  -> composes the final spoken reply

    NOTE: the router model MUST report the `tools` capability in `ollama show`.
    gemma3 does not, and cannot be used here.
    """

    def __init__(self, config_path: str = "core/config.json"):
        self.config_path = config_path
        self.config = self._read_config()
        self.ai_settings = self.config.get("ai_manager", {})

        self.router_model = self.ai_settings.get("router_model", DEFAULT_ROUTER_MODEL)
        self.answer_model = self.ai_settings.get("answer_model", DEFAULT_ANSWER_MODEL)
        # "json"  -> rules-driven classification, works with any model (gemma3)
        # "tools" -> native function-calling, needs a tools-capable model
        self.router_mode = self.ai_settings.get("router_mode", "json")

        self._router_helper = None
        self._answer_helper = None

    def _read_config(self) -> dict:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return {}

    # ---- model handles (cached so both models stay resident) ----------------

    def _get_router(self):
        from Utils.limbs.ollama_helper import OllamaHelper

        if self._router_helper is None:
            self._router_helper = OllamaHelper(model=self.router_model)
        return self._router_helper

    def _get_answer(self):
        from Utils.limbs.ollama_helper import OllamaHelper

        if self._answer_helper is None:
            self._answer_helper = OllamaHelper(model=self.answer_model)
        return self._answer_helper

    # ---- stage 1: tool selection -------------------------------------------

    def choose_tool(self, query: str, soul: str, context: str, memory: str) -> Dict:
        """Pick one tool. Dispatches on router_mode:

        "json"  -> rules-driven JSON classification from core/intents.md.
                   Works with ANY completion model, including gemma3, which
                   has no native tool-calling but is much faster.
        "tools" -> native Ollama function-calling (needs a tools-capable model).
        """
        if self.router_mode == "json":
            return self._choose_tool_json(query, soul, context, memory)
        return self._choose_tool_native(query, soul, context, memory)

    def _choose_tool_json(self, query: str, soul: str, context: str, memory: str) -> Dict:
        """Rules-driven routing. The rulebook lives in core/intents.md so it can
        be tuned without touching code."""
        from core.config import AppConfig
        from Utils.limbs.memory_manager import load_intent_rules
        from Utils.limbs.tool_registry import normalize_json_choice

        # Keep this prompt SHORT. Latency here is dominated by prompt length,
        # not by the model: 7.1k chars -> ~13s, 600 chars -> ~1.5-3s, and the
        # short version routes more accurately. Only the last conversation turn
        # is included, and user memory is deliberately left out -- the router
        # only needs to know a fact EXISTS, which the rules already state.
        rules = load_intent_rules(compact=True)
        prompt = (
            f"{rules}\n\nI am {AppConfig.name}. The user is {AppConfig.user_name}.\n"
            f'\nMessage: "{query}"\nJSON:'
        )
        # Conversation history is deliberately NOT included here. When it was,
        # "my friend moin told me about this" resolved "this" to the previous
        # topic (OpenAI) and routed to a lookup instead of remember. The tool
        # depends on the CURRENT message only; the answer model still gets the
        # history, which is where it is actually needed for follow-ups.

        raw = self._get_router()._call_ollama(prompt, format_json=True)

        if isinstance(raw, dict) and "error" in raw and "tool" not in raw:
            err = str(raw.get("error", ""))
            # Only a genuinely unreachable model warrants telling the user so.
            # Malformed JSON just means this one reply was garbage -- degrade to
            # a normal spoken answer instead of claiming an outage.
            if "Connection error" in err or "Ollama API error" in err:
                return {"name": "error", "args": {}, "error": err}
            logging.warning(f"[ai_manager] unusable router reply: {err}")
            return {"name": "answer_directly", "args": {}}
        if not isinstance(raw, dict):
            return {"name": "answer_directly", "args": {}}

        return normalize_json_choice(raw, query)

    def _choose_tool_native(self, query: str, soul: str, context: str, memory: str) -> Dict:
        """Native Ollama tool-calling. Requires a model with `tools` capability."""
        from core.config import AppConfig
        from Utils.limbs.tool_registry import TOOL_SCHEMAS, VALID_TOOL_NAMES

        system = (
            f"{soul}\n\n"
            "You are the router. Decide which single tool handles the user's message.\n"
            "Rules:\n"
            "- If the answer depends on THIS PC right now (clock, date, battery, local\n"
            "  weather, the user's timers/alarms/reminders/songs) use get_device_state,\n"
            "  even when the message is phrased as a question.\n"
            "- control_device is ONLY for an explicit instruction to change something.\n"
            "  Never use it to answer a question.\n"
            "- Questions about YOURSELF or about THE USER use answer_directly. That\n"
            "  information is in your identity and memory above. NEVER search the web\n"
            "  for who you are, who made you, or who the user is.\n"
            "- lookup_encyclopedia is ONLY for famous public entities with a Wikipedia\n"
            "  article. Never for the user's own friends, family or preferences.\n"
            "- Use search_web for news, prices, or anything recent you cannot be sure of.\n"
            "- If the user STATES a personal fact rather than asking something, use\n"
            "  remember.\n"
            "- If the user asks what a word or concept MEANS, that is answer_directly,\n"
            "  not a device reading and not an encyclopedia lookup.\n"
            "\nWorked examples:\n"
            "  'what is the time' -> get_device_state(time)\n"
            "  'how much battery do i have' -> get_device_state(battery)\n"
            "  'open brave' -> control_device(open, brave)\n"
            "  'set volume to 40' -> control_device(adjustVolume)\n"
            "  'who is salman khan' -> lookup_encyclopedia(Salman Khan)\n"
            "  'what is openai' -> lookup_encyclopedia(OpenAI)\n"
            "  'latest news about isro' -> search_web\n"
            "  'what do you mean by time' -> answer_directly\n"
            "  'tell me the capital of france' -> lookup_encyclopedia(Paris)\n"
            "    (a 'tell me ...' phrasing does NOT make it a device reading)\n"
            "  'what is artificial intelligence' -> answer_directly\n"
            "  'who is my friend' -> answer_directly (it is in your memory)\n"
            "  'who are you' / 'who am i' -> answer_directly\n"
            "  'my friend moin told me about this' -> remember(People, "
            "'Moin is a friend of the user')\n"
            "  'i prefer dark mode' -> remember(Preferences, "
            "'The user prefers dark mode')\n"
            f"\nYour identity: you are {AppConfig.name}. "
            f"The user is {AppConfig.user_name}.\n"
            f"\nWhat you already know about the user:\n{memory}"
        )
        user = (f"Recent conversation:\n{context}\n\n" if context else "") + (
            f"Message: {query}"
        )

        msg = self._get_router().chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            tools=TOOL_SCHEMAS,
            temperature=0.0,
        )

        if isinstance(msg, dict) and "error" in msg:
            return {"name": "error", "args": {}, "error": msg["error"]}

        calls = (msg or {}).get("tool_calls") or []
        if calls:
            fn = (calls[0] or {}).get("function", {}) or {}
            name = fn.get("name")
            raw_args = fn.get("arguments", {})
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except Exception:
                    raw_args = {}
            if name in VALID_TOOL_NAMES:
                return {"name": name, "args": raw_args or {}}
            logging.warning(f"[ai_manager] router returned unknown tool: {name!r}")

        return {"name": "answer_directly", "args": {}}

    # ---- stage 2: answer composition ---------------------------------------

    def compose_answer(
        self,
        query: str,
        soul: str,
        context: str,
        memory: str,
        evidence: Optional[str] = None,
    ) -> str:
        """Compose the final spoken reply with the answer model."""
        system = f"{soul}\n\nWhat you already know about the user:\n{memory}"

        # Prompt length is the dominant latency cost here (~1.85ms/char measured
        # on this machine), so keep every piece tight: last turn only, and
        # evidence hard-capped regardless of what the caller passed in.
        user = ""
        if context:
            # Labelled as background and explicitly de-prioritised: without this
            # the model answered the PREVIOUS topic instead of the new message.
            user += (
                "Earlier in this conversation (background only, do not answer "
                "this):\n"
                + "\n".join(context.strip().splitlines()[-2:])
                + "\n\n"
            )
        if evidence:
            user += (
                f"Facts:\n{evidence[:900]}\n\n"
                "Use only these facts. If they lack the answer, say so.\n\n"
            )
        else:
            # Without this, "tell me more" about a friend produced invented
            # biography ("often drops by for gaming sessions, brings snacks").
            # Fabricating personal details is worse than admitting ignorance.
            user += (
                "You have no looked-up information for this. Answer only from "
                "what you genuinely know or were told above. NEVER invent "
                "details about the user or people they know - if you do not "
                "know, say so plainly.\n\n"
            )
        user += (
            f"Answer ONLY this message: {query}\n\n"
            "Answer in 1-2 short spoken sentences."
        )

        msg = self._get_answer().chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
            num_predict=110,
        )

        if isinstance(msg, dict) and "error" in msg:
            return f"Error: {msg['error']}"
        return strip_markdown((msg or {}).get("content", ""))

    # ---- legacy surface (kept for backwards compatibility) -----------------

    def get_active_model(self) -> Dict[str, str]:
        mode = self.ai_settings.get("current_mode", "local")
        models = self.ai_settings.get(
            "local" if mode == "local" else "online", {}
        )
        active_model = next((n for n, on in models.items() if on), None)
        return {"mode": mode, "model_name": active_model}

    def generate_response(self, prompt: str, context: Optional[str] = None) -> str:
        """Plain single-model completion. Retained for callers that predate
        the router/answer split."""
        model_info = self.get_active_model()
        if not model_info["model_name"]:
            return "Error: No active AI model selected in config."
        if model_info["mode"] == "online":
            return self._query_online(prompt, model_info["model_name"], context)

        from Utils.limbs.memory_manager import load_soul

        return self.compose_answer(prompt, load_soul(), context or "", "")

    def _query_online(
        self, prompt: str, model_name: str, context: Optional[str]
    ) -> str:
        logging.info(f"Querying ONLINE Model: {model_name}")
        return f"[Simulated Online Response using {model_name}]: I understand."
