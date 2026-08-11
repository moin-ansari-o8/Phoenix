import json
import logging
import os
import re
from typing import Optional, Dict

# Repo root, so config lookup does not depend on the cwd of whichever
# subprocess constructed this. See AIDecisionMaker.__init__.
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Fallbacks used only when config.json is unreadable. They must be models that
# actually FIT: this box has 4 GB of VRAM, and the previous answer-model default
# ("gemma4:e2b", 7.2 GB) could not be resident, so the failure mode of a missing
# config was an 8-16 s per-turn CPU fallback rather than a visible error.
DEFAULT_ROUTER_MODEL = "llama3.2:latest"
DEFAULT_ANSWER_MODEL = "llama3.2:latest"


def strip_markdown(text: str, max_chars: int = 900) -> str:
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


_REPEAT_PATTERNS = (
    r"\bcome again\b",
    r"\bsay (that|it) again\b",
    r"\brepeat( that| it| again)?\b",
    r"\b(that|it|this) again\b",
    r"\bagain please\b",
    r"\b(couldn'?t|could not|didn'?t|did not) (hear|catch|get) (that|you|it)\b",
    r"\bone more time\b",
    r"\bwhat was that\b",
    r"\bpardon\b",
    r"\bcome back to that\b",
    r"\b\w+ again\b",  # "tell me PCA again", "explain again"
)


def _repeat_target(query: str, context: str) -> Optional[str]:
    """If the user asked to hear the last answer again, return that answer.

    "come again" used to get "I think we already discussed PCA" -- a deflection.
    Detecting the request deterministically and handing the model the exact text
    to restate is more reliable than hoping it infers the intent.
    """
    if not query or not context:
        return None
    low = query.strip().lower()
    if len(low.split()) > 10:  # a long message is a new question, not "again"
        return None
    if not any(re.search(p, low) for p in _REPEAT_PATTERNS):
        return None

    for line in reversed(context.strip().splitlines()):
        if ":" in line:
            speaker, _, said = line.partition(":")
            said = said.strip()
            # Skip the user's own lines and any prior deflection.
            if speaker.strip().lower() in ("you", "user"):
                continue
            if said and len(said) > 25 and "already discussed" not in said.lower():
                return said
    return None


# The answer model's escape hatch. It is a bare sentinel rather than a phrase so
# it can be detected exactly: any instruction of the form "say you don't know"
# produces a different sentence every time, and half of those sentences are a
# hedge wrapped around a guess. A token either appears or it does not.
UNKNOWN_SENTINEL = "UNKNOWN"

_UNKNOWN_RE = re.compile(r"^\W*unknown\b\W*$", re.IGNORECASE)

# Phrases that reliably precede a fabricated answer. A model that genuinely
# knows something states it; these are the tells of one talking its way toward a
# guess. Treated exactly like the sentinel, because a hedged answer IS a
# non-answer -- the hedge is the model telling us so in its own words.
_HEDGE_PATTERNS = (
    r"\bas of my (last |latest )?(update|training|knowledge)",
    r"\bmy (training|knowledge) (data |cut-?off )?(only )?(goes|extends|includes)",
    r"\bi (don'?t|do not) have (access to|real-?time|current|up-?to-?date)",
    r"\bi (can'?t|cannot) (browse|access the internet|look that up)",
    r"\bi'?m not (entirely |completely |totally )?(sure|certain)\b",
    r"\bi (may|might|could) be (wrong|mistaken|inaccurate)",
    r"\bi (don'?t|do not) have (that|this|any) (information|data|details)",
    r"\bwithout more (context|information)",
)
_HEDGE_RE = re.compile("|".join(_HEDGE_PATTERNS), re.IGNORECASE)


def is_unknown(text: str) -> bool:
    """True when the answer model declined, explicitly or by hedging."""
    if not text:
        return True
    stripped = text.strip()
    if _UNKNOWN_RE.match(stripped):
        return True
    # The sentinel leading a longer reply still counts: small models like to
    # emit "UNKNOWN. But I think it might be..." which is exactly the guess the
    # sentinel exists to suppress.
    if stripped.upper().startswith(UNKNOWN_SENTINEL):
        return True
    return bool(_HEDGE_RE.search(stripped))


class AIDecisionMaker:
    """Two-model AI brain.

    router_model  -> picks exactly one tool (needs tool-calling capability)
    answer_model  -> composes the final spoken reply

    NOTE: the router model MUST report the `tools` capability in `ollama show`.
    gemma3 does not, and cannot be used here.
    """

    def __init__(self, config_path: str = None):
        # Resolved against this file, not the cwd. The default used to be the
        # relative "core/config.json", which is only correct when Phoenix is
        # launched from the repo root. The listener and processor are spawned
        # with an inherited cwd that happens to be right today - and when it is
        # not, _read_config() swallows the error and returns {}, so every model
        # name silently falls back to the DEFAULT_* constants below. That is a
        # silent 10x latency regression, not a crash, so nothing would surface it.
        self.config_path = config_path or os.path.join(_BASE, "core", "config.json")
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
            # Loud, because the consequence is silent: falling back to the
            # DEFAULT_* models looks like Phoenix working, just slower and
            # answering from a different brain than the one configured.
            logging.error(
                "Failed to load config at %s (%s). Falling back to router=%s "
                "answer=%s - this is NOT the configured model.",
                self.config_path,
                e,
                DEFAULT_ROUTER_MODEL,
                DEFAULT_ANSWER_MODEL,
            )
            print(
                f"\n[WARN] ai_manager could not read {self.config_path}; "
                f"using fallback models",
                flush=True,
            )
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

        # temperature=0 makes classification deterministic. Without it Ollama
        # defaults to 0.8 and the same query routed differently between runs.
        raw = self._get_router()._call_ollama(
            prompt, format_json=True, temperature=0, num_predict=60
        )

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
        repeat_of = _repeat_target(query, context)

        user = ""
        if context:
            # Use the history to resolve references, but answer the NEW message.
            # An earlier version said "background only, do not answer this",
            # which made "come again" reply "we already discussed that" instead
            # of repeating -- too strong.
            user += (
                "Recent conversation, for resolving references like 'it', "
                "'that' or 'again':\n"
                + "\n".join(context.strip().splitlines()[-4:])
                + "\n\n"
            )
        # Both branches share one contract: there is always a way to decline, and
        # it is always the same token. Instructions phrased as "say you don't
        # know" produce a different sentence each time and are impossible to act
        # on; a sentinel is detectable, so the caller can escalate to a web
        # search instead of speaking a shrug.
        if evidence:
            user += (
                f"Facts:\n{evidence[:900]}\n\n"
                "Use only these facts. If they do not contain the answer, reply "
                f"with exactly {UNKNOWN_SENTINEL} and nothing else.\n\n"
            )
        else:
            # Narrowed to PERSONAL details, which is the case that actually
            # fabricated ("often drops by for gaming sessions, brings snacks").
            # A blanket "say you don't know" made it deflect on ordinary topics,
            # so the sentinel is scoped to genuine uncertainty and the personal
            # guard is kept separate and absolute.
            user += (
                "Answer from your own knowledge. Never invent personal details "
                "about the user or people they know - for those, say plainly "
                "that you were not told.\n"
                f"If you are not confident the answer is correct, reply with "
                f"exactly {UNKNOWN_SENTINEL} and nothing else. A wrong answer is "
                "worse than no answer. Do not guess, and do not hedge - answer "
                f"plainly or reply {UNKNOWN_SENTINEL}.\n\n"
            )

        if repeat_of:
            # Deterministic: the user asked to hear it again. Restating is the
            # whole request, so never respond that it was already covered.
            user += (
                f"The user is asking you to say this again:\n\"{repeat_of}\"\n\n"
                "Repeat that answer in full, rephrased more clearly. Do NOT say "
                "you already answered it, and do not shorten it to a summary.\n\n"
                f"Their exact words: {query}\n\n"
                "Reply in 1-3 short spoken sentences."
            )
        else:
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
            # 110 truncated "teach me ..." answers mid-sentence. Capping
            # generation barely affected latency anyway (that is prompt-bound),
            # so there is little reason to keep it tight.
            num_predict=220,
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
