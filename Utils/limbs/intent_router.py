"""Two-stage intent router for Phoenix.

STAGE 0 - exact-match alias lookup. O(1) dictionary, no similarity scoring, no
          thresholds, no question-word prefix rules. A miss is a miss, so a
          misfire is impossible by construction. (The previous fuzzy matcher
          fired `playsong` on a 0.462 tie for "capital of france?" because a
          whitelist bypassed its own threshold. That whole mechanism is gone.)

STAGE 1 - LLM tool router. The model picks exactly one of six tools, then the
          result is either executed (device read/control) or handed to the
          answer model to compose a brief spoken reply.

The command/question distinction is deliberately NOT used for routing. A
question can legitimately need a local tool ("what is the time"). Routing is
decided by where the answer lives, and whether it mutates state.
"""

import re
from dataclasses import dataclass
from typing import Optional

from Utils.limbs import tool_registry


@dataclass
class RouteResult:
    source: str  # "fastpath" | "tool" | "ai" | "error"
    spoken: Optional[str] = None
    tag: Optional[str] = None
    tool: Optional[str] = None


def normalize(text: str) -> str:
    """Lowercase, strip punctuation and collapse spaces for alias lookup."""
    text = (text or "").lower().strip()
    text = re.sub(r"[?!.,;:]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


# --- Stage 0 -----------------------------------------------------------------
# Exact normalized utterance -> action tag. Extend freely; every entry is a
# deliberate, explicit decision rather than a fuzzy guess.

DEVICE_ALIASES = {
    "what time is it": "saytime",
    "whats the time": "saytime",
    "what is the time": "saytime",
    "tell me the time": "saytime",
    "time": "saytime",
    "what is the date": "dateday",
    "whats the date": "dateday",
    "what is today": "dateday",
    "whats today": "dateday",
    "what day is it": "dateday",
    "date": "dateday",
    "battery": "battery",
    "battery status": "battery",
    "how much battery": "battery",
    "take a screenshot": "screenshot",
    "screenshot": "screenshot",
    "volume up": "adjustVolume",
    "volume down": "adjustVolume",
    "mute": "muteSpeaker",
    "unmute": "unmuteSpeaker",
    "maximize": "maximize",
    "minimize": "minimize",
    "fullscreen": "fullscreen",
    "new tab": "newtab",
    "close tab": "closetab",
    "my alarms": "viewAlarm",
    "my timers": "viewTimer",
    "my reminders": "viewReminder",
    "my songs": "viewsongs",
}

# Identity questions never reach the internet -- they resolve from the canned
# intents in data/intents.json plus AppConfig.
IDENTITY_ALIASES = {
    "who are you": "aboutme",
    "what is your name": "aboutme",
    "whats your name": "aboutme",
    "who made you": "aboutme",
    "who created you": "aboutme",
    "who is your master": "aboutme",
    "who is your creator": "aboutme",
    "who am i": "whoiskaly",
    "what is my name": "whoiskaly",
    "whats my name": "whoiskaly",
}

EXACT_ALIASES = {**DEVICE_ALIASES, **IDENTITY_ALIASES}


# --- Stage 0b: imperative command grammar ------------------------------------
# "increase brightness by 30%" is subject + verb + number. That is a parsing
# problem, not a reasoning problem, and sending it to a model costs seconds and
# sometimes gets it wrong. This is NOT the fuzzy matching that caused the old
# misfires: it requires BOTH a control verb AND a control subject to be present,
# so it cannot fire on a question like "what do you mean by time".

_SUBJECT_TO_ACTION = (
    (("brightness", "bright", "screen light", "backlight"), "adjustBrightness"),
    (("volume", "sound", "audio", "speaker level"), "adjustVolume"),
)

# Verbs that unambiguously name their own subject, so no noun is needed:
# "dim the screen", "make it louder".
_VERB_IMPLIES_SUBJECT = (
    (("dim", "brighten"), "adjustBrightness"),
    (("louder", "quieter", "softer", "turn it up", "turn it down"), "adjustVolume"),
)

_UP_VERBS = ("increase", "raise", "turn up", "up", "brighten", "boost", "louder", "higher")
_DOWN_VERBS = ("decrease", "reduce", "lower", "turn down", "down", "dim", "quieter", "softer")
_SET_VERBS = ("set", "change", "make it", "put it")


def _match_command_grammar(query: str):
    """Return (action_tag, canonical_query) or None.

    canonical_query is rewritten into the form the existing Utility parsers
    already understand ("increase"/"decrease"/"set <n>"), because
    Utility.adjust_volume only recognises those literal keywords.
    """
    low = normalize(query)

    # A definitional question is never a command, even when it contains a
    # control verb: "what does brighten mean".
    if re.search(r"\b(mean|means|meaning|definition|define|defined)\b", low):
        return None

    action = None
    for needles, tag in _SUBJECT_TO_ACTION:
        if any(n in low for n in needles):
            action = tag
            break

    # Some verbs name their own subject: "dim the screen", "make it louder".
    # Word-boundary matched, so "dimmer switch" does not read as "dim".
    if action is None:
        for needles, tag in _VERB_IMPLIES_SUBJECT:
            if any(re.search(rf"\b{re.escape(n)}\b", low) for n in needles):
                action = tag
                break
    if action is None:
        return None

    subject = "brightness" if action == "adjustBrightness" else "volume"

    number = re.search(r"\b(\d{1,3})\b", low)
    if number and any(v in low for v in _SET_VERBS):
        return action, f"set {subject} {number.group(1)}"
    if any(v in low for v in _DOWN_VERBS):
        return action, f"decrease {subject}"
    if any(v in low for v in _UP_VERBS):
        return action, f"increase {subject}"
    if number:
        # "brightness 40" with no verb still reads as a set.
        return action, f"set {subject} {number.group(1)}"
    return None


class IntentRouter:
    def __init__(
        self,
        intents,
        ai_manager,
        assistant=None,
        soul: str = "",
        context=None,
        remember_store=None,
    ):
        self.intents = intents
        self.ai_manager = ai_manager
        self.assistant = assistant
        self.soul = soul
        self.context = context
        self.remember_store = remember_store
        self._tag_to_responses = {i["tag"]: i.get("responses", []) for i in intents}

    # ---- helpers -----------------------------------------------------------

    def _response_for(self, tag) -> Optional[str]:
        import random

        responses = self._tag_to_responses.get(tag)
        return random.choice(responses) if responses else None

    def _memory_text(self) -> str:
        return self.remember_store.load() if self.remember_store else ""

    def _context_text(self) -> str:
        return self.context.render() if self.context else ""

    def _remember(self, query, spoken):
        if self.context:
            self.context.add(query, spoken or "")

    # ---- stage 0 -----------------------------------------------------------

    def _exact_match(self, query: str) -> Optional[RouteResult]:
        tag = EXACT_ALIASES.get(normalize(query))
        if not tag:
            return None
        return RouteResult(source="fastpath", tag=tag, spoken=self._response_for(tag))

    # ---- entry point -------------------------------------------------------

    def route(self, query: str) -> RouteResult:
        hit = self._exact_match(query)
        if hit:
            return hit

        # Stage 0b: deterministic device-control grammar. 0ms, no model call.
        grammar = _match_command_grammar(query)
        if grammar:
            action, canonical = grammar
            if self.assistant is not None:
                self.assistant._execute_action(action, canonical)
            self._remember(query, "")
            return RouteResult(source="fastpath-grammar", tag=action)

        soul = self.soul
        context = self._context_text()
        memory = self._memory_text()

        choice = self.ai_manager.choose_tool(query, soul, context, memory)

        # Never fall back to fuzzy matching on model failure -- a wrong action
        # is worse than no action.
        if choice.get("name") == "error":
            return RouteResult(
                source="error",
                spoken="I could not reach my reasoning model just now.",
            )

        result = tool_registry.dispatch(
            choice["name"],
            choice.get("args", {}),
            assistant=self.assistant,
            original_query=query,
            remember_store=self.remember_store,
        )
        kind = result["kind"]

        if kind == "action":
            # The tool already performed the action and any speaking it does.
            self._remember(query, "")
            return RouteResult(source="tool", tool=choice["name"])

        if kind == "clarify":
            # A command we could not map. Answering "normally" here would make
            # the model claim it cannot do something it actually can.
            spoken = result.get("spoken") or "I didn't catch that."
            self._remember(query, spoken)
            return RouteResult(source="tool", spoken=spoken, tool=choice["name"])

        if kind == "memory":
            # Do NOT let the answer model narrate a memory save. Asked to
            # acknowledge "i prefer dark mode" it replied "Dark mode is set,
            # I've adjusted the display" -- it had done no such thing. A fixed
            # acknowledgement cannot lie, and costs no inference time.
            from core.config import AppConfig
            import random

            fact = result.get("fact") or ""
            if result.get("saved"):
                text = random.choice(
                    ["Noted.", "Got it, I'll remember that.",
                     "Noted, I'll keep that in mind.", "Understood."]
                )
                if AppConfig.memory["announce_saves"] and fact:
                    text = f"{text} (remembered: {fact})"
            else:
                text = "I already had that noted."
            self._remember(query, text)
            return RouteResult(source="tool", spoken=text, tool=choice["name"])

        evidence = result.get("evidence") or None
        text = self.ai_manager.compose_answer(query, soul, context, memory, evidence)

        self._remember(query, text)
        return RouteResult(source="ai", spoken=text, tool=choice["name"])
