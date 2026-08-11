"""
Regression tests for Utils/limbs/lexicon.py.

Run directly (no pytest in this venv):

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\test_lexicon.py

The negative sets matter more than the positive ones here. A repair layer that
fixes Hinglish while quietly corrupting ordinary English is a net loss, and that
is not hypothetical: an earlier version of this module turned "what is the
weather today" into "...weather thoda" and "remind me to call mom" into
"reminder me to chalu mom". Those cases are in `test_repair_leaves_english_alone`
and must stay there.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.limbs.lexicon import Lexicon, normalize_roman

_RESULTS = []


def check(name, condition, detail=""):
    _RESULTS.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f"  -- {detail}" if detail and not condition else ""))


def section(title):
    print(f"\n{title}\n{'-' * len(title)}")


LEX = Lexicon()


# --------------------------------------------------------------------------
# 1. The normaliser
# --------------------------------------------------------------------------


def test_normalizer():
    section("Romanisation normaliser")

    # Spellings of the same word must collapse to the same key. That is the
    # whole contract; the key's actual value is an implementation detail.
    same = [
        ("sahiba", "saahibaa"),
        ("sahiba", "sahibaa"),
        ("chammak challo", "chamak chalo"),
        ("kaho na pyar hai", "kaho na pyaar hai"),
        ("khuda", "kuda"),
        ("vhalam", "valam"),
        ("tere naina", "tera naina"),
        ("bajao", "bajaao"),
        ("gaana", "gana"),
        ("zyada", "jyada"),
        ("mohabbat", "mohabat"),
    ]
    for left, right in same:
        check(
            f"'{left}' and '{right}' normalise alike",
            normalize_roman(left) == normalize_roman(right),
            f"{normalize_roman(left)!r} != {normalize_roman(right)!r}",
        )

    # Genuinely different words must NOT collapse, or the resolver starts
    # matching everything to everything.
    different = [
        ("sahiba", "dillagi"),
        ("perfect", "feelings"),
        ("monster", "bulleya"),
        ("despacito", "janam janam"),
        ("brightness", "volume"),
    ]
    for left, right in different:
        check(
            f"'{left}' and '{right}' stay distinct",
            normalize_roman(left) != normalize_roman(right),
            f"both -> {normalize_roman(left)!r}",
        )

    check("empty input is handled", normalize_roman("") == "")
    check("punctuation is dropped", normalize_roman("sahiba!?") == normalize_roman("sahiba"))
    check("case is irrelevant", normalize_roman("SaHiBa") == normalize_roman("sahiba"))
    check(
        "a short word is not reduced to nothing",
        normalize_roman("ishq") != "",
        normalize_roman("ishq"),
    )


# --------------------------------------------------------------------------
# 2. Song resolution
# --------------------------------------------------------------------------


def test_song_resolution():
    section("Song resolution")

    check("the library loaded", len(LEX.songs) >= 30, f"{len(LEX.songs)} songs")

    hits = [
        ("sahiba", "sahiba"),
        ("saahibaa", "sahiba"),
        ("sahiwa", "sahiba"),
        ("vhalam aavo ne", "vhalam aavo ne"),
        ("valam avo ne", "vhalam aavo ne"),
        ("chamak chalo", "chammak challo"),
        ("sanam teri kasam", "sanam teri kasam"),
        ("kaho na pyaar hai", "kaho na pyar hai"),
        ("kuda aur mohabat", "khuda aur mohabbat"),
        ("tera naina", "tere naina"),
        ("despacito", "despacito"),
        ("russian bandana", "russian bandana"),
    ]
    for heard, expected in hits:
        result = LEX.resolve_song(heard)
        check(
            f"'{heard}' resolves to '{expected}'",
            result is not None and result[0] == expected,
            f"got {result}",
        )

    # Nothing in the library is close to these. A miss is the correct answer --
    # a wrong song here is worse than admitting no match, because the miss path
    # is what lets a new song get added.
    misses = [
        "taylor swift blank space",
        "bohemian rhapsody",
        "the news",
        "what is the time",
        "",
    ]
    for heard in misses:
        check(f"'{heard}' correctly finds no match", LEX.resolve_song(heard) is None,
              f"got {LEX.resolve_song(heard)}")


# --------------------------------------------------------------------------
# 3. Slot extraction
# --------------------------------------------------------------------------


def test_slot_extraction():
    section("Song slot extraction")

    cases = [
        ("play sahiba", "sahiba"),
        ("play sahiba song", "sahiba"),
        ("play the sahiba song", "sahiba"),
        ("play sanam teri kasam", "sanam teri kasam"),
        ("vhalam aavo ne bajao", "vhalam aavo ne"),
        ("chalao despacito", "despacito"),
        ("play me some music", ""),
        ("play a song", ""),
        ("play", ""),
        ("play a random song", ""),
    ]
    for query, expected in cases:
        got = LEX.extract_song_slot(query)
        check(f"'{query}' -> '{expected}'", got == expected, f"got '{got}'")

    # End to end: the spoken phrasing must reach the library title.
    end_to_end = [
        ("play saahibaa song", "sahiba"),
        ("valam avo ne bajao", "vhalam aavo ne"),
        ("play kuda aur mohabat", "khuda aur mohabbat"),
    ]
    for query, expected in end_to_end:
        slot = LEX.extract_song_slot(query)
        result = LEX.resolve_song(slot)
        check(
            f"'{query}' reaches '{expected}'",
            result is not None and result[0] == expected,
            f"slot='{slot}' got={result}",
        )


# --------------------------------------------------------------------------
# 3b. Candidate retrieval -- the basis of the two-pass rerank
# --------------------------------------------------------------------------


def _mangle(text, severity, rng):
    """Approximate what an English STT model does to a romanised Hindi title."""
    out = []
    for ch in text:
        if ch == " ":
            out.append(ch)
            continue
        roll = rng.random()
        if roll < severity * 0.25:
            continue  # dropped sound
        if roll < severity * 0.5:
            out.append(rng.choice("aeiou") if ch in "aeiou" else rng.choice("bvdtkgjzsn"))
        elif roll < severity * 0.6:
            out.append(ch)
            out.append(ch)  # doubled letter
        else:
            out.append(ch)
    return "".join(out)


def test_candidate_recall():
    section("Candidate retrieval (two-pass rerank depends on this)")

    import random

    rng = random.Random(7)

    # The whole two-pass design rests on one asymmetry: ranking the right title
    # FIRST is unreliable, but having it SOMEWHERE in the top 8 is nearly
    # certain. The second pass only has to choose among 8, so recall is what
    # must hold. If this test starts failing, the rerank stops being worth its
    # latency and the thresholds need revisiting.
    for severity, label, min_recall in ((0.25, "light", 0.95), (0.45, "heavy", 0.95)):
        first = hits = total = 0
        for title in LEX.songs:
            for _ in range(6):
                query = _mangle(title, severity, rng)
                if not query.strip():
                    continue
                total += 1
                results = LEX.candidates(query, limit=8)
                if results and results[0][0] == title:
                    first += 1
                if any(candidate == title for candidate, _ in results):
                    hits += 1

        recall = hits / max(total, 1)
        precision = first / max(total, 1)
        check(
            f"{label} mangling: recall@8 >= {min_recall:.0%}",
            recall >= min_recall,
            f"recall {recall:.1%}, top-1 {precision:.1%}",
        )
        check(
            f"{label} mangling: recall@8 beats top-1",
            recall >= precision,
            f"recall {recall:.1%} vs top-1 {precision:.1%}",
        )
        print(f"         (top-1 {precision:.1%}, recall@8 {recall:.1%}, n={total})")

    check("candidates on empty input is empty", LEX.candidates("") == [])
    check(
        "candidates respects the limit",
        len(LEX.candidates("sahiba", limit=3)) <= 3,
    )
    check(
        "candidates returns titles, not normalised keys",
        all(c in LEX.songs for c, _ in LEX.candidates("sahiba")),
    )


def test_song_request_detection():
    section("Song-request detection (gates the second pass)")

    yes = ["play sahiba", "phoenix play the news song", "vhalam aavo ne bajao", "chalao despacito"]
    for text in yes:
        check(f"'{text}' is a song request", LEX.is_song_request(text))

    # A false positive here costs one wasted STT pass. A false negative costs
    # the rerank entirely, so this errs toward yes -- but it must not fire on
    # ordinary commands.
    no = [
        "what is the time",
        "open brave",
        "increase the brightness",
        "how much battery do i have",
        "",
    ]
    for text in no:
        check(f"'{text}' is not a song request", not LEX.is_song_request(text))


def test_ranked_songs():
    section("Play-count ranking (chooses which ~20 titles get biased)")

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        stats = os.path.join(tmp, "song_stats.json")
        lex = Lexicon(stats_file=stats)

        check("with no history, order matches the library", lex.ranked_songs() == lex.songs)

        target = lex.songs[-1]  # last in file order, so ranking has to move it
        for _ in range(3):
            lex.record_play(target)

        ranked = lex.ranked_songs()
        check(f"a played title rises to the front", ranked[0] == target, ranked[0])
        check("the play count persisted", lex.play_count(target) == 3, str(lex.play_count(target)))
        check("every title is still present", sorted(ranked) == sorted(lex.songs))

        reloaded = Lexicon(stats_file=stats)
        check("counts survive a reload", reloaded.play_count(target) == 3)

        # A corrupt stats file must not break song playback.
        with open(stats, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        broken = Lexicon(stats_file=stats)
        check("a corrupt stats file degrades quietly", broken.ranked_songs() == broken.songs)


# --------------------------------------------------------------------------
# 4. Transcript repair -- the negative set is the important one
# --------------------------------------------------------------------------


def test_repair_fixes_wake_words():
    section("Transcript repair: known mishearings")

    cases = [
        ("phonix open brave", "phoenix open brave"),
        ("hey fenix", "hey phoenix"),
        ("pheonix what is the time", "phoenix what is the time"),
        ("ok phoneix", "ok phoenix"),
        ("feenix play sahiba", "phoenix play sahiba"),
    ]
    for heard, expected in cases:
        repaired, _ = LEX.repair_transcript(heard)
        check(f"'{heard}' -> '{expected}'", repaired == expected, f"got '{repaired}'")

    check(
        "capitalisation shape is preserved",
        LEX.repair_transcript("Phonix open brave")[0] == "Phoenix open brave",
        LEX.repair_transcript("Phonix open brave")[0],
    )

    repaired, repairs = LEX.repair_transcript("phonix open brave")
    check("repairs are reported for the trace", repairs == [("phonix", "phoenix")], str(repairs))


def test_repair_leaves_english_alone():
    section("Transcript repair: ordinary English is untouched")

    # Every one of these must come back byte-identical. The first two are
    # actual regressions -- see the module docstring.
    untouched = [
        "what is the weather today",
        "remind me to call mom at six",
        "what is the capital of france",
        "open brave and play the news",
        "set volume to fifty percent",
        "increase the brightness by thirty percent",
        "tell me a joke about cats",
        "how much battery do i have",
        "search youtube for lofi beats",
        "take a screenshot now",
        "what did you say again",
        "who is my friend rohit",
        "play some music",
        "close the window",
        "i prefer dark mode",
        "what is python",
        "turn it down a bit",
        "set a timer for ten minutes",
    ]
    for text in untouched:
        repaired, repairs = LEX.repair_transcript(text)
        check(f"'{text}' is unchanged", repaired == text, f"became '{repaired}' via {repairs}")

    check("empty input survives", LEX.repair_transcript("")[0] == "")


def test_resilience():
    section("Resilience")

    missing = Lexicon(lexicon_file="does-not-exist.json", songs_file="also-missing.txt")
    check("a missing lexicon does not raise", missing.repair_transcript("hello")[0] == "hello")
    check("a missing song library resolves to None", missing.resolve_song("sahiba") is None)
    check("a missing library reports zero songs", missing.songs == [])


if __name__ == "__main__":
    print("Phoenix lexicon regression tests")
    test_normalizer()
    test_song_resolution()
    test_slot_extraction()
    test_candidate_recall()
    test_song_request_detection()
    test_ranked_songs()
    test_repair_fixes_wake_words()
    test_repair_leaves_english_alone()
    test_resilience()

    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    failed = [(name, detail) for name, ok, detail in _RESULTS if not ok]

    print(f"\n{'=' * 60}")
    print(f"{passed}/{len(_RESULTS)} checks passed")
    if failed:
        print("\nFailures:")
        for name, detail in failed:
            print(f"  - {name}" + (f"  ({detail})" if detail else ""))
    sys.exit(1 if failed else 0)
