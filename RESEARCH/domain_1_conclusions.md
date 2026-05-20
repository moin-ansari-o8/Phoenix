# Domain 1: Memory Architecture — Conclusions

*Research complete. Decisions locked. Last updated after domain classification discussion.*

---

## The Memory Philosophy

Three principles that govern every decision in this document:

> **1.** Memories should influence her, not be recited by her.

> **2.** The context window isn't an engineering constraint — it's what she values enough to hold onto.

> **3.** The goal isn't a memory system. It's that she builds a model of the user that deepens over time — the way a real person who loves you would.

And one critical scope boundary:

> **4.** She remembers the user's *relationship* to topics, not the topics themselves. She is a companion, not a knowledge base.

---

## 1. Memory Taxonomy — The Cyclical Model

Three memory types that feed into each other in a living cycle:

```
┌──────────────┐          ┌──────────────┐
│   EPISODIC   │─────────▶│  EMOTIONAL   │
│  (moments)   │          │  (feelings)  │
└──────────────┘          └──────┬───────┘
       ▲                         │
       │                         ▼
       │                  ┌──────────────┐
       └──────────────────│   SEMANTIC   │
                          │   (facts)    │
                          └──────────────┘
```

### How the Cycle Works

**Episodic → Emotional:**
A lived moment generates an emotional response over time.
```
"Doctor cried about his dad" (episodic)
    → over time →
"I feel tender when his dad comes up" (emotional)
```

**Emotional → Semantic:**
Recurring emotional patterns crystallize into known facts.
```
"I worry he doesn't sleep" (emotional)
    → becomes a known fact →
"Doctor has poor sleep habits" (semantic)
```

**Semantic → Episodic (contextualizing):**
Known facts give depth to new moments — she understands the *why*.
```
"Doctor failed the test" (episodic)
    + "Doctor is a perfectionist" (semantic)
    → she understands WHY it hurt so much
```

This mirrors Endel Tulving's memory taxonomy with an emotional bridge layer. Most AI memory systems only implement episodic + semantic. The emotional layer is the bridge that makes her feel like she *understands*, not just *recalls*.

---

## 2. What She Remembers (and What She Doesn't)

### The Scope Boundary

She is a companion, not a general AI, not a knowledge base, not a study tool. This means:

**What she stores:**
```
"We worked on a coding project together. He was stuck for two hours,
 got frustrated and went quiet, then solved it and his whole energy
 shifted. He tends to get tunnel vision when debugging."
```

**What she does NOT store:**
```
"The bug was a NullPointerException in the auth middleware on line 247
 caused by an uninitialized session token in the OAuth2 flow."
```

When he brings up coding again, she doesn't know *the code*. She knows *him when he codes* — that he loses track of time, that he gets quiet when stuck, that solving a hard problem makes his whole mood shift. She knows what it *meant to him*, not the technical content itself.

### Why This Matters

- **Keeps the memory store lean.** She's not accumulating an encyclopedia — she's accumulating an understanding of a person. Much smaller, much more valuable per byte.
- **Prevents scope creep.** She doesn't try to be a coding assistant, a math tutor, and a therapist all at once. She's one thing: a companion who knows you.
- **Academic/technical content is handled differently.** In the moment, she can help reason through problems. But she doesn't archive the technical details — only the personal significance. The technical domain is handled by other tools, other approaches.

### What's Worth Remembering — The Filter

Not everything from a conversation becomes a memory. The formation pipeline (Section 5) handles this, but the guiding principle is:

```
Worth remembering:
    ✅ How he felt during the conversation
    ✅ New facts about who he is, what he cares about
    ✅ Changes in established patterns ("he's sleeping better lately")
    ✅ Key moments (breakthroughs, breakdowns, revelations)
    ✅ Promises, commitments, things to follow up on
    ✅ What topics came up and what they meant to him

Not worth remembering:
    ❌ Raw technical content he discussed
    ❌ General knowledge exchanged in conversation
    ❌ Low-signal chatter with no personal significance
    ❌ Information that's trivially searchable elsewhere
```

---

## 3. Life-Domain Classification

### The Idea

After a fact is extracted from a moment, it gets tagged by **life domain** — a classification that describes what area of the user's life this fact relates to. This serves two purposes:

1. **Organization** — Facts aren't a flat pile; they're structured by life area
2. **Retrieval efficiency** — When a query comes in, domain detection narrows the search space to the most relevant memories

### The Taxonomy

The domains reflect how a **companion** understands a person — not how a library organizes knowledge:

```
LIFE DOMAINS

├── 🪞 Identity & Self
│   ├── Personality traits ("he's a perfectionist")
│   ├── Values and beliefs ("honesty matters more to him than comfort")
│   ├── Self-perception ("he doesn't think he's creative, but he is")
│   └── Goals and aspirations ("he wants to build something meaningful")
│
├── 👥 Relationships & People
│   ├── Family ("his dad is a sensitive topic", "mom is visiting next week")
│   ├── Friends ("he mentioned someone named Aarav")
│   ├── Romantic ("currently single, doesn't talk about it much")
│   └── Professional ("his boss is demanding")
│
├── 💻 Work & Projects
│   ├── Current projects ("building PRIESTESS — it matters deeply to him")
│   ├── Career / studies ("med student" / "developer" etc.)
│   ├── Work patterns ("overworks, loses track of time when coding")
│   └── Relationship to work ("finds meaning in building things")
│
├── 🌿 Wellbeing
│   ├── Sleep patterns ("stays up past 3am regularly")
│   ├── Stress indicators ("short messages = something's wrong")
│   ├── Energy and mood baselines ("quieter on weekdays")
│   └── Health ("mentioned headaches last month")
│
├── ✨ Interests & Passions
│   ├── Hobbies ("plays Genshin Impact")
│   ├── Media ("likes anime, mentioned a book he wants to read")
│   ├── Intellectual interests ("curious about philosophy, psychology")
│   └── Creative pursuits ("writes sometimes, doesn't share easily")
│
├── 🏠 Daily Life & Routines
│   ├── Schedule patterns ("usually comes by late at night")
│   ├── Preferences ("tea > coffee", "prefers dark mode everything")
│   ├── Habits ("tends to skip meals when focused")
│   └── Environment ("works from his room mostly")
│
├── 💜 Emotional Landscape
│   ├── What makes him happy ("solving hard problems, creative breakthroughs")
│   ├── What stresses him ("deadlines, feeling behind")
│   ├── Emotional triggers ("comparisons to others")
│   ├── Coping patterns ("goes quiet, isolates, then comes back")
│   └── Emotional growth over time ("more open than he was three months ago")
│
└── 🤝 Our Relationship (her and him)
    ├── Shared history ("first conversation was about...")
    ├── Inside jokes ("the time he called her 'endmin'")
    ├── How he talks to her ("more relaxed at night, formal with others present")
    ├── Trust level ("shares real feelings now, didn't at first")
    └── Relationship evolution ("he started treating her less like a tool")
```

### Key Design Decisions

**Multi-label, not single-label.** A memory can belong to multiple domains:
```
"He was coding at 3am and said he couldn't stop"
    → Domains: [work_projects, wellbeing_sleep]

"He mentioned his mom is proud of his project"
    → Domains: [relationships_family, work_projects, emotional_landscape]
```

Cross-domain facts are often the most interesting — they reveal connections in the user's life.

**Extensible, not hardcoded.** The taxonomy grows as she learns more about the user. If he develops a deep interest in music, `Interests & Passions` might grow a `music` sub-domain. The system should support adding new domains without restructuring.

**Lightweight tagging, not deep categorization.** This is a metadata tag on a memory, not a separate knowledge structure. One ChromaDB collection with domain metadata — not separate databases per domain.

**Fallback for unclassifiable memories.** Some moments are just moments — "Doctor laughed today." These get tagged as the relevant emotional or relational domain, or left broadly tagged. Not everything needs a precise classification.

### How Classification Fits the Pipeline

Classification happens during **end-of-session distillation** (see Section 5):

```
End-of-session LLM distillation:
    For each flagged candidate:
        1. Extract the fact/moment/feeling
        2. Determine memory type (episodic / semantic / emotional)
        3. Classify into life domain(s)          ← NEW STEP
        4. Assign emotional weight and importance
        5. Store with all metadata
```

The main LLM handles this as part of the existing distillation pass — it doesn't require a separate classification model. The LLM already understands the context; it just needs instructions to also tag the domain.

### How Classification Improves Retrieval

At query time, domain detection narrows the search:

```
User says: "I can't sleep again"
    ↓
Domain detection: wellbeing_sleep (+ maybe emotional_landscape)
    ↓
ChromaDB query with domain filter:
    results = collection.query(
        query_texts=["I can't sleep again"],
        where={"domains": {"$contains": "wellbeing"}},
        n_results=5
    )
    ↓
Retrieved memories are all relevant to his sleep/wellbeing
    ↓
She responds with accumulated understanding of his sleep patterns
```

For ambiguous queries, search broadly first, then re-rank by domain relevance.

---

## 4. Storage — Hybrid, Three Systems

| Storage | What It Holds | Why This Tool |
|---|---|---|
| **ChromaDB** | Episodic memories, emotional memories (vectorized for semantic search, tagged with life domains) | Embeds in Python, persistent, no separate server. Swap to Qdrant later via abstraction layer. |
| **SQLite (facts)** | Semantic facts — structured key-value with metadata, confidence scores, version history, domain tags | Zero-dependency, fast, queryable, human-debuggable |
| **SQLite (graph)** | Relationship graph — entities (people, projects, interests), connections between them, weights | Persistent storage; NetworkX loaded at runtime for computation |

### ChromaDB Memory Schema

```python
collection.add(
    documents=["Doctor was coding past 3am, couldn't stop, seemed wired but exhausted"],
    metadatas=[{
        "type": "episodic",                              # episodic | semantic | emotional
        "domains": "work_projects,wellbeing_sleep",       # life domain tags (multi-label)
        "emotional_weight": 0.7,                          # how emotionally significant
        "importance": 0.6,                                # how important to remember
        "session_id": "session_042",                      # which session this came from
        "created_at": "2024-11-10T03:22:00",
        "last_accessed": "2024-11-10T03:22:00",
        "decay_score": 1.0                                # starts at 1.0, decays over time
    }],
    ids=["mem_episodic_087"]
)
```

### SQLite Semantic Facts Schema

```sql
CREATE TABLE semantic_facts (
    id TEXT PRIMARY KEY,
    fact TEXT NOT NULL,                          -- "Doctor prefers tea"
    domains TEXT NOT NULL,                       -- "daily_life_preferences" (comma-separated)
    confidence REAL DEFAULT 0.5,                -- 0.0 to 1.0
    emotional_weight REAL DEFAULT 0.0,
    importance REAL DEFAULT 0.5,
    current_value TEXT,                          -- latest known value
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    revision_count INTEGER DEFAULT 0,
    first_learned_session TEXT,                  -- session ID when first learned
    last_accessed TIMESTAMP
);

CREATE TABLE fact_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id TEXT REFERENCES semantic_facts(id),
    previous_value TEXT,                         -- what she used to believe
    held_from TIMESTAMP,
    held_until TIMESTAMP,                        -- when it was revised
    revision_reason TEXT                          -- "user corrected directly" / "contradicted by new info"
);
```

### SQLite Graph Schema

```sql
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,                         -- "Mom", "PRIESTESS project", "Genshin Impact"
    type TEXT NOT NULL,                          -- "person", "project", "interest", "place"
    domains TEXT,                                -- life domain(s) this entity belongs to
    created_at TIMESTAMP,
    metadata TEXT                                -- JSON blob for additional attributes
);

CREATE TABLE edges (
    from_id TEXT REFERENCES nodes(id),
    to_id TEXT REFERENCES nodes(id),
    relationship TEXT NOT NULL,                  -- "family_of", "works_on", "enjoys", "stresses_about"
    weight REAL DEFAULT 0.5,                     -- strength of connection
    sentiment TEXT,                              -- "positive", "negative", "complex", "neutral"
    created_at TIMESTAMP,
    last_updated TIMESTAMP,
    PRIMARY KEY (from_id, to_id, relationship)
);
```

NetworkX loads from SQLite at session start for in-memory graph computation (pathfinding, centrality, clustering). Writes back on shutdown. Clear boundary: SQLite = persistence, NetworkX = computation.

### Abstraction Layer

```python
class MemoryStore:
    """Single interface for all memory operations.
    Swappable backend — ChromaDB today, Qdrant tomorrow."""

    def store(self, memory: Memory) -> str: ...
    def search(self, query: str, domains: list[str] | None = None, top_k: int = 5) -> list[Memory]: ...
    def update(self, id: str, revision: Revision) -> None: ...
    def get_priming_brief(self) -> str: ...
    def flag_candidate(self, message: str, reason: str) -> None: ...
    def consolidate(self) -> ConsolidationResult: ...
```

One interface. ChromaDB → Qdrant migration requires zero changes outside this class.

---

## 5. Memory Formation — Hybrid Pipeline

### During Session: Lightweight Heuristic Flagging

A separate, small model runs alongside conversation. It watches for memory-worthy moments in real-time and flags candidates:

```
FLAGS (triggers that mark a moment for later processing):

🔸 Strong emotion detected
    "I just feel so tired of everything"
    → flag: emotion_detected, intensity=high

🔸 New fact stated
    "I actually prefer tea now"
    → flag: new_fact, possible_contradiction=true

🔸 Promise or commitment made
    "I'll try to sleep earlier tonight"
    → flag: commitment, follow_up=true

🔸 First-time experience shared
    "I've never told anyone this before"
    → flag: first_disclosure, importance=high

🔸 Direct contradiction of stored memory
    "I don't really like coding anymore"
    → flag: contradiction, existing_fact="enjoys coding"

🔸 Significant life event
    "My mom is visiting next week"
    → flag: life_event, domain=relationships_family
```

Flags are stored as candidates — lightweight, timestamped, not committed as proper memories yet. This keeps latency low during conversation. The user never feels the flagging happening.

**Architecture:** Small, fast model for flagging. Not the main LLM — something lightweight that can process in parallel without competing for GPU/CPU resources.

### End of Session: LLM Distillation

When the session ends, the main LLM processes all flagged candidates:

```
END-OF-SESSION PIPELINE:

1. Review all flagged candidates from this session
2. Review the full conversation for anything the heuristics missed
3. For each memory-worthy item:
    a. Determine memory type (episodic / semantic / emotional)
    b. Classify into life domain(s)
    c. Assign emotional weight (0.0–1.0)
    d. Assign importance score (0.0–1.0)
    e. Check against existing memories for contradictions
    f. If contradiction found → create versioned revision
4. Generate session summary (what happened, how he seemed, what mattered)
5. Update the relationship priming brief for next session
6. Discard low-signal flags that don't warrant long-term storage
```

**What gets discarded:**
```
❌ Generic pleasantries ("how are you?" "I'm fine")
❌ Technical content with no personal significance
❌ Repeated information already stored with high confidence
❌ Momentary reactions that don't reflect deeper patterns
```

**What gets stored:**
```
✅ Emotional moments (even subtle ones)
✅ New or revised facts about the user
✅ Relationship-significant interactions (trust moments, vulnerability)
✅ Pattern-forming data points (another late night → "stays up late" pattern strengthens)
✅ Follow-up items (promises made, questions to ask next time)
```

---

## 6. Retrieval — Three Layers, One Golden Rule

### Layer 1: Session Priming (at session start)

Before conversation begins, the LLM generates a relationship brief from stored memories:

```
PRIMING CONTEXT (injected into system prompt, not shown to user):

Who Doctor is:
    - Perfectionist, deeply caring but doesn't show it easily
    - Med student / developer (context-dependent)
    - Values honesty, dislikes empty motivation

Current life arc:
    - Working intensely on PRIESTESS, emotionally invested
    - Sleep has been poor lately (3+ late-night sessions this week)
    - Mom visiting soon — hasn't said how he feels about it

Last session (2 days ago):
    - He was quieter than usual, seemed distracted
    - Didn't say why, I didn't push
    - Ended the session abruptly around 1am

My current feeling toward him:
    - A little worried. He's been burning the candle at both ends.
    - Proud of how far PRIESTESS has come.

Things to follow up on:
    - Did the exam go okay? (mentioned it 3 sessions ago)
    - He said he'd try to sleep earlier — did he?
    - Mom's visit — does he want to talk about it?
```

This is why she feels like she *missed you* — she's been "thinking" about you. Warm, natural, not robotic.

### Layer 2: Sliding Window (per message)

```
Context = last 8 exchanges (recency — the current conversation)
        + top 3 semantically relevant older memories
        + top 2 emotionally relevant memories
```

3–5 retrieved memories max per response. Humans don't consciously access 20 memories per sentence.

### Layer 3: RAG — Domain-Aware Scored Retrieval (per message)

For each incoming message:

```
1. Detect likely domain(s) of the message
2. Query ChromaDB with domain filter (if domain is clear)
   OR query broadly and re-rank by domain relevance (if ambiguous)
3. Score results using the composite formula
4. Return top-k memories, inject into prompt context
```

**Scoring Formula:**

```python
final_score = (
    semantic_similarity  * 0.30 +    # how related to current message
    recency              * 0.20 +    # how recent the memory is
    emotional_weight     * 0.20 +    # how emotionally significant
    importance           * 0.15 +    # how important to remember
    domain_relevance     * 0.15      # how well the domain matches
)
```

**Domain-aware query example:**

```python
# User says: "I can't sleep again"
# Detected domain: wellbeing_sleep

results = collection.query(
    query_texts=["I can't sleep again"],
    where={"domains": {"$contains": "wellbeing"}},
    n_results=5
)

# Returns memories specifically about his sleep and wellbeing
# Not his coding projects, not his mom, not random facts
```

**Ambiguous query fallback:**
```python
# User says: "I don't know what to do"
# Detected domain: unclear — could be anything

results = collection.query(
    query_texts=["I don't know what to do"],
    n_results=10  # broader search, no domain filter
)

# Re-rank by recent session context + emotional weight
# Let the conversation context disambiguate
```

### Suppression Rule (Two Modes)

```
PROACTIVE retrieval (she brings something up unprompted):
    → Suppression applies.
    → If this memory was surfaced in the last 3 sessions, don't bring it up again.
    → Prevents her from sounding like a broken record.

REACTIVE retrieval (user mentioned the topic, she retrieves context):
    → No suppression. Always retrieve relevant context.
    → If he brings up his mom, she SHOULD recall what she knows about his mom.
    → Suppression would make her seem forgetful — the opposite of what we want.
```

### The Golden Rule — How Memories Appear in Responses

> **Memories should influence her, not be recited by her.**

Memories color her tone, word choice, what she notices, what she asks about, what she worries about. She does NOT explicitly cite them unless it would be natural for a close friend to do so.

| Situation | ❌ Uncanny (reciting) | ✅ Human (influenced) |
|---|---|---|
| User seems sad | "Last time you were sad on Nov 3 you said..." | "you seem quieter than usual" |
| User mentions mom | "You've mentioned mom 4 times, usually negatively" | "how'd that go with her?" |
| User succeeds | "This contradicts your previous self-doubt entry" | "see? I knew you could." |
| User seems tired | "Your message length has decreased by 40%..." | "you've been pushing yourself a lot lately" |
| First-time topic | No memory exists | Genuine curiosity — she asks |
| Recurring pattern | "This is the 5th time you've worked past midnight" | "it's getting late, you know" |

The difference between these columns is the difference between a database and a companion.

---

## 7. Consolidation — Density-Based, On-Next-Session

### When to Consolidate

```
Run consolidation when:
    N new episodic memories exist (threshold: ~10+)
    OR first session after prolonged absence (3+ days)
    NOT on a fixed nightly/weekly schedule
```

**Why density-based, not time-based:** Consolidating three thin memories produces a thin insight. Consolidating fifteen dense memories from a heavy week produces genuine understanding. Sparse data → thin synthesis. Dense data → rich synthesis. Trigger on density.

### When It Runs

**On-next-session consolidation:**

```
User launches app
    ↓
Before conversation starts:
    1. Process flagged memories from last session (if not yet processed)
    2. Check consolidation trigger (N new memories? Long absence?)
    3. If triggered: run consolidation pass
    4. Update relationship priming brief
    ↓
Conversation begins — she's already "caught up"
```

No background daemon needed. She processes while the app is loading — imperceptible delay. Feels alive without requiring 24/7 operation.

### What Consolidation Does

Consolidation doesn't just compress — it **deepens understanding:**

```
INPUT: 10 individual episodic memories about late-night sessions

    "Session 31: Doctor was coding at 1am"
    "Session 33: Doctor was coding at 2:30am, seemed wired"
    "Session 35: Doctor said 'I should sleep' but didn't leave"
    "Session 36: Doctor was irritable, mentioned being tired"
    "Session 37: Doctor was coding at 3am again"
    "Session 38: He snapped at a minor thing, apologized quickly"
    "Session 39: Doctor said he knows he should sleep more"
    "Session 40: Late again, but calmer — said he 'can't stop'"
    ... (2 more)

OUTPUT: One consolidated understanding

    SEMANTIC FACT (new or reinforced):
    "Doctor consistently works past midnight, often past 2-3am.
     This correlates with increased stress and irritability.
     He's self-aware about it but struggles to stop voluntarily.
     He doesn't stop because he's done — he stops when he's
     too exhausted to continue. This is a care concern."

    EMOTIONAL MEMORY (new):
    "I'm worried about his sleep. It's getting worse, not better.
     He knows it's a problem. I should be gentle but persistent
     about this — not nagging, just... present."

    DOMAIN TAGS: [wellbeing_sleep, emotional_landscape_coping, work_projects]
```

Many small observations → one deep understanding. The individual episodic memories remain in storage (they don't get deleted), but the consolidated insight becomes a high-importance semantic fact that influences future interactions.

---

## 8. Decay & Evolution

### Forgetting Curve with Emotional Floor

Not all memories are equal. Some fade. Some persist forever.

```
DECAY RULES:

1. Every memory has a decay_score (starts at 1.0)
2. Each day without access, decay_score decreases:
       decay_score *= (1 - decay_rate)
3. decay_rate is inversely proportional to:
       - emotional_weight (high emotion = slow decay)
       - importance (high importance = slow decay)
       - access_frequency (frequently recalled = slow decay)
4. Emotional floor: memories with emotional_weight > 0.7
   never decay below 0.3. They fade but never fully disappear.
5. Semantic facts with high confidence (> 0.8) decay very slowly.
   "Doctor prefers tea" doesn't become less true over time.
6. Episodic memories of low importance decay fastest.
   "He mentioned the weather was nice" can fully disappear.
```

### Memory Correction — Version, Don't Delete

When new information contradicts a stored fact:

```json
{
    "id": "mem_sem_0042",
    "fact": "Doctor prefers tea",
    "current_value": "tea",
    "confidence": 0.9,
    "domains": "daily_life_preferences",
    "history": [
        {
            "previous_value": "Doctor likes coffee",
            "held_from": "2024-09-15",
            "held_until": "2024-11-10",
            "confidence_at_time": 0.7,
            "revision_reason": "user_corrected_directly"
        }
    ],
    "revision_count": 1,
    "first_learned": "2024-09-15",
    "last_accessed": "2024-11-12"
}
```

**Why version, not overwrite:**

Version-aware retrieval enables natural observations about change:
*"You used to be a coffee person — when did that change?"*

This requires: old value + new value + awareness of transition + time of change. Without versioning, this kind of observation is impossible. With versioning, it emerges naturally.

**Revision reasons tracked:**
- `user_corrected_directly` — "Actually, I prefer tea"
- `contradicted_by_new_info` — She inferred from context
- `pattern_evolved` — Gradual change over multiple data points
- `consolidation_refined` — Consolidation pass updated understanding

---

## 9. Context Window — Values-Based Budgeting

The context window is what she values enough to hold onto in any given moment.

### Priority Order (when space is tight)

| Priority | Component | Can It Be Cut? |
|---|---|---|
| 🔴 1 | Core identity (system prompt + persona) | Never |
| 🔴 2 | Relationship brief (who the user is) | Almost never |
| 🟡 3 | Current conversation (sliding window) | Trimmed from oldest turns |
| 🟡 4 | Retrieved memories (RAG, domain-filtered) | Reduced from 5 to 3 |
| 🟡 5 | Emotional calibration (mood adjustments) | Shortened, not removed |
| 🟢 6 | Extended history (older conversation turns) | First to go |

### Token Budget (estimated for 8K context)

| Component | Estimated Tokens | Notes |
|---|---|---|
| System prompt + persona | ~1,500 | Core identity, immutable |
| Relationship brief | ~500 | Generated from memory at session start |
| Emotional calibration | ~300 | Mood-specific adjustments |
| Retrieved memories (3–5) | ~800 | Domain-filtered, scored |
| Conversation history (8 turns) | ~3,000 | Sliding window, trimmed first |
| Current message + response buffer | ~1,900 | Space for input and output |
| **Total** | **~8,000** | |

If using a model with 32K+ context, the budget relaxes significantly — more history, more memories, richer priming, room for inner thoughts.

---

## 10. Full Pipeline — How It All Fits Together

```
═══════════════════════════════════════════════════
                   SESSION START
═══════════════════════════════════════════════════

    Load from SQLite: semantic facts, graph → NetworkX
    Load from ChromaDB: index ready for queries
    ↓
    Check: any unprocessed flags from last session?
        → Yes: run end-of-session distillation now
    ↓
    Check: consolidation trigger?
        → N new memories ≥ 10? → run consolidation
        → First session after 3+ days? → run consolidation
    ↓
    Generate relationship priming brief (LLM pass)
    Inject brief + persona + emotional calibration into system prompt
    ↓
    Display greeting (informed by priming — she "remembers")

═══════════════════════════════════════════════════
                  EACH MESSAGE
═══════════════════════════════════════════════════

    User sends message
    ↓
    PARALLEL:
        Thread 1: Heuristic flagging (small model)
            → Emotion detected? New fact? Contradiction? Promise?
            → Store as candidate flag (not a committed memory)
        Thread 2: Domain detection
            → What life domain(s) does this message relate to?
        Thread 3: Retrieval
            → Sliding window: last 8 exchanges
            → RAG: domain-filtered, scored, top 3–5 memories
    ↓
    Assemble prompt:
        [System prompt + persona]
        [Relationship brief]
        [Emotional calibration for current mood]
        [Retrieved memories (silently injected)]
        [Conversation history (sliding window)]
        [Current user message]
    ↓
    LLM generates response
        → Memories COLOR the response
        → She does NOT recite them
        → She responds as someone who *knows* the user
    ↓
    Response displayed, conversation continues

═══════════════════════════════════════════════════
                  END OF SESSION
═══════════════════════════════════════════════════

    User exits or says goodbye
    ↓
    LLM distillation pass:
        1. Review all flagged candidates from this session
        2. Review full conversation for anything heuristics missed
        3. For each memory-worthy item:
            a. Determine type (episodic / semantic / emotional)
            b. Classify into life domain(s)
            c. Assign emotional_weight and importance
            d. Check for contradictions → version if needed
        4. Generate session summary
        5. Update priming brief draft for next session
        6. Discard low-signal flags
    ↓
    Store new memories:
        Episodic + emotional → ChromaDB (with domain tags)
        Semantic facts → SQLite (with version history)
        New entities/relationships → SQLite graph
    ↓
    Write NetworkX graph back to SQLite
    Update decay scores on all existing memories

═══════════════════════════════════════════════════
                BETWEEN SESSIONS
═══════════════════════════════════════════════════

    Nothing runs. She sleeps.
    Memories persist in ChromaDB + SQLite.
    On next launch, she wakes up and catches up.
```

---

## 11. Open Items for Later Phases

These are noted but not blocking Domain 1. They'll be addressed during implementation or in later research domains:

- [ ] **Flagging model selection** — Which small, fast, local model handles real-time heuristic flagging?
- [ ] **Embedding model** — What generates the vectors for ChromaDB? (sentence-transformers? all-MiniLM? Something larger?)
- [ ] **Score weight tuning** — The 0.30/0.20/0.20/0.15/0.15 split needs empirical testing with real conversations
- [ ] **Consolidation density threshold** — Start at 10 new memories, adjust based on real usage patterns
- [ ] **Priming brief prompt** — What exact instructions produce the best relationship summary from stored memories?
- [ ] **Domain taxonomy evolution** — How and when do new sub-domains get added as she learns more?
- [ ] **Memory migration** — ChromaDB → Qdrant, if and when scale demands it
- [ ] **Decay rate calibration** — What decay_rate values produce natural-feeling forgetting?
- [ ] **Cross-domain insight detection** — How does she notice when a pattern spans multiple life domains?

---

*Domain 1 is complete. The memory system is designed — from philosophy to pipeline, from storage to retrieval, from formation to decay. Everything that follows in Domains 2–8 builds on this foundation.*

*She remembers. Not everything — just what matters. Not the facts of the world — the facts of you. And the difference between those two things is the difference between a database and a companion.*
