"""Soul loading, conversation context, chat log, and long-term memory."""

import json
import os
import re
from collections import deque
from datetime import datetime

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # -> Phoenix/
SOUL_PATH = os.path.join(_BASE, "core", "soul.md")
INTENT_RULES_PATH = os.path.join(_BASE, "core", "intents.md")
REMEMBER_PATH = os.path.join(_BASE, "data", "remember.md")
CHATLOG_PATH = os.path.join(_BASE, "data", "ChatLog.json")

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
    """Rolling window of recent turns, rendered into prompts.

    Persists to data/ChatLog.json so history survives a restart. Only the last
    `max_turns` are fed to the model (prompt length is the main latency cost),
    but the full log is kept on disk up to `max_log_entries`.
    """

    def __init__(
        self,
        max_turns: int = 8,
        path: str = CHATLOG_PATH,
        persist: bool = True,
        max_log_entries: int = 500,
    ):
        self._turns = deque(maxlen=max_turns)
        self.path = path
        self.persist = persist
        self.max_log_entries = max_log_entries
        self._log = []
        if self.persist:
            self._load()

    # ---- disk -------------------------------------------------------------

    def _load(self):
        """Read the log and seed the in-memory window with the last turns."""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._log = [e for e in data if isinstance(e, dict)]
        except FileNotFoundError:
            self._log = []
        except Exception:
            # A corrupt log must never stop Phoenix from starting.
            self._log = []

        pending_user = None
        for entry in self._log:
            role, msg = entry.get("role"), entry.get("message", "")
            if role == "user":
                pending_user = msg
            elif role == "assistant" and pending_user:
                self._turns.append((pending_user, msg))
                pending_user = None

    def _save(self):
        if not self.persist:
            return
        try:
            if len(self._log) > self.max_log_entries:
                self._log = self._log[-self.max_log_entries:]
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._log, f, ensure_ascii=False, indent=1)
        except Exception:
            pass  # never let logging break a reply

    # ---- api --------------------------------------------------------------

    def add(self, user_msg: str, assistant_msg: str):
        if not (user_msg and assistant_msg):
            return
        self._turns.append((user_msg, assistant_msg))
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._log.append({"role": "user", "message": user_msg, "at": stamp})
        self._log.append({"role": "assistant", "message": assistant_msg, "at": stamp})
        self._save()

    def render(self) -> str:
        from core.config import AppConfig

        if not self._turns:
            return ""
        return "\n".join(
            f"{AppConfig.user_name}: {u}\n{AppConfig.name}: {a}" for u, a in self._turns
        )

    def search(self, query: str, limit: int = 5) -> str:
        """Find past exchanges mentioning `query`, for recall across sessions."""
        words = [w for w in re.findall(r"[a-z]{3,}", (query or "").lower())
                 if w not in _STOPWORDS]
        if not words:
            return ""
        hits = []
        for entry in reversed(self._log):
            msg = entry.get("message", "")
            low = msg.lower()
            if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words):
                hits.append(f"{entry.get('role', '?')}: {msg}")
                if len(hits) >= limit:
                    break
        return "\n".join(reversed(hits))

    def history_size(self) -> int:
        return len(self._log)

    def clear(self):
        self._turns.clear()
        self._log = []
        self._save()


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

    def forget(self, topic: str = "", last: bool = False, all_: bool = False):
        """Remove stored facts. Returns the list of removed facts.

        `last=True` drops the most recently added entry ("forget that"), and a
        `topic` removes entries mentioning it ("forget about narendra modi").
        Without this, "remove what you just remembered" was routed to remember
        and ADDED an entry instead of deleting one.
        """
        lines = self.load().splitlines()
        fact_idx = [i for i, ln in enumerate(lines) if ln.startswith("- ")]
        if not fact_idx:
            return []

        def text_of(i):
            return re.sub(r"\s*<!--.*?-->\s*$", "", lines[i]).strip()[2:].strip()

        targets = []
        if all_:
            targets = list(fact_idx)
        elif last:
            targets = [fact_idx[-1]]
        elif topic:
            words = [
                w
                for w in re.findall(r"[a-z]{3,}", topic.lower())
                if w not in _STOPWORDS
            ]
            if words:
                for i in fact_idx:
                    low = text_of(i).lower()
                    if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words):
                        targets.append(i)
        if not targets:
            return []

        removed = [text_of(i) for i in targets]
        for i in sorted(targets, reverse=True):
            del lines[i]
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            return []
        return removed

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
        # A fact needs a SUBJECT. The model returned "is a foreman" for
        # "munir alam, my father, is a foreman" -- it dropped who. Reject
        # anything opening with a verb or a bare connective.
        # Articles are NOT listed here: "The user prefers dark mode" is the
        # canonical format intents.md asks for, and blacklisting "the" silently
        # rejected every preference. Bare fragments like "a foreman" are already
        # caught by the three-word minimum above.
        if re.match(
            r"^(told|said|mentioned|about|this|that|is|are|was|were|has|have|"
            r"had|likes?|liked|prefers?|preferred|works?|worked|lives?|lived|"
            r"wants?|owns?|uses?|does|did|and|but|so)\b",
            fact.lower(),
        ):
            return False
        if not self._is_grounded(fact, source):
            return False
        # A request is not a fact. "a joke on narendra modi" was stored as
        # "is a joke on narendra modi".
        if re.search(
            r"\b(joke|jokes|story|stories|poem|song|riddle|essay|recipe)\b",
            fact.lower(),
        ):
            return False
        if re.match(
            r"^\s*(tell|write|give|make|sing|show|read|explain|teach|find|play)\b",
            (source or "").lower(),
        ):
            return False
        if category not in VALID_CATEGORIES:
            category = "Facts"
        # Keep the file organised even when the model picks the wrong bucket:
        # "munir alam is kALY's father" was filed under Facts.
        if re.search(
            r"\b(father|mother|dad|mum|mom|brother|sister|friend|wife|husband|"
            r"son|daughter|cousin|uncle|aunt|colleague|boss|neighbour|neighbor|"
            r"teacher|partner)\b",
            fact.lower(),
        ):
            category = "People"

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
