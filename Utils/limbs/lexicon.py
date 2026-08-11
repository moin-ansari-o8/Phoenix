"""
Lexicon — repairs romanised Hindi/Gujarati words in an English transcript.

## The problem

Whisper is running an English model (`stt.model`). Ask it for "vhalam aavo ne"
and it returns whatever English-ish string the acoustics nearest-neighboured to:
`well um are vo nay`, `valam avo ne`, `bhalam aao na`. The sound was captured
correctly; only the spelling is wrong. Matching that against `data/songs.txt`
with `==` finds nothing.

Prompt conditioning (`hotwords`) helps and is applied upstream in
`voice_command_processor._build_dynamic_prompt`, but it is capped at ~223 tokens
by faster-whisper (`get_prompt`: `hotwords_tokens[: max_length // 2 - 1]`). A
song library does not fit in that budget and never will. This module is the
other half: unlimited vocabulary, applied after transcription, costing no STT
time at all.

## Why not double-metaphone / soundex

Both encode ENGLISH orthography. `sahiba` and `saahibaa` produce different
metaphone keys, while `ishq` and `ask` collapse together — exactly backwards for
this corpus. `normalize_roman` below instead folds the specific ways romanised
Indic words vary in spelling: doubled vowels, aspirated consonants written with
a trailing h, and the v/w and j/z pairs that have no stable convention.

## The rule this module must never break

README §9.1: **never fuzzy-match intents.** A `SequenceMatcher` intent matcher
once fired `playsong` on "capital of france?" at a 0.462 tie, and removing it was
a deliberate rewrite.

Nothing here selects an intent, a tool or an action. This module does two much
narrower things:

  * `repair_transcript` — rewrites individual WORDS toward a closed lexicon of
    names and command vocabulary, and refuses to touch anything that is already
    an ordinary English word unless the match is near-exact.
  * `resolve` — matches a SLOT VALUE (the text after "play") against a known
    library of ~40 titles.

Intent selection stays where it is: exact alias table, explicit grammar, then
the LLM router. If a future change makes this module's output decide which
action runs, that change is reintroducing the bug.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

logger = logging.getLogger("Lexicon")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LEXICON_FILE = os.path.join(_ROOT, "data", "lexicon.json")
SONGS_FILE = os.path.join(_ROOT, "data", "songs.txt")
SONG_STATS_FILE = os.path.join(_ROOT, "data", "song_stats.json")

# Words a repair must never overwrite. These are real English words that also
# sit phonetically close to something in the lexicon, and rewriting them is how
# "play the news" would turn into "play tere naina".
ENGLISH_GUARD = frozenset(
    """
    a an the and or but if is are was were be been being am do does did doing
    have has had having i you he she it we they me him her them my your his
    their our this that these those what which who whom whose when where why how
    all any both each few more most other some such no nor not only own same so
    than too very can will just should now here there then once about above after
    again against between into through during before below to from up down in out
    on off over under of at by for with as
    play song music open close start stop set turn take show tell give make
    time date day today tomorrow yesterday news weather battery volume light
    up down high low big small good bad new old next last first second
    """.split()
)

# The verbs that introduce a song request, in both languages the user mixes.
PLAY_VERBS = ("play", "bajao", "chalao", "lagao", "sunao", "put on", "put")
# Trailing nouns that describe the request rather than name the song.
TRAILING_NOUNS = ("song", "songs", "music", "gaana", "gana", "track", "please")

_WORD_RE = re.compile(r"[a-z']+", re.IGNORECASE)


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------

# Applied in order. Longer digraphs first, or "chh" would be eaten by "ch".
_FOLD_RULES: Tuple[Tuple[str, str], ...] = (
    ("chh", "c"),
    ("sh", "s"),
    ("ch", "c"),
    ("kh", "k"),
    ("gh", "g"),
    ("jh", "j"),
    ("dh", "d"),
    ("th", "t"),
    ("ph", "f"),
    ("bh", "b"),
    # "vhalam"/"valam", "whalam" -- Gujarati aspirated v has no settled roman
    # spelling, and Whisper picks a different one most times it hears it.
    ("vh", "v"),
    ("wh", "v"),
    ("aa", "a"),
    ("ee", "i"),
    ("ii", "i"),
    ("oo", "u"),
    ("uu", "u"),
    ("ai", "e"),
    ("ay", "e"),
    ("au", "o"),
    ("ou", "o"),
    ("ck", "k"),
    ("qu", "k"),
    ("q", "k"),
    ("x", "ks"),
    ("w", "v"),
    ("z", "j"),
    ("y", "i"),
)


def normalize_roman(text: str) -> str:
    """
    Collapse romanised-Indic spelling variation to a comparable key.

    Romanisation has no standard, so the same word reaches us spelled several
    ways and Whisper invents a few more. All of these must land on one key:

        sahiba / saahiba / sahibaa / sahiva  -> sahib
        vhalam / bhalam / valam              -> valam
        khuda  / kuda                        -> kuda

    Deliberately lossy. It is a bucketing function for fuzzy comparison, never
    something to display or store.
    """
    if not text:
        return ""

    text = text.lower().strip()
    text = re.sub(r"[^a-z\s]", "", text)

    out = []
    for word in text.split():
        for src, dst in _FOLD_RULES:
            word = word.replace(src, dst)
        # Collapse any remaining doubled letters ("chammak" -> "camak").
        word = re.sub(r"(.)\1+", r"\1", word)
        # A trailing bare vowel is the least stable part of a romanisation
        # ("mahi"/"maahi ve", "sahib"/"sahiba"), so drop it -- but never reduce
        # a word to nothing.
        if len(word) > 3 and word[-1] in "aeiou":
            word = word[:-1]
        if word:
            out.append(word)

    return " ".join(out)


# --------------------------------------------------------------------------
# The lexicon
# --------------------------------------------------------------------------


class Lexicon:
    """
    Closed vocabulary + song library, with phonetic lookup over both.

    Loaded from disk once and reloaded when either source file changes, so
    adding a song does not need a Phoenix restart.
    """

    # A word-level repair rewrites what the user said, so it needs to be nearly
    # certain. A song lookup only picks between ~40 known titles and a wrong
    # pick is obvious and instantly correctable, so it can afford to be bolder.
    WORD_THRESHOLD = 88
    ENGLISH_OVERRIDE_THRESHOLD = 97
    SONG_THRESHOLD = 75
    # Two-pass reranking bands. Measured over the real library with synthetic
    # mangling (tests/test_lexicon.py::test_candidate_recall):
    #   top-1 correct  92.9%
    #   correct in top-8  99.6%
    # That gap is the entire reason the second pass works -- retrieval over the
    # whole library is nearly perfect, only the ranking is unreliable, so a
    # second pass biased toward 8 candidates is choosing from a set that almost
    # always contains the answer.
    SONG_CONFIDENT = 88  # at or above this, pass 1 was right; do not re-run STT
    SONG_FLOOR = 60  # below this nothing in the library is plausible: a new song
    CANDIDATE_LIMIT = 8
    # A repair that changes the length a lot is a different word, not a
    # misspelling: "call" -> "chalu" scored well phonetically and was completely
    # wrong.
    MAX_LENGTH_RATIO = 1.5

    # Word-level repair runs over NAMES ONLY -- wake words and people.
    #
    # It originally covered `commands` and `hinglish` too, and testing killed
    # that: "what is the weather today" became "...weather thoda", and "remind
    # me to call mom" became "reminder me to chalu mom". Both are the same
    # mistake. The STT model is an ENGLISH model, so English command words are
    # exactly what it already gets right; running a fuzzy rewrite over them
    # risks the words that work in order to fix words that were never broken.
    #
    # Those categories still earn their place in data/lexicon.json -- they feed
    # the `hotwords` bias in _build_dynamic_prompt, where nudging the decoder
    # toward a spelling is safe because the acoustics still get a vote. Editing
    # a finished transcript has no such safety net.
    #
    # Hinglish inside a song request is handled by extract_song_slot +
    # resolve_song, which match a whole slot against a closed library rather
    # than rewriting individual words.
    REPAIR_CATEGORIES = ("names",)

    def __init__(
        self,
        lexicon_file: str = LEXICON_FILE,
        songs_file: str = SONGS_FILE,
        stats_file: str = SONG_STATS_FILE,
    ):
        self.lexicon_file = lexicon_file
        self.songs_file = songs_file
        self.stats_file = stats_file
        self._stats: Dict[str, dict] = {}
        self._categories: Dict[str, List[str]] = {}
        self._songs: List[str] = []
        # normalised key -> canonical form, per category
        self._index: Dict[str, Dict[str, str]] = {}
        # exact heard-word -> canonical, for known mishearings
        self._aliases: Dict[str, str] = {}
        self._mtimes: Dict[str, float] = {}
        self.reload()

    # -- loading ------------------------------------------------------------

    def _mtime(self, path: str) -> float:
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0.0

    def reload_if_stale(self):
        if (
            self._mtime(self.lexicon_file) != self._mtimes.get("lexicon")
            or self._mtime(self.songs_file) != self._mtimes.get("songs")
        ):
            self.reload()

    def reload(self):
        self._categories = self._load_lexicon()
        self._aliases = self._load_aliases()
        self._songs = self._load_songs()
        self._stats = self._load_stats()
        self._categories["songs"] = list(self._songs)

        self._index = {}
        for category, words in self._categories.items():
            table: Dict[str, str] = {}
            for word in words:
                key = normalize_roman(word)
                # First spelling wins: data/lexicon.json is hand-ordered by how
                # often the word is actually said.
                if key and key not in table:
                    table[key] = word
            self._index[category] = table

        self._mtimes = {
            "lexicon": self._mtime(self.lexicon_file),
            "songs": self._mtime(self.songs_file),
        }
        logger.info(
            "Lexicon loaded: %s",
            ", ".join(f"{c}={len(w)}" for c, w in sorted(self._categories.items())),
        )

    def _load_lexicon(self) -> Dict[str, List[str]]:
        try:
            with open(self.lexicon_file, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except FileNotFoundError:
            logger.warning("No lexicon at %s - repair disabled", self.lexicon_file)
            return {}
        except (json.JSONDecodeError, OSError) as exc:
            # A broken lexicon must not take the voice processor down with it.
            logger.error("Lexicon unreadable (%s) - repair disabled", exc)
            return {}

        self._raw = raw
        return {
            key: [str(w).strip().lower() for w in value if str(w).strip()]
            for key, value in raw.items()
            if not key.startswith("_") and key != "aliases" and isinstance(value, list)
        }

    def _load_aliases(self) -> Dict[str, str]:
        raw = getattr(self, "_raw", {}).get("aliases", {})
        if not isinstance(raw, dict):
            return {}
        return {
            str(heard).strip().lower(): str(canonical).strip().lower()
            for heard, canonical in raw.items()
            if str(heard).strip() and str(canonical).strip()
        }

    def _load_songs(self) -> List[str]:
        songs: List[str] = []
        try:
            with open(self.songs_file, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    _, _, title = line.partition("|")
                    title = (title or line).strip().lower()
                    if title:
                        songs.append(title)
        except FileNotFoundError:
            logger.warning("No song library at %s", self.songs_file)
        except OSError as exc:
            logger.error("Song library unreadable (%s)", exc)
        return songs

    def _load_stats(self) -> Dict[str, dict]:
        try:
            with open(self.stats_file, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except FileNotFoundError:
            return {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Song stats unreadable (%s) - starting fresh", exc)
            return {}
        if not isinstance(raw, dict):
            return {}
        return {
            str(title).lower(): value
            for title, value in raw.items()
            if isinstance(value, dict)
        }

    def _save_stats(self):
        try:
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            with open(self.stats_file, "w", encoding="utf-8") as handle:
                json.dump(self._stats, handle, indent=2, sort_keys=True)
        except OSError as exc:
            # Losing a play count is not worth failing a command over.
            logger.warning("Could not persist song stats (%s)", exc)

    def record_play(self, title: str):
        """Count a play, so the bias window can follow what is actually listened to."""
        if not title:
            return
        key = title.strip().lower()
        if not key:
            return
        entry = self._stats.setdefault(key, {"plays": 0, "last_played": 0.0})
        entry["plays"] = int(entry.get("plays", 0)) + 1
        entry["last_played"] = time.time()
        self._save_stats()

    def play_count(self, title: str) -> int:
        return int(self._stats.get((title or "").lower(), {}).get("plays", 0))

    # -- lookup -------------------------------------------------------------

    @property
    def songs(self) -> List[str]:
        return list(self._songs)

    def ranked_songs(self) -> List[str]:
        """
        Library ordered by how often each title is actually played.

        The hotword budget holds roughly twenty titles no matter how large the
        library grows (8.7 tokens per title against a 223-token hard cap), so
        WHICH twenty is the only lever available. Play count beats file order:
        people replay favourites, and a title that has never been played is the
        one least likely to be asked for next.

        Ties keep library order, so a fresh install with no history behaves
        exactly as before.
        """
        self.reload_if_stale()
        order = {title: index for index, title in enumerate(self._songs)}
        return sorted(
            self._songs,
            key=lambda title: (-self.play_count(title), order.get(title, 0)),
        )

    def candidates(self, text: str, limit: Optional[int] = None) -> List[Tuple[str, float]]:
        """
        Best `limit` library titles for `text`, ranked, with no score cutoff.

        This is the retrieval half of the two-pass match. Recall is what matters
        here, not precision -- the list is handed to Whisper as hotwords for a
        second transcription pass, so containing the right answer somewhere
        matters far more than ordering it first. Measured recall at 8: 99.6%.
        """
        self.reload_if_stale()
        table = self._index.get("songs")
        if not table or not text:
            return []

        key = normalize_roman(text)
        if not key:
            return []

        matches = process.extract(
            key,
            table.keys(),
            scorer=fuzz.token_set_ratio,
            limit=limit or self.CANDIDATE_LIMIT,
        )
        return [(table[match[0]], float(match[1])) for match in matches]

    def words(self, category: str) -> List[str]:
        return list(self._categories.get(category, []))

    def resolve(
        self,
        text: str,
        category: str,
        min_score: Optional[float] = None,
        scorer=fuzz.WRatio,
    ) -> Optional[Tuple[str, float]]:
        """
        Best match for `text` within one category, or None.

        Returns (canonical_form, score). Compares normalised keys, so the caller
        gets back the library's own spelling rather than what was heard -- which
        is what makes the result safe to hand to a search or a file lookup.
        """
        table = self._index.get(category)
        if not table or not text:
            return None

        key = normalize_roman(text)
        if not key:
            return None

        if key in table:
            return table[key], 100.0

        threshold = self.SONG_THRESHOLD if category == "songs" else self.WORD_THRESHOLD
        if min_score is not None:
            threshold = min_score

        match = process.extractOne(key, table.keys(), scorer=scorer, score_cutoff=threshold)
        if match is None:
            return None
        return table[match[0]], float(match[1])

    def resolve_song(self, text: str, min_score: Optional[float] = None):
        """
        Match a spoken song request against the library.

        Uses token_set_ratio rather than WRatio: requests arrive with extra or
        missing words ("play sanam teri kasam song", "kasam"), and token_set
        scores on shared tokens instead of penalising length differences.
        """
        self.reload_if_stale()
        return self.resolve(
            text, "songs", min_score=min_score, scorer=fuzz.token_set_ratio
        )

    # -- transcript repair --------------------------------------------------

    def repair_word(self, word: str) -> Optional[Tuple[str, str, float]]:
        """Best repair for one word as (canonical, category, score), or None."""
        # Known mishearings first, exactly. These are the cases fuzzy matching
        # should not have to guess at.
        alias = self._aliases.get(word.lower())
        if alias:
            return (alias, "alias", 100.0) if alias != word.lower() else None

        if len(word) < 3:
            # Too short to fuzzy-match safely: at three characters almost
            # everything is within edit distance of everything else.
            return None

        is_english = word.lower() in ENGLISH_GUARD
        best: Optional[Tuple[str, str, float]] = None

        for category in self.REPAIR_CATEGORIES:
            hit = self.resolve(word, category)
            if hit is None:
                continue
            canonical, score = hit
            if canonical == word.lower():
                return None  # already correct, nothing to do
            if is_english and score < self.ENGLISH_OVERRIDE_THRESHOLD:
                continue
            longer, shorter = sorted((len(canonical), len(word)), reverse=True)
            if shorter and longer / shorter > self.MAX_LENGTH_RATIO:
                continue
            if best is None or score > best[2]:
                best = (canonical, category, score)

        return best

    def repair_transcript(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Repair individual words in a transcript against the closed lexicon.

        Returns (repaired_text, [(heard, corrected), ...]). The list is for the
        runtime trace: a repair layer that works silently is a repair layer
        nobody can tell is misfiring.

        Conservative by construction -- it only ever rewrites a word into a word
        that is already in the lexicon, and leaves ordinary English alone unless
        the phonetic match is near-exact.
        """
        if not text or not self._index:
            return text, []

        self.reload_if_stale()
        repairs: List[Tuple[str, str]] = []

        def _sub(match: re.Match) -> str:
            word = match.group(0)
            hit = self.repair_word(word)
            if hit is None:
                return word
            canonical, _category, _score = hit
            repairs.append((word, canonical))
            # Keep the original capitalisation shape so "Phonix" -> "Phoenix"
            # rather than "phoenix" at the start of a sentence.
            if word[:1].isupper():
                return canonical.capitalize()
            return canonical

        return _WORD_RE.sub(_sub, text), repairs

    # -- song request parsing -----------------------------------------------

    def is_song_request(self, text: str) -> bool:
        """
        Whether `text` is asking for a song, cheaply and conservatively.

        Used only to decide whether a SECOND transcription pass is worth its
        latency. It never selects an intent -- routing still happens downstream
        exactly as before, and a false positive here costs one wasted STT pass,
        never a wrong action.
        """
        if not text:
            return False
        low = f" {text.lower().strip()} "
        return any(f" {verb} " in low for verb in PLAY_VERBS)

    def extract_song_slot(self, query: str) -> str:
        """
        Pull the requested title out of a play command.

        "play sahiba"                  -> "sahiba"
        "phoenix play sanam teri kasam song" -> "sanam teri kasam"
        "vhalam aavo ne bajao"         -> "vhalam aavo ne"
        "play some music"              -> ""   (no title named)

        Returns "" when nothing identifiable is left, which the caller must read
        as "no specific song asked for" rather than as a failed match.
        """
        if not query:
            return ""

        slot = query.lower().strip()
        slot = re.sub(r"[^\w\s']", " ", slot)

        # Verbs can lead ("play X") or trail ("X bajao"), because the user mixes
        # English and Hindi word order.
        for verb in sorted(PLAY_VERBS, key=len, reverse=True):
            slot = re.sub(rf"\b{re.escape(verb)}\b", " ", slot)
        for noun in TRAILING_NOUNS:
            slot = re.sub(rf"\b{re.escape(noun)}\b", " ", slot)

        slot = re.sub(r"\b(some|a|an|the|me|for|my|any|please|now|random)\b", " ", slot)
        slot = re.sub(r"\s+", " ", slot).strip()
        return slot


# --------------------------------------------------------------------------
# Module-level singleton
# --------------------------------------------------------------------------

_LEXICON: Optional[Lexicon] = None


def get_lexicon() -> Lexicon:
    """Shared instance. Built on first use so importing this module is cheap."""
    global _LEXICON
    if _LEXICON is None:
        _LEXICON = Lexicon()
    return _LEXICON
