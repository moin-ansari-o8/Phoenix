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
                "Search the internet for current or factual information. Use for news, "
                "prices, weather elsewhere, sports, recent events, or anything you are "
                "not confident about."
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
    {
        "type": "function",
        "function": {
            "name": "lookup_encyclopedia",
            "description": (
                "Look up a FAMOUS, PUBLIC person, place, company or organisation that "
                "would have a Wikipedia article - for example Salman Khan, OpenAI, "
                "Anthropic, Tokyo, ISRO. "
                "DO NOT use this for: people in the user's own life (their friends, "
                "family, colleagues - those are in your memory); the user themselves; "
                "yourself; or the meaning of an ordinary English word or everyday "
                "concept. If the subject is not a named public entity, do not use "
                "this tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The subject to look up."}
                },
                "required": ["topic"],
            },
        },
    },
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
                "the web for it. Also use for chit-chat, greetings, follow-ups, "
                "opinions, and general concepts you are confident about."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

VALID_TOOL_NAMES = {t["function"]["name"] for t in TOOL_SCHEMAS}


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
        from Utils.limbs.web_search import gather_context

        query = str(args.get("query", "") or original_query).strip()
        evidence = gather_context(
            query,
            max_chars=AppConfig.web["max_context_chars"],
            max_results=AppConfig.web["max_results"],
            timeout=AppConfig.web["fetch_timeout_seconds"],
        )
        return _result("evidence", evidence=evidence)

    if name == "lookup_encyclopedia":
        from core.config import AppConfig
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
        fact = str(args.get("fact", "") or "").strip()
        category = str(args.get("category", "Facts")).strip()
        saved = False
        if remember_store is not None and fact:
            # Pass the original message so fabricated content is rejected.
            saved = remember_store.add_fact(category, fact, source=original_query)
        return _result("memory", saved=saved, fact=fact)

    # answer_directly, or anything unrecognised
    if name != "answer_directly":
        logging.warning(f"[tool_registry] unknown tool: {name!r}")
    return _result("direct")
