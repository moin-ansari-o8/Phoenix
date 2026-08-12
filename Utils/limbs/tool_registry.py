"""Tool schemas for the LLM router, and dispatch into existing Phoenix actions.


Six tools. The ~90 PC actions collapse into two enum-driven tools split by
read vs. mutate -- this is what lets a *question* legitimately reach a *local*
tool ("what is the time" needs the clock, not a web search).
"""

import logging
import re

# Read-only device state. Values are existing action tags in _execute_action.
DEVICE_STATE_READS = {
    "time": "saytime",
    "date": "dateday",
    "battery": "battery",
    "weather": "weather",
    "timers": "viewTimer",
    "alarms": "viewAlarm",
    "reminders": "viewReminder",
    "songs": "viewsongs",
}

# State-changing actions. Every one must already exist as a key in
# PhoenixAssistant._execute_action's action_map / common_tags.
CONTROL_ACTIONS = [
    "open", "close", "openelse", "playsong", "playpause", "adjustVolume",
    "adjustBrightness", "muteSpeaker", "unmuteSpeaker", "screenshot",
    "setTimer", "setAlarm", "dltAlarm", "setReminder", "newtab", "closetab",
    "changetab", "swtchTab", "maximize", "minimize", "fullscreen", "hide",
    "pcshutdown", "pcrestart", "pcsleep", "pchibernate", "phnxrestart",
    "bluetooth", "hotspot", "switchdesk", "movewind", "press", "type",
    "searchyoutube", "searchinsta", "amazon", "flipkart", "suggestsong",
    "addsong", "dltsong", "knock-knock",
]

MEMORY_CATEGORIES = ["People", "Preferences", "Facts", "Projects"]

# Topical guard for get_device_state. This is a VALIDATOR, not a router: it can
# only reject a reading the model picked, never choose one. Without it a 3B
# router will answer "tell me the capital of france" by reporting the clock,
# because "tell me the ..." pattern-matches the time example in its prompt.
# Rejection degrades safely to a normal spoken answer.
_STATE_KEYWORDS = {
    "time": ("time", "clock", "hour", "minute", "o'clock", "oclock"),
    "date": ("date", "today", "day", "month", "year", "tomorrow", "yesterday"),
    "battery": ("battery", "charge", "charging", "power", "percent", "juice"),
    "weather": ("weather", "temperature", "hot", "cold", "rain", "forecast",
                "humid", "sunny", "cloudy"),
    "timers": ("timer",),
    "alarms": ("alarm",),
    "reminders": ("remind", "reminder"),
    "songs": ("song", "music", "playlist", "track"),
}


def _state_is_plausible(what: str, query: str) -> bool:
    """True if the query actually talks about the reading the model chose."""
    words = _STATE_KEYWORDS.get(what)
    if not words:
        return False
    low = (query or "").lower()
    return any(w in low for w in words)


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_device_state",
            "description": (
                "Read a live READING from the user's own PC: the current clock, today's "
                "date, the battery percentage, local weather, or the user's own timers, "
                "alarms, reminders and songs. Questions may use this tool, and you "
                "should never search the web for these. "
                "Only use it when the user wants the CURRENT VALUE. Do NOT use it when "
                "the user asks what a word or concept MEANS - 'what do you mean by "
                "time' asks for an explanation, not the clock."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "what": {
                        "type": "string",
                        "enum": list(DEVICE_STATE_READS.keys()),
                        "description": "Which piece of device state to read.",
                    }
                },
                "required": ["what"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_device",
            "description": (
                "Change something on the user's Windows PC: launch or close apps, "
                "adjust volume or brightness, take a screenshot, set a timer or alarm, "
                "shut down. Use ONLY for an explicit instruction to do something. "
                "Never use this to answer a question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": CONTROL_ACTIONS,
                        "description": "The action tag to run.",
                    },
                    "argument": {
                        "type": "string",
                        "description": "Target of the action, e.g. an app name. May be empty.",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the internet for information that CHANGES OVER TIME. Use for "
                "population figures, prices, exchange rates, news, weather elsewhere, "
                "sports scores, who currently holds an office, latest software "
                "versions, and anything phrased with today/now/current/latest/recent. "
                "Do NOT use it for facts that never change - a capital city, a "
                "historical date, a definition - those go to answer_directly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"],
            },
        },
    },
    # NOTE: there is deliberately NO separate "lookup_encyclopedia" tool.
    # A three-way knowledge split (know-it / encyclopedia / search) is too subtle
    # for a small router: it sent "capital of france" and "who was gandhi" to an
    # encyclopedia lookup, and even "current PM of india" (which changes!).
    # IGRS used only two knowledge modes - general vs realtime - and that is why
    # it worked. search_web tries Wikipedia first internally (see
    # web_search.gather_context), so named entities still get encyclopedic
    # quality without the router having to make that call.
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": (
                "Save a durable fact the user just revealed about themselves, the "
                "people in their life, or their preferences. "
                "Trigger on statements like: 'my friend Moin told me...' (save that "
                "Moin is their friend), 'I prefer dark mode', 'I like X', 'I work at "
                "Y', 'my sister is Z', 'I'm learning W'. "
                "Any sentence where the user states a personal fact rather than asking "
                "a question or giving a command belongs here. Do not use for questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": MEMORY_CATEGORIES},
                    "fact": {
                        "type": "string",
                        "description": "The fact, in third person as a standalone sentence.",
                    },
                },
                "required": ["category", "fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer_directly",
            "description": (
                "Answer from your identity, your memory of the user, the conversation, "
                "or your own general knowledge - with no lookup and no PC action. "
                "ALWAYS use this for questions about YOURSELF (your name, who made you, "
                "who your master is), about the USER (who am I, what is my name, what "
                "do I like), or about people and preferences the user has told you "
                "before. That information is already given to you above - never search "
                "the web for it. "
                "ALSO use this for any fact that NEVER CHANGES and you already know: "
                "capital cities, history, geography, definitions, science, maths - "
                "'what is the capital of France', 'who was Gandhi', 'what is Python'. "
                "Looking those up wastes seconds for an answer you already have. "
                "Also use for chit-chat, greetings, follow-ups, "
                "opinions, and general concepts you are confident about."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

VALID_TOOL_NAMES = {t["function"]["name"] for t in TOOL_SCHEMAS}
# Accepted from the model but folded into search_web, since older prompts and
# some model outputs still name it.
VALID_TOOL_NAMES.add("lookup_encyclopedia")


# Argument repair. Small models often return the VERB ("increase") instead of the
# tool tag ("adjustBrightness"). This does not change WHICH tool was chosen -- the
# model already said control_device -- it only repairs the argument, so it is not
# routing logic. Without it "increase brightness by 30%" fails outright.
_SUBJECT_ACTIONS = (
    ("brightness", "adjustBrightness"),
    ("bright", "adjustBrightness"),
    ("dim", "adjustBrightness"),
    ("volume", "adjustVolume"),
    ("sound", "adjustVolume"),
    ("louder", "adjustVolume"),
    ("quieter", "adjustVolume"),
    ("screenshot", "screenshot"),
    ("bluetooth", "bluetooth"),
    ("hotspot", "hotspot"),
    ("timer", "setTimer"),
    ("alarm", "setAlarm"),
    ("remind", "setReminder"),
    ("shutdown", "pcshutdown"),
    ("shut down", "pcshutdown"),
    ("mute", "muteSpeaker"),
)


def salvage_action(action: str, query: str):
    """Return a valid CONTROL_ACTIONS tag, or None if unrecoverable."""
    if action in CONTROL_ACTIONS:
        return action

    # Models often cram action and target together: "open brave".
    head = action.split()[0] if action.split() else ""
    if head in CONTROL_ACTIONS:
        return head
    # ...or use a colon/comma form: "action:open,target:brave".
    m = re.search(r"action\s*[:=]\s*([A-Za-z_]+)", action)
    if m and m.group(1) in CONTROL_ACTIONS:
        return m.group(1)

    low = f"{action} {query}".lower()
    for needle, tag in _SUBJECT_ACTIONS:
        if needle in low:
            return tag
    return None


def normalize_json_choice(raw: dict, query: str) -> dict:
    """Convert the flat {"tool","arg","extra"} JSON the rules ask for into the
    per-tool argument dicts that dispatch() expects."""
    name = str(raw.get("tool", "") or "").strip()
    arg = str(raw.get("arg", "") or "").strip()
    extra = str(raw.get("extra", "") or "").strip()

    if name not in VALID_TOOL_NAMES:
        logging.warning(f"[tool_registry] unknown tool from rules: {name!r}")
        return {"name": "answer_directly", "args": {}}

    if name == "get_device_state":
        return {"name": name, "args": {"what": arg.lower()}}
    if name == "control_device":
        return {"name": name, "args": {"action": arg, "argument": extra}}
    if name == "search_web":
        return {"name": name, "args": {"query": arg or query}}
    if name == "lookup_encyclopedia":
        return {"name": name, "args": {"topic": arg or query}}
    if name == "remember":
        return {"name": name, "args": {"fact": arg, "category": extra or "Facts"}}
    return {"name": name, "args": {}}


# Words that make a question unambiguously time-sensitive. answer_directly is
# the default (so settled facts stay instant), but a stale answer to "who is the
# CURRENT prime minister" is confidently wrong, which is worse than being slow.
# This overrides answer_directly -> search_web on these signals only.
_VOLATILITY_MARKERS = (
    "current", "currently", "latest", "recent", "recently", "today", "todays",
    "right now", "this year", "this month", "this week", "up to date",
    "nowadays", "these days", "price", "prices", "cost of", "population",
    "news", "headline", "score", "who won", "live", "newest", "so far",
    "as of now", "trending", "release date", "released",
)

# ...except when the question is really about local device state, where
# "current" just means "right now on this pc" and a lookup is nonsense.
_DEVICE_WORDS = (
    "time", "clock", "date", "day", "battery", "charge", "alarm", "timer",
    "reminder", "song", "playlist", "volume", "brightness",
)


# Questions the PC can answer exactly. A typo ("wht's today") missed the alias
# table, reached the model, and got "August 9th, National Women's Day and Islamic
# New Year" -- partly invented. The clock is authoritative; never guess it.
_DEVICE_STATE_PATTERNS = (
    (r"\b(time|clock)\b", "time"),
    (r"\b(date|today|todays|day)\b", "date"),
    (r"\b(battery|charging|charge level)\b", "battery"),
)


def device_state_for(query: str):
    """Return a DEVICE_STATE_READS key if the query asks for a local reading."""
    low = (query or "").lower()
    # "what do you mean by time" asks for a definition, not the clock.
    if re.search(r"\b(mean|means|meaning|definition|define)\b", low):
        return None
    for pattern, what in _DEVICE_STATE_PATTERNS:
        if re.search(pattern, low):
            return what
    return None


# "forget"/"unremember" are inherently about memory. The others also mean
# ordinary deletion ("remove the file"), so they need memory context.
_MEMORY_VERBS = r"(forget|unremember)"
_GENERIC_DELETE_VERBS = r"(remove|delete|erase|drop|discard|scrub)"
# remem\w* tolerates typos -- the real request was "remove wht u jst rememebrd".
_MEMORY_WORDS = r"(remem\w*|memory|memories|noted|stored|saved|you know|know about)"


def _forget_request(query: str):
    """Detect a request to delete stored memory.

    Returns None, or {"topic": str, "last": bool}. `last` drops the most
    recent entry ("forget that").
    """
    low = (query or "").strip().lower()
    words = low.split()

    is_memory_verb = re.search(rf"\b{_MEMORY_VERBS}\b", low) is not None
    is_generic = re.search(rf"\b{_GENERIC_DELETE_VERBS}\b", low) is not None
    if not (is_memory_verb or is_generic):
        return None

    has_memory_ctx = re.search(rf"\b{_MEMORY_WORDS}\b", low) is not None
    # "remove the file" must not wipe memory.
    if is_generic and not is_memory_verb and not has_memory_ctx:
        return None

    if re.search(r"\b(everything|all of it|all of them|all)\b", low):
        return {"topic": "", "last": False, "all": True}

    m = re.search(r"\babout\s+(.+)$", low)
    if m:
        topic = re.sub(r"[^\w\s]", "", m.group(1)).strip()
        # "about narendra modi" keeps the name; "about me/that" is not a topic.
        if topic and topic not in ("me", "it", "that", "this"):
            return {"topic": topic, "last": False, "all": False}

    # Bare "forget that" only. "forget it i will do it myself" is a dismissal,
    # not a delete, so require a short utterance.
    if len(words) <= 4:
        return {"topic": "", "last": True, "all": False}
    if has_memory_ctx:
        return {"topic": "", "last": True, "all": False}
    return None


def web_allowed() -> bool:
    """
    Whether Phoenix may reach the internet right now.

    `web.enabled` was parsed by core/config.py but read by nobody, so setting it
    to false did precisely nothing - the one switch a user would reach for to
    make Phoenix offline was decorative. Every network path in this module now
    goes through here, and here delegates to connectivity.network_allowed(),
    which also honours `offline_mode` and an actual reachability probe.
    """
    from Utils.limbs.connectivity import network_allowed

    return network_allowed()


# Spoken when a lookup is refused. Deliberately an admission, not an attempt:
# the failure mode this exists to prevent is Phoenix answering from stale
# training data while sounding like it just looked something up.
OFFLINE_NOTICE = "I can't look that up right now - web access is turned off."
NO_NETWORK_NOTICE = "I can't look that up - I'm not connected to the internet."


def _offline_evidence(topic: str):
    """
    Try the local encyclopedia before admitting defeat.

    Most of what search_web was used for is encyclopedic rather than volatile,
    and that does not need a network - it needs a local copy. Returns evidence
    or None; a missing archive is simply None.
    """
    try:
        from Utils.limbs.offline_wiki import get_wiki

        text = get_wiki().summary(topic)
    except Exception as exc:
        logging.debug(f"[tool_registry] offline wiki unavailable: {exc}")
        return None
    if text:
        logging.info(f"[tool_registry] answered {topic!r} from the offline archive")
    return text or None


def _refuse_web(query: str):
    """
    A blocked network lookup: answer locally if we can, otherwise say so.

    "You switched the web off" and "there is no wifi" are different facts and
    lead to different user actions, so they get different sentences. Neither is
    ever a fall-through to answering from training data - that is the failure
    this whole path exists to prevent.
    """
    from Utils.limbs.connectivity import network_allowed

    evidence = _offline_evidence(query)
    if evidence:
        return _result("evidence", evidence=evidence)

    _, why = network_allowed(reason=True)
    spoken = NO_NETWORK_NOTICE if why == "no network detected" else OFFLINE_NOTICE
    logging.info(f"[tool_registry] blocked ({why}); refusing lookup for {query!r}")
    return _result("direct", spoken=spoken)


def needs_fresh_data(query: str) -> bool:
    """True if the query is explicitly time-sensitive and not about this PC."""
    low = (query or "").lower()
    if any(re.search(rf"\b{re.escape(w)}\b", low) for w in _DEVICE_WORDS):
        return False
    return any(m in low for m in _VOLATILITY_MARKERS)


def _result(kind, spoken=None, evidence=None, saved=None, fact=None):
    return {
        "kind": kind,
        "spoken": spoken,
        "evidence": evidence,
        "saved": saved,
        "fact": fact,
    }


def dispatch(name, args, assistant=None, original_query="", remember_store=None):
    """Execute one tool call.

    Returns {"kind": "action"|"evidence"|"memory"|"direct", ...}.
    Model-supplied strings are validated against the enums above -- never
    passed to getattr/eval.
    """
    args = args or {}

    if name == "get_device_state":
        what = str(args.get("what", "")).strip().lower()
        tag = DEVICE_STATE_READS.get(what)
        if not tag:
            logging.warning(f"[tool_registry] unknown device state: {what!r}")
            return _result("direct")
        if not _state_is_plausible(what, original_query):
            # The router misfired: the query is not about this reading at all.
            # Answer it normally rather than performing an unrelated action.
            logging.warning(
                f"[tool_registry] rejected get_device_state({what!r}) for "
                f"unrelated query: {original_query!r}"
            )
            return _result("direct")
        if assistant is not None:
            assistant._execute_action(tag, original_query)
        return _result("action")

    if name == "control_device":
        raw_action = str(args.get("action", "")).strip()
        action = salvage_action(raw_action, original_query)
        if action is None:
            # A command we could not map. Do NOT hand this to the answer model:
            # it will confidently claim Phoenix cannot do it, which is a lie.
            logging.warning(
                f"[tool_registry] unmappable action {raw_action!r} for "
                f"query {original_query!r}"
            )
            return _result(
                "clarify",
                spoken="I didn't catch which setting you wanted me to change.",
            )
        if action != raw_action:
            logging.info(
                f"[tool_registry] salvaged action {raw_action!r} -> {action!r}"
            )
        argument = str(args.get("argument", "") or "").strip()
        if assistant is not None:
            assistant._execute_action(action, argument or original_query)
        return _result("action")

    if name == "search_web":
        from core.config import AppConfig

        query = str(args.get("query", "") or original_query).strip()
        if not web_allowed():
            return _refuse_web(query)

        from Utils.limbs.web_search import gather_context

        evidence = gather_context(
            query,
            max_chars=AppConfig.web["max_context_chars"],
            max_results=AppConfig.web["max_results"],
            timeout=AppConfig.web["fetch_timeout_seconds"],
        )
        return _result("evidence", evidence=evidence)

    if name == "lookup_encyclopedia":
        from core.config import AppConfig

        if not web_allowed():
            return _refuse_web(str(args.get("topic", "") or original_query))

        from Utils.limbs.web_search import gather_context, wiki_summary

        # Never look up someone the user calls their own. "my friend rohit told
        # me about this" produced a Wikipedia page for cricketer Rohit Sharma.
        # Those facts live in memory, not on the internet.
        if re.search(
            r"\bmy (friend|sister|brother|mom|mum|dad|father|mother|wife|"
            r"husband|son|daughter|colleague|boss|cousin|uncle|aunt|neighbour|"
            r"neighbor|teacher|partner)\b",
            (original_query or "").lower(),
        ):
            logging.info(
                "[tool_registry] refused encyclopedia lookup of a personal "
                f"relation in: {original_query!r}"
            )
            return _result("direct")

        topic = str(args.get("topic", "") or original_query).strip()

        # If the subject is already someone/something in memory, answer from
        # memory. "tell me more about rohit" returned the cricketer Rohit Sharma
        # while Rohit was the user's friend.
        if remember_store is not None and remember_store.mentions(topic):
            logging.info(
                f"[tool_registry] {topic!r} is known from memory; "
                "skipping encyclopedia lookup"
            )
            return _result("direct")

        # Local archive first when one is installed. Encyclopedic facts do not
        # go stale on a useful timescale, a disk read beats a network round
        # trip, and if the archive has no article this falls straight through
        # to the web - so the worst case is exactly the old behaviour.
        # Set prefer_offline_encyclopedia: false to always go online first.
        if getattr(AppConfig, "prefer_offline_encyclopedia", True):
            local = _offline_evidence(topic)
            if local:
                return _result("evidence", evidence=local)

        evidence = wiki_summary(topic)
        if not evidence:
            evidence = gather_context(
                topic,
                max_chars=AppConfig.web["max_context_chars"],
                max_results=AppConfig.web["max_results"],
                timeout=AppConfig.web["fetch_timeout_seconds"],
            )
        return _result("evidence", evidence=evidence)

    if name == "remember":
        # A deletion request must never become an insertion. "remove what you
        # just remembered about narendra modi" was routed here and stored
        # "remembers narendra modi".
        forget = _forget_request(original_query)
        if forget is not None:
            if remember_store is None:
                return _result("clarify", spoken="I have nothing stored yet.")
            removed = remember_store.forget(
                topic=forget["topic"],
                last=forget["last"],
                all_=forget.get("all", False),
            )
            if removed:
                logging.info(f"[tool_registry] forgot: {removed}")
                what = removed[0] if len(removed) == 1 else f"{len(removed)} entries"
                return _result("clarify", spoken=f"Forgotten - {what}.")
            return _result("clarify", spoken="I had nothing stored about that.")

        # A question is never a fact to store. "who is my friend" matched the
        # "my friend" trigger and tried to SAVE instead of answering. This is a
        # validator on the save path, not routing: it only blocks a write.
        q = (original_query or "").strip().lower()
        if q.endswith("?") or re.match(
            r"^(who|what|when|where|why|which|whose|how|do|does|did|is|are|can|"
            r"could|should|would|will|tell me)\b",
            q,
        ):
            logging.info(
                f"[tool_registry] refused to store a fact from a question: "
                f"{original_query!r}"
            )
            return _result("direct")

        fact = str(args.get("fact", "") or "").strip()
        category = str(args.get("category", "Facts")).strip()
        saved = False
        if remember_store is not None and fact:
            # Pass the original message so fabricated content is rejected.
            saved = remember_store.add_fact(category, fact, source=original_query)
        if not saved:
            # Nothing was stored -- the "fact" was ungrammatical, ungrounded, or
            # already known. Answer conversationally instead of acknowledging a
            # save that did not happen: "thanks" was being routed here and got
            # "I already had that noted."
            return _result("direct")
        return _result("memory", saved=True, fact=fact)

    # answer_directly, or anything unrecognised
    if name != "answer_directly":
        logging.warning(f"[tool_registry] unknown tool: {name!r}")

    # The clock/date/battery are authoritative on this machine -- never let the
    # model answer them from its own head.
    _what = device_state_for(original_query)
    if _what and assistant is not None:
        logging.info(
            f"[tool_registry] answering from device state ({_what}) instead of "
            f"the model: {original_query!r}"
        )
        assistant._execute_action(DEVICE_STATE_READS[_what], original_query)
        return _result("action")

    # Upgrade to a live lookup when the question is explicitly time-sensitive.
    # "who is the current prime minister" routed here and would have answered
    # from stale training data.
    if needs_fresh_data(original_query):
        from core.config import AppConfig

        # The upgrade path matters most for the offline promise: this is where
        # "who is the current prime minister" silently becomes a web lookup. If
        # the web is off, the honest answer is a refusal, NOT a fall-through to
        # answer_directly - that would answer a time-sensitive question from
        # stale training data, which is exactly the behaviour to avoid.
        if not web_allowed():
            return _refuse_web(original_query)

        from Utils.limbs.web_search import gather_context

        logging.info(
            f"[tool_registry] time-sensitive query, upgrading "
            f"answer_directly -> search_web: {original_query!r}"
        )
        evidence = gather_context(
            original_query,
            max_chars=AppConfig.web["max_context_chars"],
            max_results=AppConfig.web["max_results"],
            timeout=AppConfig.web["fetch_timeout_seconds"],
        )
        if evidence:
            return _result("evidence", evidence=evidence)

    return _result("direct")
