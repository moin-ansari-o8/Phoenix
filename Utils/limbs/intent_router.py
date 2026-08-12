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

import logging
import re
from dataclasses import dataclass
from typing import Optional

from Utils.limbs import tool_registry
from Utils.ai_manager import is_unknown

logger = logging.getLogger("IntentRouter")


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
    "headphone mode": "echoModeOpen",
    "headphones mode": "echoModeOpen",
    "im on headphones": "echoModeOpen",
    "i am on headphones": "echoModeOpen",
    "speaker mode": "echoModeGate",
    "speakers mode": "echoModeGate",
    "im on speakers": "echoModeGate",
    "i am on speakers": "echoModeGate",
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

# Social formulae. Added 2026-08-12 from scripts/utilities/mine_aliases.py run
# against the real data/ChatLog.json, which showed only 3% of actual utterances
# resolving without a model call - far below the ~40% that tests/test_routing.py
# suggests, because that file is device-command heavy while real use is mostly
# conversational. Greetings and farewells were each costing a ~1.7 s model call
# to produce a canned reply the model was not adding anything to.
#
# Kept deliberately narrow. An alias is a permanent claim that a phrase always
# means one thing, so only fixed social formulae are here. Notably absent:
# "it's amazing" (repeated twice in the log) - that is a comment about something
# specific and deserves a real answer, not a stock reply.
CONVERSATION_ALIASES = {
    # greetings
    "hi": "hi",
    "hii": "hi",
    "hello": "hi",
    "hey": "hi",
    "hi there": "hi",
    "hello there": "hi",
    "hey there": "hi",
    "hi bro": "hi",
    "hi there bro": "hi",
    "hello bro": "hi",
    "yo": "hi",
    "good morning": "hi",
    "good evening": "hi",
    # presence checks - "are you there" wants an acknowledgement, not an essay
    "are you there": "hi",
    "you there": "hi",
    "hello are you there": "hi",
    "are you awake": "hi",
    "are you listening": "hi",
    # how are you
    "how are you": "greetask",
    "how are you doing": "greetask",
    "hows it going": "greetask",
    "how is it going": "greetask",
    "whats up": "greetask",
    "wassup": "greetask",
    "sup": "greetask",
    # thanks
    "thank you": "youarewelcome",
    "thanks": "youarewelcome",
    "thank you so much": "youarewelcome",
    "thanks a lot": "youarewelcome",
    "thankyou": "youarewelcome",
    # farewells
    "thank you bye": "nicetalking",
    "bye": "nicetalking",
    "goodbye": "nicetalking",
    "good bye": "nicetalking",
    "see you": "nicetalking",
    "see you later": "nicetalking",
    "nice talking to you": "nicetalking",
    # acknowledgements
    "ok": "okay",
    "okay": "okay",
    "alright": "okay",
    "got it": "okay",
    "cool": "okay",
}

EXACT_ALIASES = {**DEVICE_ALIASES, **IDENTITY_ALIASES, **CONVERSATION_ALIASES}


# --- Stage 0b: imperative command grammar ------------------------------------
# "increase brightness by 30%" is subject + verb + number. That is a parsing
# problem, not a reasoning problem, and sending it to a model costs seconds and
# sometimes gets it wrong. This is NOT the fuzzy matching that caused the old
# misfires: it requires BOTH a control verb AND a control subject to be present,
# so it cannot fire on a question like "what do you mean by time".

_SUBJECT_TO_ACTION = (
    (("brightness", "bright", "screen light", "backlight"), "adjustBrightness"),
    (("volume", "sound", "audio", "music", "speaker level"), "adjustVolume"),
)

_ACTION_FOR_SUBJECT = {
    "brightness": "adjustBrightness",
    "volume": "adjustVolume",
}

# "decrease it" only means anything if we remember what was last adjusted.
_PRONOUNS = (r"\bit\b", r"\bthat\b", r"\bthis\b", r"\bthem\b", r"\bagain\b")

# Words that may remain in a query that is otherwise just a bare command,
# e.g. "decrease by 40%" -> nothing meaningful left once these are removed.
_FILLER = (
    "by", "to", "the", "a", "an", "please", "little", "bit", "some", "more",
    "percent", "pct", "now", "my", "for", "me", "and", "then", "just",
    "normal", "back", "again",
)

# "back to normal" means restore the level the session started at.
# "make it normal" must match too -- requiring the word "to" missed it, and the
# request fell through to the LLM, which carried on with the previous topic.
_RESET_PATTERNS = (
    r"\bback to normal\b", r"\bto normal\b", r"\bnormal again\b",
    r"\b(make|set|put|bring|get|return|restore)\b[^?]*\bnormal\b",
    r"^normal$", r"\breset\b", r"\bundo\b", r"\brevert\b", r"\brestore\b",
    r"\bas (it was|before)\b", r"\boriginal\b", r"\bdefault\b",
)

# "more" straight after a brightness/volume change means do it again. Only
# treated as a continuation when the previous turn WAS a device command --
# otherwise "come again" would adjust the screen instead of repeating an answer.
_CONTINUE_PATTERNS = (
    r"^more$", r"^a (bit|little) more$", r"^some more$", r"^even more$",
    r"^more please$", r"^again$", r"^once more$", r"^keep going$",
    r"^further$", r"^continue$", r"^and more$", r"^bit more$",
)


def _is_continuation(query: str) -> bool:
    low = normalize(query)
    return any(re.search(p, low) for p in _CONTINUE_PATTERNS)


# A question about normality is not a reset command: "is this normal?"
_QUESTION_OPENERS = (
    "is", "are", "was", "were", "do", "does", "did", "can", "could",
    "should", "would", "will", "what", "why", "how", "who", "which", "when",
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

# Verbs strong enough to justify resolving a pronoun against the last device.
# Bare "up"/"down" are excluded: "can you look it up" is not a brightness
# command, and "make it"/"change" are too generic ("make it clear").
_STRONG_VERBS = (
    "increase", "decrease", "raise", "lower", "reduce", "boost", "dim",
    "brighten", "turn up", "turn down", "louder", "quieter", "softer",
    "higher", "set",
)


def _residual_is_empty(low: str) -> bool:
    """True if nothing but verbs, numbers and filler remain.

    Lets "decrease by 40%" resolve to the last-adjusted device, while a query
    that names something else ("turn down the oven") does not.
    """
    words = set(re.findall(r"[a-z]+", low))
    verbs = set()
    for group in (_UP_VERBS, _DOWN_VERBS, _SET_VERBS):
        for v in group:
            verbs.update(v.split())
    return not (words - verbs - set(_FILLER))


def _match_command_grammar(query: str, last_device=None):
    """Parse a device-control command.

    Returns None, or a dict:
      {"action": tag, "subject": "brightness"|"volume",
       "mode": "increase"|"decrease"|"set"|"reset", "amount": int|None}

    `last_device` resolves pronouns: "decrease it" after adjusting brightness
    means brightness. Without it, "decrease it" reached the LLM, came back as
    action="decrease" with no target, and failed with "I didn't catch which
    setting you wanted me to change."
    """
    low = normalize(query)

    # A definitional question is never a command: "what does brighten mean".
    if re.search(r"\b(mean|means|meaning|definition|define|defined)\b", low):
        return None

    subject = None
    for needles, tag in _SUBJECT_TO_ACTION:
        if any(n in low for n in needles):
            subject = "brightness" if tag == "adjustBrightness" else "volume"
            break

    # Verbs that name their own subject: "dim the screen", "make it louder".
    if subject is None:
        for needles, tag in _VERB_IMPLIES_SUBJECT:
            if any(re.search(rf"\b{re.escape(n)}\b", low) for n in needles):
                subject = "brightness" if tag == "adjustBrightness" else "volume"
                break

    has_verb = any(
        v in low for group in (_UP_VERBS, _DOWN_VERBS, _SET_VERBS) for v in group
    )
    # "is this normal?" asks a question; it does not ask for a restore.
    looks_asked = low.split()[0] in _QUESTION_OPENERS if low.split() else False
    is_reset = (not looks_asked) and any(
        re.search(p, low) for p in _RESET_PATTERNS
    )
    has_pronoun = any(re.search(p, low) for p in _PRONOUNS)

    # Resolve "it"/"that", or a bare "decrease by 40%", against the last device.
    # Requires an unambiguous verb so "can you look it up" stays a question.
    has_strong_verb = any(
        re.search(rf"\b{re.escape(v)}\b", low) for v in _STRONG_VERBS
    )
    if subject is None and last_device and (is_reset or has_strong_verb):
        if has_pronoun or _residual_is_empty(low):
            subject = last_device
    if subject is None:
        return None

    action = _ACTION_FOR_SUBJECT[subject]

    if is_reset:
        return {"action": action, "subject": subject, "mode": "reset", "amount": None}
    if not has_verb:
        # A bare noun is a question ("what is brightness"), not a command.
        if not re.search(r"\b\d{1,3}\b", low):
            return None

    number = re.search(r"\b(\d{1,3})\b", low)
    amount = int(number.group(1)) if number else None
    relative = amount is not None and re.search(r"\bby\b", low)

    if amount is not None and any(v in low for v in _SET_VERBS) and not relative:
        return {"action": action, "subject": subject, "mode": "set", "amount": amount}
    if any(v in low for v in _DOWN_VERBS):
        return {
            "action": action, "subject": subject, "mode": "decrease",
            "amount": amount if relative else None,
        }
    if any(v in low for v in _UP_VERBS):
        return {
            "action": action, "subject": subject, "mode": "increase",
            "amount": amount if relative else None,
        }
    if amount is not None:
        return {"action": action, "subject": subject, "mode": "set", "amount": amount}
    return None


DEFAULT_STEP = 10  # matches Utility.adjust_brightness / adj_volume defaults


def build_canonical(subject: str, mode: str, amount) -> str:
    """Render into the literal keywords Utility.adjust_* already parses."""
    if mode == "set":
        return f"set {subject} {amount}"
    if amount:
        return f"{mode} {subject} by {amount}"
    return f"{mode} {subject}"


class IntentRouter:
    def __init__(
        self,
        intents,
        ai_manager,
        assistant=None,
        soul: str = "",
        context=None,
        remember_store=None,
        trace=None,
    ):
        self.intents = intents
        self.ai_manager = ai_manager
        self.assistant = assistant
        self.soul = soul
        self.context = context
        self.remember_store = remember_store
        # Optional callable(label: str) used to surface the routing decision,
        # e.g. "answer_directly  capital of france". Borrowed from IGRS, where
        # the classifier emits a visible "general <query>" / "realtime <query>"
        # prefix -- it makes the assistant's reasoning legible at a glance.
        self.trace = trace
        self._tag_to_responses = {i["tag"]: i.get("responses", []) for i in intents}
        # Which device was last adjusted, so "decrease it" has a referent, and
        # the net change applied to each so "back to normal" can undo it.
        self.last_device = None
        # Absolute level read from the hardware before our first change, so
        # "back to normal" restores it even if it was changed outside Phoenix.
        self.baseline = {"brightness": None, "volume": None}
        # Fallback when the hardware level cannot be read (some monitors expose
        # no WMI brightness, pycaw may be missing): undo our own net change.
        self.net_delta = {"brightness": 0, "volume": 0}
        # Last device command, so a bare "more" can repeat it.
        self.last_mode = None
        self.last_amount = None
        self.last_was_device = False

    def _emit_trace(self, label: str, detail: str = ""):
        if not self.trace:
            return
        try:
            self.trace(f"{label} {detail}".strip())
        except Exception:
            pass

    # ---- helpers -----------------------------------------------------------

    def _response_for(self, tag) -> Optional[str]:
        import random

        responses = self._tag_to_responses.get(tag)
        return random.choice(responses) if responses else None

    def _memory_text(self) -> str:
        return self.remember_store.load() if self.remember_store else ""

    def _context_text(self) -> str:
        return self.context.render() if self.context else ""

    def _recall_text(self, query: str) -> str:
        """Relevant older exchanges from the persisted chat log.

        The rolling window only holds the last few turns, so without this
        "you told me about X last week" is unanswerable after a restart.
        """
        if not self.context or not hasattr(self.context, "search"):
            return ""
        try:
            return self.context.search(query, limit=4)
        except Exception:
            return ""

    def _remember(self, query, spoken):
        if self.context:
            self.context.add(query, spoken or "")

    def _clear_device_focus(self):
        """A non-device turn breaks the "more" chain."""
        self.last_was_device = False

    # ---- stage 0 -----------------------------------------------------------

    def _exact_match(self, query: str) -> Optional[RouteResult]:
        tag = EXACT_ALIASES.get(normalize(query))
        if not tag:
            return None
        return RouteResult(source="fastpath", tag=tag, spoken=self._response_for(tag))

    def _read_level(self, subject: str):
        """Current hardware level 0-100, or None if unreadable."""
        util = getattr(self.assistant, "utility", None)
        if util is None:
            return None
        try:
            if subject == "brightness":
                return util.get_brightness()
            return util.get_volume_percent()
        except Exception:
            return None

    def _set_absolute(self, subject: str, value):
        util = getattr(self.assistant, "utility", None)
        if util is None:
            return None
        try:
            if subject == "brightness":
                return util.set_brightness_absolute(value)
            return util.set_volume_percent(value)
        except Exception:
            return None

    def _capture_baseline(self, subject: str):
        """Record the level before our first change to this device."""
        if self.baseline.get(subject) is None:
            level = self._read_level(subject)
            if level is not None:
                self.baseline[subject] = level

    def _run_device_command(self, query: str, parsed: dict) -> RouteResult:
        """Execute a parsed brightness/volume command and update focus state."""
        subject, mode = parsed["subject"], parsed["mode"]
        action, amount = parsed["action"], parsed["amount"]

        if mode != "reset":
            self._capture_baseline(subject)

        if mode == "reset":
            target = self.baseline.get(subject)
            if target is not None:
                # Absolute restore: correct even if the level was changed
                # outside Phoenix since we took the baseline.
                self._emit_trace("grammar", f"{subject} restore -> {target}")
                applied = self._set_absolute(subject, target)
                self.net_delta[subject] = 0
                self.last_device = subject
                spoken = (
                    f"{subject.capitalize()} is back to {target} percent."
                    if applied is not None
                    else f"I could not restore the {subject}."
                )
                self._remember(query, spoken)
                return RouteResult(
                    source="fastpath-grammar", tag=action, spoken=spoken
                )

            # No baseline readable: undo our own net change instead.
            delta = self.net_delta.get(subject, 0)
            if delta == 0:
                spoken = f"The {subject} is already back where it started."
                self._emit_trace("grammar", f"{subject} reset (no change to undo)")
                self._remember(query, spoken)
                return RouteResult(
                    source="fastpath-grammar", tag=action, spoken=spoken
                )
            mode = "decrease" if delta > 0 else "increase"
            amount = abs(delta)
            self.net_delta[subject] = 0
        elif mode == "set":
            # An absolute set discards the baseline we were tracking.
            self.net_delta[subject] = 0
        else:
            step = amount if amount else DEFAULT_STEP
            self.net_delta[subject] += step if mode == "increase" else -step

        self.last_device = subject
        self.last_mode = mode
        self.last_amount = amount
        self.last_was_device = True
        canonical = build_canonical(subject, mode, amount)
        self._emit_trace("grammar", f"{action} <- {canonical}")
        if self.assistant is not None:
            self.assistant._execute_action(action, canonical)
        self._remember(query, "")
        return RouteResult(source="fastpath-grammar", tag=action)

    # ---- entry point -------------------------------------------------------

    def route(self, query: str) -> RouteResult:
        hit = self._exact_match(query)
        if hit:
            self._emit_trace("alias", hit.tag or "")
            return hit

        # "more" right after a device change repeats it. Gated on the previous
        # turn actually being a device command, so "again" after a Q&A still
        # means "repeat that answer".
        if (
            self.last_was_device
            and self.last_device
            and self.last_mode in ("increase", "decrease")
            and _is_continuation(query)
        ):
            return self._run_device_command(
                query,
                {
                    "action": _ACTION_FOR_SUBJECT[self.last_device],
                    "subject": self.last_device,
                    "mode": self.last_mode,
                    "amount": self.last_amount,
                },
            )

        # Stage 0b: deterministic device-control grammar. 0ms, no model call.
        grammar = _match_command_grammar(query, last_device=self.last_device)
        if grammar:
            return self._run_device_command(query, grammar)

        soul = self.soul
        context = self._context_text()
        memory = self._memory_text()

        self._clear_device_focus()
        choice = self.ai_manager.choose_tool(query, soul, context, memory)

        # IGRS-style visible classification: "search_web population of france".
        _args = choice.get("args") or {}
        self._emit_trace(
            choice.get("name", "?"),
            str(
                _args.get("what")
                or _args.get("action")
                or _args.get("topic")
                or _args.get("query")
                or _args.get("fact")
                or ""
            ),
        )

        # Never fall back to fuzzy matching on model failure -- a wrong action
        # is worse than no action.
        if choice.get("name") == "error":
            return RouteResult(
                source="error",
                spoken="I could not reach my reasoning model just now.",
            )

        # If the model chose a device change but named no target ("decrease it"),
        # re-parse with the remembered device rather than giving up.
        if choice["name"] == "control_device" and self.last_device:
            _act = str((choice.get("args") or {}).get("action", ""))
            if tool_registry.salvage_action(_act, query) is None:
                retry = _match_command_grammar(
                    f"{_act} {query}", last_device=self.last_device
                )
                if retry:
                    return self._run_device_command(query, retry)

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

            # dispatch only returns kind="memory" when a save actually happened.
            fact = result.get("fact") or ""
            text = random.choice(
                ["Noted.", "Got it, I'll remember that.",
                 "Noted, I'll keep that in mind.", "Understood."]
            )
            if AppConfig.memory["announce_saves"] and fact:
                text = f"{text} (remembered: {fact})"
            self._remember(query, text)
            return RouteResult(source="tool", spoken=text, tool=choice["name"])

        evidence = result.get("evidence") or None
        # For a direct answer, older matching exchanges are the only way to
        # recall something said before the rolling window (or before a restart).
        if evidence is None:
            recalled = self._recall_text(query)
            if recalled and recalled not in context:
                memory = f"{memory}\n\nEarlier exchanges that mention this:\n{recalled}"
        text, already_spoken = self._answer(query, soul, context, memory, evidence)

        if is_unknown(text) and not already_spoken:
            text = self._handle_unknown(query, soul, context, memory, had_evidence=bool(evidence))

        self._remember(query, text)
        # spoken=None tells the caller it has already been said aloud, sentence
        # by sentence, while the model was still writing the rest.
        return RouteResult(
            source="ai", spoken=None if already_spoken else text, tool=choice["name"]
        )

    def _answer(self, query, soul, context, memory, evidence):
        """
        Produce the spoken answer, streaming it when that is safe.

        Returns (text, already_spoken).

        **Streaming commits us.** Once the first sentence has been spoken there
        is no taking it back, so `_handle_unknown`'s escalation to a web search
        is only available while we are still silent. That is why `emit` below
        refuses to speak a sentinel or a hedge: if the model declines, nothing
        is voiced, `already_spoken` stays False, and the normal escalation path
        runs exactly as it did before. A late hedge after two good sentences is
        simply not spoken - far better than answering twice, which is what
        escalating mid-stream would produce.
        """
        from core.config import AppConfig

        streaming = bool(getattr(AppConfig, "stream_answers", True))
        speaker = getattr(self.assistant, "speak", None)
        if not streaming or speaker is None:
            return self.ai_manager.compose_answer(
                query, soul, context, memory, evidence
            ), False

        spoken_flag = {"any": False}

        def emit(sentence):
            spoken_flag["any"] = True
            speaker(sentence)

        try:
            text = self.ai_manager.compose_answer_streaming(
                query, soul, context, memory, evidence, on_sentence=emit
            )
        except Exception as exc:
            logger.warning("Streaming answer failed (%s); using blocking path", exc)
            if spoken_flag["any"]:
                # Half an answer is out. Say nothing more rather than starting
                # a second, different one.
                return "", True
            return self.ai_manager.compose_answer(
                query, soul, context, memory, evidence
            ), False

        return text, spoken_flag["any"]

    def _handle_unknown(self, query, soul, context, memory, had_evidence):
        """
        The answer model declined. Look it up rather than giving up.

        "I don't know" is honest but useless when the answer is one search away,
        so a decline escalates to the web first and only becomes a spoken "I
        don't know" when that also comes back empty. Escalating is skipped when
        the model was already working from web evidence -- searching again would
        just fetch the same page and decline again, slower.
        """
        # Imported locally to match route() above, which does the same. A
        # module-level AppConfig here would be shadowed inside route() by its
        # own local import and raise UnboundLocalError -- see the 2026-08-12
        # entry in .github/mistakes.md.
        from core.config import AppConfig

        if had_evidence or not AppConfig.web.get("enabled", True):
            self._emit_trace("unknown", "no answer, not escalating")
            return "I don't know that one, sir."

        self._emit_trace("unknown", "escalating to web search")
        try:
            result = tool_registry.dispatch(
                "search_web",
                {"query": query},
                assistant=self.assistant,
                original_query=query,
                remember_store=self.remember_store,
            )
            evidence = result.get("evidence") or None
        except Exception as exc:
            logger.warning("Escalated search failed: %s", exc)
            evidence = None

        if not evidence:
            return "I don't know that one, sir."

        text = self.ai_manager.compose_answer(query, soul, context, memory, evidence)
        if is_unknown(text):
            # The search ran and the model still could not answer from it. Say
            # so plainly instead of reading out whatever it hedged with.
            return "I looked it up and still couldn't find a clear answer, sir."
        return text
