"""Soul loading, conversation context, and long-term memory for Phoenix."""

import os
import re
from collections import deque
from datetime import datetime

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # -> Phoenix/
SOUL_PATH = os.path.join(_BASE, "core", "soul.md")
INTENT_RULES_PATH = os.path.join(_BASE, "core", "intents.md")
REMEMBER_PATH = os.path.join(_BASE, "data", "remember.md")

VALID_CATEGORIES = ("People", "Preferences", "Facts", "Projects")

# Words that must never on their own make a topic look "already known", or every
# lookup would be refused because remember.md happens to contain them.
# Words a rewritten fact may legitimately introduce that were not in the user's
# own sentence (grammar glue, framing, relationship nouns).
_FACT_ALLOWED = {
    "is", "are", "was", "were", "has", "have", "had", "the", "a", "an", "of",
    "to", "in", "on", "at", "and", "or", "s", "user", "users", "prefers",
    "prefer", "likes", "like", "dislikes", "works", "working", "named",
    "called", "his", "her", "their", "them", "they", "he", "she", "friend",
    "friends", "family", "name", "known", "uses", "building", "builds",
}

_STOPWORDS = {
    "the", "and", "for", "about", "user", "prefers", "likes", "friend",
    "his", "her", "their", "with", "from", "that", "this", "who", "what",
    "tell", "more", "know", "name", "person", "people", "mode", "dark",
}


def load_soul() -> str:
    """Read core/soul.md and substitute identity placeholders from AppConfig."""
    from core.config import AppConfig

    try:
        with open(SOUL_PATH, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return f"You are {AppConfig.name}, a concise desktop assistant."
    return (
        text.replace("{assistant_name}", AppConfig.name)
        .replace("{user_name}", AppConfig.user_name)
        .replace("{user_tags}", ", ".join(AppConfig.user_tags))
    )


_PROMPT_BEGIN = "<!-- PROMPT:BEGIN -->"
_PROMPT_END = "<!-- PROMPT:END -->"


def load_intent_rules(compact: bool = True) -> str:
    """Read core/intents.md - the editable tool-selection rulebook.

    compact=True (default) returns ONLY the delimited PROMPT block. This matters
    a lot: measured on this machine, sending the whole 7.1k-char file cost
    13.1-13.6s per routing decision and misrouted commands, while the ~600-char
    prompt block cost 1.5-3.0s and routed them correctly. Prompt length is the
    dominant latency cost.
    """
    from core.config import AppConfig

    try:
        with open(INTENT_RULES_PATH, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return ""

    if compact and _PROMPT_BEGIN in text and _PROMPT_END in text:
        text = text.split(_PROMPT_BEGIN, 1)[1].split(_PROMPT_END, 1)[0].strip()
    return (
        text.replace("{assistant_name}", AppConfig.name)
        .replace("{user_name}", AppConfig.user_name)
        .replace("{user_tags}", ", ".join(AppConfig.user_tags))
    )


class ConversationContext:
    """Rolling window of recent turns, rendered into prompts."""

    def __init__(self, max_turns: int = 8):
        self._turns = deque(maxlen=max_turns)

    def add(self, user_msg: str, assistant_msg: str):
        if user_msg and assistant_msg:
            self._turns.append((user_msg, assistant_msg))

    def render(self) -> str:
        from core.config import AppConfig

        if not self._turns:
            return ""
        return "\n".join(
            f"{AppConfig.user_name}: {u}\n{AppConfig.name}: {a}" for u, a in self._turns
        )

    def clear(self):
        self._turns.clear()


class RememberStore:
    """Reads and appends facts to data/remember.md, deduplicating on write."""

    def __init__(self, path: str = REMEMBER_PATH, max_entries: int = 200):
        self.path = path
        self.max_entries = max_entries
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(
                    "# Long-Term Memory\n\n## People\n## Preferences\n"
                    "## Facts\n## Projects\n"
                )

    def load(self) -> str:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _existing_facts(self) -> list:
        return [
            re.sub(r"\s*<!--.*?-->\s*$", "", ln).strip()[2:].strip()
            for ln in self.load().splitlines()
            if ln.startswith("- ")
        ]

    def mentions(self, topic: str) -> bool:
        """True if `topic` names something already in memory.

        Used to stop an encyclopedia lookup hijacking a name the user has told
        us about: "tell me more about rohit" must not return the cricketer
        Rohit Sharma when Rohit is the user's friend.
        """
        topic = (topic or "").strip().lower()
        if len(topic) < 3:
            return False
        stored = self.load().lower()
        words = [w for w in re.findall(r"[a-z]{3,}", topic) if w not in _STOPWORDS]
        if not words:
            return False
        return any(re.search(rf"\b{re.escape(w)}\b", stored) for w in words)

    @staticmethod
    def _is_grounded(fact: str, source: str) -> bool:
        """True if every content word in `fact` came from the user's message.

        A fabricated memory persists and poisons every later answer. Asked to
        note "my friend rohit told me about this", the model wrote "Rohit tells
        Kaly that he is a dragon in the game" -- inventing 'dragon' and 'game'.
        Anything the user did not actually say is rejected.
        """
        if not source:
            return True  # nothing to check against; other validators still apply
        src = set(re.findall(r"[a-z0-9]+", source.lower()))
        invented = [
            w
            for w in re.findall(r"[a-z0-9]+", fact.lower())
            if w not in src and w not in _FACT_ALLOWED and len(w) > 2
        ]
        return len(invented) == 0

    def add_fact(self, category: str, fact: str, source: str = "") -> bool:
        """Append a fact under `category`. Returns False if duplicate/invalid/full.

        `source` is the user's original message; when given, the fact must be
        grounded in it.
        """
        fact = (fact or "").strip().rstrip(".")
        # Models sometimes leak the JSON scaffolding into the value itself.
        fact = re.sub(r"\b(extra|arg|category|tool)\s*:\s*", "", fact).strip(" ,;:")
        if not fact or len(fact) > 200:
            return False
        # Reject junk the model sometimes emits: a bare name ("moin"), or a
        # fragment that states nothing ("told me about this"). A usable fact
        # needs a subject and at least a few words.
        if len(fact.split()) < 3:
            return False
        if re.match(r"^(told|said|mentioned|about|this|that)\b", fact.lower()):
            return False
        if not self._is_grounded(fact, source):
            return False
        if category not in VALID_CATEGORIES:
            category = "Facts"

        existing = self._existing_facts()
        if len(existing) >= self.max_entries:
            return False
        low = fact.lower()
        for e in existing:  # dedupe, incl. near-duplicates
            if not e:
                continue
            if low == e.lower() or low in e.lower() or e.lower() in low:
                return False

        stamp = datetime.now().strftime("%Y-%m-%d")
        lines = self.load().splitlines()
        header = f"## {category}"
        try:
            idx = lines.index(header)
        except ValueError:
            lines += [header]
            idx = len(lines) - 1
        lines.insert(idx + 1, f"- {fact}  <!-- {stamp} -->")

        with open(self.path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
