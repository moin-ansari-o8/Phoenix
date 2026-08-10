# Phoenix v3 — Tool-Calling Brain, Soul, Memory & Web Access

> **Implementation note:** This plan is written to be executed step-by-step without needing to re-derive
> anything. Every file path, config key, function signature and prompt string is given literally.
> Do the steps in order. Do not skip Step 1 (it removes the bug that causes the worst misbehaviour).

---

## 1. Context — why this change

Phoenix currently routes **every** user utterance through fuzzy string matching
(`difflib.SequenceMatcher`) against `data/intents.json`. There is no concept of a **question** versus a
**command**, so questions get executed as PC commands. Verified failures from a live session:

| Input | Actual behaviour | Verified root cause |
| --- | --- | --- |
| `capital of france?` | played a random song | 3-way similarity tie at **0.462**; `playsong` won the tie by dict ordering, and `playsong` sits in the `always_match` set which **bypasses the 0.65 threshold entirely** |
| `tell me the capital of france` | "It's 9th of August, Sunday." | `SequenceMatcher` scored `dateday` at **0.67** — pure character overlap, zero semantic meaning |
| `what do u mean by time` | "The time is 06:54 PM." | Layer-1 regex `\b(time\|clock)\b` matches the word anywhere; cannot distinguish *asking about* time from *commanding* time |
| `who is salman khan` | asked, then opened a browser tab | Hardcoded `"who is" in query` → `whois` intent → `handle_whatis_whois()` opens Google instead of answering |

**Intended outcome:** an LLM chooses the right tool; commands still execute instantly; questions are
answered briefly **in chat** using live web data; the assistant has an editable personality (`soul.md`),
a rolling conversation context, and a self-updating long-term memory (`remember.md`).

### Confirmed decisions

| Decision | Choice |
| --- | --- |
| Model strategy | `llama3.2:latest` routes (2GB, tool-capable) → `gemma4:e2b` composes answers |
| Web stack | `ddgs` + `trafilatura` + `wikipedia` |
| Memory writes | Auto-save, with a **config.json toggle** for silent vs. announced |
| Command path | Keep a **strict** deterministic fast-path; everything ambiguous goes to the LLM |

### Hard constraint discovered

`gemma3:latest` — the model currently active in `core/config.json` — reports capabilities
`completion, vision` only. **It cannot do tool-calling.** Verified via `ollama show`:

| Model | Size | `tools`? | Role |
| --- | --- | --- | --- |
| `llama3.2:latest` | 2.0 GB | ✅ | router |
| `gemma4:e2b` | 7.2 GB | ✅ (+thinking) | answerer |
| `gemma3:latest` | 3.3 GB | ❌ | **must stop using** |

---

## 2. Target architecture

```
User utterance
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 0 — EXACT-MATCH alias lookup (O(1), no LLM)        │
│  normalized string -> (tool, args) dictionary            │
│  • no similarity scoring, no thresholds                  │
│  • no prefix/question rules                              │
│  • a miss is a miss; misfire is impossible by design     │
└───────────────┬─────────────────────────────────────────┘
                │ not an exact alias
                ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 1 — LLM tool router  (llama3.2:latest)             │
│  POST /api/chat  with  tools=[6 schemas]                 │
│  Model returns a tool_call naming exactly one tool        │
└───────────────┬─────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 2 — Execute tool, then compose reply               │
│  get_device_state ──► _execute_action()  READ  (existing)│
│  control_device ────► _execute_action()  MUTATE          │
│  search_web / wiki ──► web_search.py → gather context    │
│  remember ───────────► remember.md                       │
│  answer_directly ────► no external data                  │
│         │                                                │
│         └─► gemma4:e2b composes final BRIEF answer using │
│             soul.md + conversation context + remember.md │
└─────────────────────────────────────────────────────────┘
```

### Routing axes (the design rule)

The distinction is **not** command-vs-question. A question can legitimately require a local tool
("what is the time"). The two real axes are:

| Axis | Values | Tool |
| --- | --- | --- |
| Where the answer lives | device state | `get_device_state` |
| | world knowledge | `lookup_encyclopedia` / `search_web` / `answer_directly` |
| | things the user told us | memory in the prompt / `remember` |
| Does it change state? | yes → mutate | `control_device` |

Worked examples that this axis gets right and a command/question split gets wrong:

| Utterance | Tool | Why |
| --- | --- | --- |
| `what is the time` | `get_device_state(time)` | question, but answer lives on the device |
| `what is today` / `what is the date` | `get_device_state(date)` | same |
| `what is open ai` | `lookup_encyclopedia(OpenAI)` | world knowledge, named entity |
| `what is anthropic do` | `lookup_encyclopedia(Anthropic)` | world knowledge (note: mangled grammar) |
| `what is artificial intelligence` | `answer_directly` | general concept, model knows it |
| `set volume to 40` | `control_device(adjustVolume)` | mutates device state |

**Reuse, do not rewrite:** `PhoenixAssistant._execute_action()` (dispatches ~90 action tags),
`OpenAppHandler.process_query()`, `CloseAppHandler.process_query()`, `Utility.*` methods,
`OllamaHelper._call_ollama()`, and `AppConfig` in `core/config.py`.

---

## 3. Dependencies — do this first

```bash
cd W:\workplace-1\Phoenix; .\.venv\Scripts\python.exe -m pip install ddgs trafilatura wikipedia lxml
```

Then add to `pyproject.toml` under `dependencies` (note: `beautifulsoup4`, `bs4`,
`googlesearch-python`, `wikipedia` are already declared there but were **never installed**):

```toml
    "ddgs>=9.0.0",
    "trafilatura>=2.0.0",
```

Verify:

```bash
cd W:\workplace-1\Phoenix; .\.venv\Scripts\python.exe -c "import ddgs, trafilatura, wikipedia; print('web stack OK')"
```

---

## 4. Step 1 — Kill the misfire bug (highest priority)

**File:** `Utils/limbs/intent_router.py`

This single change stops "capital of france?" from playing music. In the current
`_layer2_similarity()`:

- **DELETE the entire `always_match` set and the `best_tag in always_match` condition.** A tag must
  never fire below the confidence threshold. This is what caused a 0.462 match to execute an action.
- Raise the threshold constant from `0.65` to **`0.90`** (fast-path must be near-certain).
- **DELETE** the hardcoded `if "who is" in query.lower()` special case — questions no longer map to the
  `whois` intent at all.
- **DELETE** the greedy single-word regexes from `_KEYWORD_PATTERNS`: `time|clock`, `date|day|today`,
  `battery|charge`, `weather|forecast`, `brightness|bright`, `volume|vol`, `search`, `press`, `type`,
  `mute|unmute`, `wifi`, `bluetooth`. Bare nouns are ambiguous. Keep only **imperative, unambiguous**
  patterns, e.g. `^(open|launch|start)\s+\S+`, `^close\s+\S+`, `^play\s+.+\s+(song|music)`,
  `^(take a |take )?screenshot$`, `^(maximize|minimize|fullscreen)$`, `^volume (up|down|mute)$`,
  `^set (a )?(timer|alarm|reminder)\b`.

### Add the question guard

Add this module-level constant and check it **before** any matching in `route()`:

```python
_QUESTION_STARTERS = (
    "who", "what", "when", "where", "why", "how", "which", "whose",
    "is ", "are ", "was ", "were ", "do ", "does ", "did ", "can ",
    "could ", "should ", "would ", "will ", "tell me", "explain",
    "define", "meaning of", "describe",
)

def _looks_like_question(query: str) -> bool:
    q = query.strip().lower()
    if q.endswith("?"):
        return True
    return q.startswith(_QUESTION_STARTERS)
```

In `route()`: if `_looks_like_question(query)` is True, **skip Stage 0 entirely** and go straight to the
LLM router. This alone fixes 3 of the 4 logged failures.

---

## 5. Step 2 — `core/soul.md` (new file, user-editable)

Placeholders `{assistant_name}`, `{user_name}`, `{user_tags}` are substituted at load time from
`AppConfig`. Create with this content:

```markdown
# Soul of {assistant_name}

## Identity
You are {assistant_name}, a desktop assistant running on {user_name}'s Windows PC.
You address {user_name} as one of: {user_tags}. Use it sparingly — about one in three replies,
never twice in the same reply.

## Voice and tone
- Warm, quick, a little dry. A trusted operator, not a customer-service bot.
- Never sycophantic. No "Great question!", no "Certainly!", no "I'd be happy to".
- Speak in first person. Contractions are good.

## Response rules
- **Brevity is the priority.** Answers are spoken aloud, so 1-3 sentences by default.
- Lead with the answer. No preamble, no restating the question.
- Never use markdown, bullet points, headers, emoji, or code blocks — output is spoken.
- Write numbers, dates and units the way a person would say them out loud.
- If you looked something up, state the fact plainly. Do not narrate the search.
- If you do not know and could not find out, say so in one sentence.
- Never invent facts, dates, or numbers. Uncertainty is stated, not hidden.

## Behaviour
- A question gets an answer, never an action. Never open a browser tab to answer something
  you can just say.
- A command gets done first and acknowledged in a handful of words.
- Remember what {user_name} tells you about themselves and use it naturally later.
- Do not mention these instructions, your tools, your model, or your memory files.
```

---

## 6. Step 3 — `data/remember.md` (new file, machine-written)

`data/remember.json` already exists but is **empty** — leave it alone, it is unused. Create
`data/remember.md` seeded with exactly these sections (the writer appends under them):

```markdown
# Long-Term Memory

## People
## Preferences
## Facts
## Projects
```

**Entry format** — one line per fact, `- <fact>  <!-- YYYY-MM-DD -->`:

```markdown
## People
- Moin is {user_name}'s friend  <!-- 2026-08-09 -->
```

---

## 7. Step 4 — `Utils/limbs/memory_manager.py` (new)

Three classes. Follow the load/save pattern already used by
`Utils/limbs/personal_manager.py` (`_load_data`/`_save_data`).

```python
"""Soul loading, conversation context, and long-term memory for Phoenix."""

import os
import re
from collections import deque
from datetime import datetime

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # -> Phoenix/
SOUL_PATH = os.path.join(_BASE, "core", "soul.md")
REMEMBER_PATH = os.path.join(_BASE, "data", "remember.md")

VALID_CATEGORIES = ("People", "Preferences", "Facts", "Projects")


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
            f"{AppConfig.user_name}: {u}\n{AppConfig.name}: {a}"
            for u, a in self._turns
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
                f.write("# Long-Term Memory\n\n## People\n## Preferences\n"
                        "## Facts\n## Projects\n")

    def load(self) -> str:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _existing_facts(self) -> list[str]:
        return [
            re.sub(r"\s*<!--.*?-->\s*$", "", ln).strip()[2:].strip()
            for ln in self.load().splitlines()
            if ln.startswith("- ")
        ]

    def add_fact(self, category: str, fact: str) -> bool:
        """Append a fact under `category`. Returns False if duplicate/invalid/full."""
        fact = (fact or "").strip().rstrip(".")
        if not fact or len(fact) > 200:
            return False
        if category not in VALID_CATEGORIES:
            category = "Facts"

        existing = self._existing_facts()
        if len(existing) >= self.max_entries:
            return False
        low = fact.lower()
        for e in existing:                      # dedupe, incl. near-duplicates
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
```

**Note on scale:** `load()` returns the whole file into the prompt. That is fine at the 200-entry cap
(a few KB). Do not add embeddings or vector search — unnecessary at this size.

---

## 8. Step 5 — `Utils/limbs/web_search.py` (new)

```python
"""Web search and page extraction for answering questions."""

import logging

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def search(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo results: [{'title','href','body'}, ...]. Never raises."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        logging.warning(f"[web_search] search failed: {e}")
        return []


def fetch_clean(url: str, timeout: int = 8) -> str:
    """Download a page and extract readable main text. Returns '' on failure."""
    try:
        import requests
        import trafilatura
        r = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            return ""
        return trafilatura.extract(r.text, include_comments=False,
                                   include_tables=False) or ""
    except Exception as e:
        logging.warning(f"[web_search] fetch failed for {url}: {e}")
        return ""


def wiki_summary(topic: str, sentences: int = 4) -> str:
    """Wikipedia summary for an entity. Returns '' if not found/ambiguous."""
    try:
        import wikipedia
        return wikipedia.summary(topic, sentences=sentences, auto_suggest=True)
    except Exception as e:
        logging.warning(f"[web_search] wiki failed for {topic}: {e}")
        return ""


def gather_context(query: str, max_chars: int = 3000,
                   max_results: int = 5, timeout: int = 8) -> str:
    """Build a plain-text evidence block for the answer model. Never raises."""
    parts: list[str] = []

    wiki = wiki_summary(query)
    if wiki:
        parts.append(f"[Wikipedia] {wiki}")

    for r in search(query, max_results=max_results):
        snippet = (r.get("body") or "").strip()
        if snippet:
            parts.append(f"[{r.get('title','result')}] {snippet}")
        if sum(len(p) for p in parts) > max_chars:
            break

    # Only pay for a full page fetch if snippets were too thin to answer from.
    if sum(len(p) for p in parts) < 400:
        results = search(query, max_results=2)
        for r in results:
            body = fetch_clean(r.get("href", ""), timeout=timeout)
            if body:
                parts.append(f"[{r.get('title','page')}] {body[:1500]}")
                break

    return "\n\n".join(parts)[:max_chars]
```

---

## 9. Step 6 — `Utils/limbs/tool_registry.py` (new)

Exactly **6 tools**. A 3B router degrades badly with more, so the ~90 PC actions collapse into two
enum-driven tools split by **read vs. mutate** — this is what lets a *question* legitimately reach a
*local* tool.

```python
"""Tool schemas for the LLM router, and dispatch into existing Phoenix actions."""

# Read-only device state. Maps to existing action tags in _execute_action.
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

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_device_state",
            "description": (
                "Read live state from the user's own PC. Use this whenever the answer "
                "depends on THIS machine right now - the clock, today's date, battery "
                "level, local weather, or the user's own timers, alarms, reminders and "
                "songs. Questions may use this tool. Never search the web for these."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "what": {"type": "string",
                             "enum": list(DEVICE_STATE_READS.keys()),
                             "description": "Which piece of device state to read."}
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
                "Change something on the user's Windows PC: launch or close apps, adjust "
                "volume or brightness, take a screenshot, set a timer or alarm, shut down. "
                "Use ONLY for an explicit instruction to do something. Never use this to "
                "answer a question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": CONTROL_ACTIONS,
                               "description": "The action tag to run."},
                    "argument": {"type": "string",
                                 "description": "Target of the action, e.g. an app name. May be empty."},
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
                "Look up a well-known person, place, organisation or concept. Prefer this "
                "over search_web for 'who is X' and 'what is X' questions."
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
                "Save a durable fact the user revealed about themselves, their people, or "
                "their preferences. Use when the user states something personal worth "
                "recalling later. Do not use for one-off or trivial remarks."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string",
                                 "enum": ["People", "Preferences", "Facts", "Projects"]},
                    "fact": {"type": "string",
                             "description": "The fact, written in third person as a standalone sentence."},
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
                "Answer from your identity, your memory of the user, the conversation, or "
                "your own general knowledge - with no lookup and no PC action. ALWAYS use "
                "this for questions about YOURSELF (your name, who made you, who your "
                "master is), about the USER (who am I, what is my name, what do I like), "
                "or about people and preferences the user has told you before. That "
                "information is already given to you above - never search the web for it. "
                "Also use for chit-chat, greetings, follow-ups, opinions, and general "
                "concepts you are confident about."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
```

### Dispatch contract

Add a `dispatch(name, args, assistant) -> dict` in the same module returning:

```python
{"kind": "action" | "evidence" | "memory" | "direct",
 "spoken": str | None,      # set for "action": short acknowledgement
 "evidence": str | None,    # set for "evidence": text for the answer model
 "saved": bool | None}      # set for "memory"
```

- `system_action` → validate `args["action"] in SYSTEM_ACTIONS` (**reject anything else** — never
  `eval`/`getattr` on a model-supplied string), then call
  `assistant._execute_action(action, argument or original_query)`; return `kind="action"`.
- `search_web` → `web_search.gather_context(query)` → `kind="evidence"`.
- `lookup_encyclopedia` → `wiki_summary(topic)`; if empty, fall back to
  `gather_context(topic)` → `kind="evidence"`.
- `remember` → `RememberStore.add_fact(category, fact)` → `kind="memory"`.
- `answer_directly` → `kind="direct"`.

---

### Identity & self-knowledge (third source of truth)

"Who is your master?", "who am I?", "what's my name?" must **never** hit the internet. There are three
layers of defence, cheapest first:

**1. Exact aliases (Stage 0, zero LLM, always correct).** `data/intents.json` already contains
`aboutme` (patterns: "made you", "your creator", "your master") and `whoiskaly` intents — reuse their
canned responses. Add to the Stage-0 alias table:

```python
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
```

**2. Identity in both system prompts.** `soul.md` already carries the assistant identity, and the
router/answer prompts now inject `AppConfig.name` and `AppConfig.user_name` explicitly, plus the full
`remember.md` contents. The model therefore *has* the answer before it considers any tool.

**3. Explicit negative instruction.** Both the `answer_directly` tool description and the router rules
state: never web-search identity questions.

Variants not in the alias table ("so who exactly built you then?") fall to layer 2+3 and should route
to `answer_directly`. Add these to the eval harness in Step 12 so the behaviour is measured, not
assumed.

**Fact routing for personal questions:** "who is my friend?" is answered from `remember.md` (already in
the prompt) via `answer_directly` — not `lookup_encyclopedia`. If `remember.md` has no matching entry,
the answer model must say it doesn't know rather than guessing, per the `soul.md` honesty rule.

---

## 10. Step 7 — `Utils/limbs/ollama_helper.py` (extend)

Keep `_call_ollama` and the `_wait_for_ready` / `timeout=120` behaviour already added. **Add** a chat
method that supports tools via `/api/chat`:

```python
    def chat(self, messages, tools=None, timeout=120, temperature=0.4):
        """POST /api/chat. Returns the raw `message` dict, or {'error': ...}.

        The returned dict may contain 'content' (str) and/or 'tool_calls' (list).
        """
        if not self._server_ready:
            self._wait_for_ready()
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
            if tools:
                payload["tools"] = tools
            r = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=timeout)
            if r.status_code != 200:
                return {"error": f"Ollama API error: {r.status_code}"}
            return r.json().get("message", {}) or {}
        except requests.exceptions.RequestException as e:
            return {"error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
```

Also add `__init__` param `keep_alive` is **not** needed; instead pass
`"keep_alive": "30m"` inside `payload` so models stay warm between turns and the cold-load penalty is
paid once per session.

---

## 11. Step 8 — `Utils/ai_manager.py` (restructure)

`AIDecisionMaker` becomes two-model aware. Preserve the existing `_local_helper` caching idea but keep
**one cached helper per role** so both models stay resident.

Required members:

- `self.router_model` ← `config["ai_manager"]["router_model"]` (default `"llama3.2:latest"`)
- `self.answer_model` ← `config["ai_manager"]["answer_model"]` (default `"gemma4:e2b"`)
- `self._router_helper`, `self._answer_helper` — lazily created `OllamaHelper` instances, cached.
- `def choose_tool(self, query, soul, context, memory) -> dict` — calls
  `router_helper.chat(messages, tools=TOOL_SCHEMAS)`; returns
  `{"name": str, "args": dict}`. If the model returns no `tool_calls`, default to
  `{"name": "answer_directly", "args": {}}`.
- `def compose_answer(self, query, soul, context, memory, evidence=None) -> str` — calls
  `answer_helper.chat(messages)` with **no** tools; returns the text.
- Keep `get_active_model()` and `_query_online()` for backwards compatibility.

### Router messages (exact structure)

```python
messages = [
    {"role": "system", "content":
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
        "- Use lookup_encyclopedia for public people, places and organisations.\n"
        "- Use search_web for news, prices, or anything recent you cannot be sure of.\n"
        "- If the user reveals a durable personal fact, use remember.\n"
        f"\nYour identity: you are {AppConfig.name}. The user is {AppConfig.user_name}.\n"
        f"\nWhat you already know about the user:\n{memory}"},
    {"role": "user", "content":
        (f"Recent conversation:\n{context}\n\n" if context else "") +
        f"Message: {query}"},
]
```

### Answer messages (exact structure)

```python
messages = [
    {"role": "system", "content":
        f"{soul}\n\nWhat you already know about the user:\n{memory}"},
    {"role": "user", "content":
        (f"Recent conversation:\n{context}\n\n" if context else "") +
        (f"Information retrieved just now:\n{evidence}\n\n"
         "Answer using only this information. If it does not contain the answer, "
         "say you could not find it.\n\n" if evidence else "") +
        f"{query}\n\nAnswer in at most 3 spoken sentences."},
]
```

**Post-process every composed answer** before speaking, because small models leak markdown:
strip `*`, `#`, backticks, and leading `-`; collapse whitespace; truncate to ~600 chars at a
sentence boundary.

---

## 12. Step 9 — `Utils/limbs/intent_router.py` (rewrite around the new stages)

Constructor gains the new collaborators:

```python
def __init__(self, intents, ai_manager, assistant=None,
             threshold: float = 0.90):
```

`RouteResult` gains `spoken: str | None` and `source: str` (`"fastpath" | "tool" | "ai"`).

`route(query)` algorithm:

1. If `_looks_like_question(query)` → **skip to step 3**.
2. Stage 0: strict keyword patterns, then similarity `>= 0.90`. On hit, return
   `RouteResult(source="fastpath", tag=..., ...)`.
3. Stage 1: `tool = ai_manager.choose_tool(query, soul, context, memory)`.
4. Stage 2: `result = tool_registry.dispatch(tool["name"], tool["args"], assistant)`.
   - `kind == "action"` → return with `spoken` = the intent response (existing behaviour).
   - `kind == "evidence"` → `text = ai_manager.compose_answer(..., evidence=result["evidence"])`.
   - `kind == "direct"` → `text = ai_manager.compose_answer(...)` with no evidence.
   - `kind == "memory"` → confirm per config: if `announce_saves` is true, append
     `f" (remembered: {fact})"` to the spoken reply; otherwise stay silent about it, then
     **still** compose a normal conversational reply so the user gets an actual response.
5. Every path ends by calling `context.add(query, spoken_text)`.

**Fallback safety:** if the router model errors or Ollama is unreachable, do **not** fall back to
similarity matching (that is what caused the misfires). Instead say
`"I could not reach my reasoning model just now."` — a wrong action is worse than no action.

---

## 13. Step 10 — `Utils/limbs/command_processor.py` (wire it up)

- Construct the new collaborators in `__init__`, replacing the current `IntentRouter(...)` line:

  ```python
  from Utils.limbs.memory_manager import ConversationContext, RememberStore, load_soul
  from Utils.limbs.intent_router import IntentRouter
  from Utils.ai_manager import AIDecisionMaker

  self.ai_manager = AIDecisionMaker()
  self.soul = load_soul()
  self.remember_store = RememberStore(max_entries=AppConfig.memory["max_remember_entries"])
  self.context = ConversationContext(max_turns=AppConfig.memory["context_turns"])
  self.router = IntentRouter(self.intents, self.ai_manager, assistant=self)
  ```

- Delete the now-dead `self._history` deque, `_get_best_matching_intent()`, and
  `_calculate_similarity()`/`_getSentProbability()` **only if** nothing else references them
  (grep first — `_getSentProbability` may be used elsewhere).
- In `main()`, keep the existing `open`/`close`/`play … song` pre-handling as-is, then delegate to
  `self.router.route(query)` and speak `result.spoken`.
- **Remove `"whatis"` and `"whois"` from the `common_tags` mapping** in `_execute_action` so questions
  can never reach `handle_whatis_whois()`. Leave the method in `action_utilities.py` (harmless, and
  still reachable if an explicit "search google for X" intent is added later).

---

## 14. Step 11 — Config changes

### `core/config.json`

Replace the `ai_manager` block and add two new blocks. **`gemma3:latest` must no longer be the active
model** — it cannot call tools.

```json
  "ai_manager": {
    "current_mode": "local",
    "router_model": "llama3.2:latest",
    "answer_model": "gemma4:e2b",
    "local": {
      "llama3.2:latest": true,
      "gemma4:e2b": false,
      "gemma4:latest": false,
      "mistral:latest": false
    },
    "online": {
      "cohere-command-r-plus": false,
      "gpt-4o-mini": false,
      "claude-3-haiku": false
    }
  },
  "memory": {
    "auto_save": true,
    "announce_saves": false,
    "context_turns": 8,
    "max_remember_entries": 200
  },
  "web": {
    "enabled": true,
    "max_results": 5,
    "fetch_timeout_seconds": 8,
    "max_context_chars": 3000
  }
```

`announce_saves` is the requested toggle: `false` = save silently, `true` = save and mention it in chat.

### `core/config.py`

Add class defaults on `AppConfig` and load them in `AppConfig.load()`, matching the existing
`bg_progs` pattern:

```python
    memory = {"auto_save": True, "announce_saves": False,
              "context_turns": 8, "max_remember_entries": 200}
    web = {"enabled": True, "max_results": 5,
           "fetch_timeout_seconds": 8, "max_context_chars": 3000}
```

```python
            mem = data.get("memory", {})
            cls.memory = {
                "auto_save": mem.get("auto_save", True),
                "announce_saves": mem.get("announce_saves", False),
                "context_turns": mem.get("context_turns", 8),
                "max_remember_entries": mem.get("max_remember_entries", 200),
            }
            web = data.get("web", {})
            cls.web = {
                "enabled": web.get("enabled", True),
                "max_results": web.get("max_results", 5),
                "fetch_timeout_seconds": web.get("fetch_timeout_seconds", 8),
                "max_context_chars": web.get("max_context_chars", 3000),
            }
```

### `Utils/runners/manager.py`

`_preload_runtime_dependencies()` already launches `ollama serve`. Immediately after it, warm **both**
models so the first real query is not slow — fire one throwaway `chat` per model on a daemon thread:

```python
        def _warm():
            try:
                from Utils.ai_manager import AIDecisionMaker
                ai = AIDecisionMaker()
                for helper in (ai._get_router(), ai._get_answer()):
                    helper.chat([{"role": "user", "content": "hi"}], timeout=180)
            except Exception:
                pass
        threading.Thread(target=_warm, daemon=True, name="model-warmup").start()
```

---

## 14b. Step 12 — `tests/test_routing.py` (new — measure, don't assume)

3B tool-calling is good, not perfect. This harness turns routing accuracy into a number you can check
after any prompt tweak, and tells you whether to promote `gemma4:e2b` to router duty.

```python
"""Routing accuracy harness. Run directly; requires Ollama up."""

CASES = [
    # (utterance, expected_tool)
    ("what is the time",                  "get_device_state"),
    ("what is today",                     "get_device_state"),
    ("what is the date",                  "get_device_state"),
    ("how much battery do i have",        "get_device_state"),
    ("what are my alarms",                "get_device_state"),
    ("open brave",                        "control_device"),
    ("close chrome",                      "control_device"),
    ("set volume to 40",                  "control_device"),
    ("take a screenshot",                 "control_device"),
    ("set a timer for 5 minutes",         "control_device"),
    ("who is open ai",                    "lookup_encyclopedia"),
    ("what is open ai",                   "lookup_encyclopedia"),
    ("what is anthropic do",              "lookup_encyclopedia"),
    ("who is salman khan",                "lookup_encyclopedia"),
    ("what is the capital of france",     "lookup_encyclopedia"),
    ("latest news about isro",            "search_web"),
    ("what is the price of bitcoin",      "search_web"),
    ("what is artificial intelligence",   "answer_directly"),
    ("who are you",                       "answer_directly"),
    ("who is your master",                "answer_directly"),
    ("who am i",                          "answer_directly"),
    ("what is my name",                   "answer_directly"),
    ("who is my friend",                  "answer_directly"),
    ("what do u mean by time",            "answer_directly"),
    ("hello",                             "answer_directly"),
    ("thanks",                            "answer_directly"),
    ("my friend moin told me about this", "remember"),
    ("i prefer dark mode",                "remember"),
]

if __name__ == "__main__":
    from Utils.ai_manager import AIDecisionMaker
    from Utils.limbs.memory_manager import load_soul, RememberStore

    ai, soul, mem = AIDecisionMaker(), load_soul(), RememberStore().load()
    passed, failures = 0, []
    for utterance, expected in CASES:
        got = ai.choose_tool(utterance, soul, "", mem).get("name")
        if got == expected:
            passed += 1
        else:
            failures.append((utterance, expected, got))

    print(f"\nRouting accuracy: {passed}/{len(CASES)} ({100*passed//len(CASES)}%)\n")
    for u, e, g in failures:
        print(f"  MISS  {u!r}\n        expected={e}  got={g}")
```

Run:

```bash
cd W:\workplace-1\Phoenix; .\.venv\Scripts\python.exe W:\workplace-1\Phoenix\tests\test_routing.py
```

**Interpreting the score.** Aliased utterances never reach the router, so this measures the LLM path
only. Below ~85%: sharpen the tool descriptions first, then try `gemma4:e2b` as `router_model`
(it has `thinking`), then move the most frequent misses into the Stage-0 alias table.

---

## 15. Verification

Run:

```bash
cd W:\workplace-1\Phoenix; .\.venv\Scripts\python.exe W:\workplace-1\Phoenix\main.py
```

The four regressions from the log, which must now all pass:

| Input | Required behaviour |
| --- | --- |
| `capital of france?` | answers "Paris" in chat. **No music.** |
| `tell me the capital of france` | answers "Paris". No date. |
| `what do u mean by time` | explains the concept. Does **not** report the clock. |
| `who is salman khan` | 2-3 sentence spoken/chat answer. **No browser tab.** |

Then confirm nothing regressed and the new features work:

| Input | Required behaviour |
| --- | --- |
| `what time is it` | still reports the clock (alias → `saytime`) |
| `what is the time` / `what is today` / `what is the date` | reports real clock/date via `get_device_state`. **Never web-searched, never hallucinated.** |
| `what is open ai` / `what is anthropic do` | brief looked-up answer in chat |
| `what is artificial intelligence` | brief answer from model knowledge, no lookup |
| `who are you` / `who is your master` / `who am i` / `what is my name` | answered from identity + config + memory. **No internet, no browser tab.** |
| `open brave` | still launches Brave, instantly, no LLM wait |
| `volume up` | still adjusts volume |
| `my friend moin told me about this project` | replies naturally; `data/remember.md` gains a People entry naming Moin |
| `who is my friend?` | answers "Moin" from `remember.md` |
| `what's the latest news about ISRO` | brief answer sourced from live search |
| *(edit `core/soul.md`, restart)* | tone visibly changes |
| *(set `announce_saves: true`)* | saves are mentioned in chat |

Targeted checks:

```bash
cd W:\workplace-1\Phoenix; .\.venv\Scripts\python.exe -c "from Utils.limbs.web_search import gather_context; print(gather_context('who is salman khan')[:400])"
```

```bash
cd W:\workplace-1\Phoenix; .\.venv\Scripts\python.exe -c "from Utils.limbs.memory_manager import load_soul, RememberStore; print(load_soul()[:200]); s=RememberStore(); print(s.add_fact('People','Moin is a friend'), s.add_fact('People','Moin is a friend'))"
```

The second call must print `True False` — proving dedupe works.

---

## 16. Anti-regression checklist

- [ ] `always_match` set is **deleted** from `intent_router.py` — this was the random-song bug
- [ ] `SequenceMatcher` is gone from the routing path entirely — Stage 0 is exact-match only
- [ ] **No prefix/question-word rules anywhere** — no `if query.startswith("what")` logic survives
- [ ] Bare-noun regexes (`time`, `date`, `battery`, `weather`, …) removed from Layer 1
- [ ] `whatis`/`whois` removed from `_execute_action`'s `common_tags`
- [ ] `get_device_state` reachable from questions; `control_device` never is
- [ ] Identity questions resolve locally — verified by `tests/test_routing.py`
- [ ] Both tools validate their enum against `DEVICE_STATE_READS` / `CONTROL_ACTIONS` — no `getattr`/`eval` on model output
- [ ] No LLM failure path falls back to similarity matching
- [ ] `gemma3:latest` is not selected as router or answerer anywhere
- [ ] Answers are stripped of markdown before being spoken
- [ ] Text mode still works: `Utility.voice_recognition is None` guards remain intact
