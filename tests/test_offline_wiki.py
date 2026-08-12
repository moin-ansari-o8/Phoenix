"""
Offline encyclopedia tests.

The text-cleaning half runs everywhere - it is pure string work and it is where
the failures would actually be heard, since anything it misses gets read aloud
as markup. The archive half skips cleanly when no .zim is installed, so this
suite stays green on a fresh clone.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pytest W:\\workplace-1\\Phoenix\\tests\\test_offline_wiki.py -q
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.limbs.offline_wiki import (  # noqa: E402
    OfflineWiki,
    _first_sentences,
    _is_prose,
    _strip_html,
    get_wiki,
)


# ------------------------------------------------------------ text cleaning


def test_tags_are_removed():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_entities_are_decoded():
    assert _strip_html("Tom &amp; Jerry") == "Tom & Jerry"
    assert _strip_html("a&nbsp;b") == "a b"
    assert _strip_html("&quot;quoted&quot;") == '"quoted"'


def test_reference_markers_are_removed():
    """'[1]' read aloud becomes 'bracket one' - noise in a spoken answer."""
    got = _strip_html("Gandhi was born in 1869.[1] He studied law.[2][edit]")
    assert "[1]" not in got and "[2]" not in got and "[edit]" not in got
    assert "Gandhi was born in 1869." in got


def test_whitespace_is_collapsed():
    assert _strip_html("a\n\n   b\t\tc") == "a b c"


def test_empty_input():
    assert _strip_html("") == ""
    assert _strip_html(None) == ""


def test_first_sentences_never_cuts_mid_word():
    text = (
        "Ada Lovelace was an English mathematician. She is known for her work "
        "on the Analytical Engine. She was the first to recognise it had "
        "applications beyond calculation."
    )
    got = _first_sentences(text, 80)
    assert got.endswith(".")
    assert len(got) <= 80
    assert got.split()[-1] in text.split()


def test_first_sentences_returns_short_text_whole():
    assert _first_sentences("Short.", 500) == "Short."


def test_first_sentences_falls_back_to_a_word_boundary():
    """A passage with no sentence end must still not split a word."""
    text = "word " * 60
    got = _first_sentences(text, 50)
    assert len(got) <= 50
    assert not got.endswith("wor")


# ------------------------------------------------ found by the real archive
# Every case below was a live defect, not a hypothetical. The unit tests above
# all passed while Phoenix would have read a CSS stylesheet aloud.


def test_style_block_contents_are_removed():
    """
    The first thing the real archive produced for "Mahatma Gandhi" was
    ".mw-parser-output .infobox-subbox{padding:0;border:none...}" - Wikipedia
    ships per-article CSS inline, so stripping tags alone leaves the rules as
    text. This is the normal case, not an edge one.
    """
    html = (
        "<style>/* start */ .mw-parser-output .infobox{padding:0;border:none}"
        "@media screen{html.night{background:#1f1f23}}</style>"
        "<p>Gandhi was a leader of Indian nationalism.</p>"
    )
    got = _strip_html(html)
    assert "mw-parser-output" not in got
    assert "padding" not in got
    assert "{" not in got and "}" not in got
    assert "Gandhi was a leader" in got


def test_script_contents_are_removed():
    got = _strip_html("<script>var x = 1; alert('hi');</script><p>Real text.</p>")
    assert "alert" not in got and "var x" not in got
    assert "Real text." in got


def test_licence_footer_is_not_prose():
    """Short articles ran straight into the CC footer and would have spoken it."""
    assert not _is_prose(
        "This article is issued from Wikipedia. The text is available under "
        "Creative Commons Attribution-Share Alike 4.0 unless otherwise noted."
    )


@pytest.mark.parametrize(
    "hatnote",
    [
        "This article is about Earth's moon. For moons in general, see Natural satellite.",
        "For other uses, see Python. This page is a disambiguation listing.",
        "Not to be confused with something else entirely and other similar things.",
    ],
)
def test_hatnotes_are_not_prose(hatnote):
    assert not _is_prose(hatnote)


def test_infobox_fragments_are_not_prose():
    """
    An infobox flattens to capitalised fragments with no verbs. "India" used to
    begin "Flag State Emblem Motto: ... Anthem:" and the Moon began "Apparent
    magnitude -2.5 to -12.9".
    """
    assert not _is_prose(
        "Flag State Emblem Motto: Truth Alone Triumphs Anthem: Thou Art the "
        "Ruler Capital New Delhi Currency Rupee Area 3287263 km2"
    )
    assert not _is_prose(
        "Apparent magnitude -2.5 to -12.9 Angular diameter 29.3 to 34.1 "
        "arcminutes Surface pressure 2.25 torr Orbital period 27.3 days"
    )


def test_real_sentences_are_prose():
    assert _is_prose(
        "The Moon, also known as Luna, is Earth's only natural satellite and "
        "is usually visible in the night sky at some point during the month."
    )
    assert _is_prose(
        "Ada Lovelace was an English mathematician and writer who is known as "
        "the first computer programmer in the history of the field."
    )


def test_very_short_text_is_not_prose():
    """A stub sounds like an answer while carrying no information."""
    assert not _is_prose("A city.")
    assert not _is_prose("")


# --------------------------------------------------------------- no archive


def test_missing_archive_is_not_an_error(tmp_path):
    """No .zim means no offline answers - never an exception."""
    wiki = OfflineWiki(zim_dir=str(tmp_path))
    assert wiki.available is False
    assert wiki.summary("anything") == ""


def test_unreadable_archive_is_not_an_error(tmp_path):
    bogus = tmp_path / "broken.zim"
    bogus.write_bytes(b"this is not a ZIM file")
    wiki = OfflineWiki(zim_dir=str(tmp_path))
    assert wiki.available is False
    assert wiki.summary("anything") == ""


def test_get_wiki_is_a_singleton():
    assert get_wiki() is get_wiki()


def test_tool_registry_falls_through_without_an_archive(tmp_path, monkeypatch):
    """
    With no archive and the web off, the refusal must still be a refusal - not
    an answer invented from training data.
    """
    from core.config import AppConfig
    from Utils.limbs import tool_registry as tr

    monkeypatch.setattr(tr, "_offline_evidence", lambda topic: None)
    original = AppConfig.web.get("enabled", True)
    try:
        AppConfig.web["enabled"] = False
        result = tr.dispatch("search_web", {"query": "population of france"})
        assert result["kind"] == "direct"
        assert result["spoken"] in (tr.OFFLINE_NOTICE, tr.NO_NETWORK_NOTICE)
    finally:
        AppConfig.web["enabled"] = original


def test_offline_evidence_is_used_before_refusing(monkeypatch):
    """When the archive HAS the answer, being offline is no longer a dead end."""
    from core.config import AppConfig
    from Utils.limbs import tool_registry as tr

    monkeypatch.setattr(
        tr, "_offline_evidence", lambda topic: "Ada Lovelace was a mathematician."
    )
    original = AppConfig.web.get("enabled", True)
    try:
        AppConfig.web["enabled"] = False
        result = tr.dispatch("search_web", {"query": "ada lovelace"})
        assert result["kind"] == "evidence"
        assert "Lovelace" in result["evidence"]
    finally:
        AppConfig.web["enabled"] = original


# ------------------------------------------------------------- with archive


def _installed():
    wiki = get_wiki()
    return wiki.available


needs_archive = pytest.mark.skipif(
    not _installed(), reason="no .zim archive installed in data/zim/"
)


@needs_archive
def test_real_lookup_by_title():
    got = get_wiki().summary("Mahatma Gandhi")
    assert got, "expected an article for Mahatma Gandhi"
    assert "<" not in got and "[" not in got, "markup leaked into spoken text"
    assert len(got) > 60


@needs_archive
@pytest.mark.parametrize(
    "topic,must_contain",
    [
        ("India", "India"),
        ("Moon", "Moon"),
        ("Ada Lovelace", "Lovelace"),
        ("Albert Einstein", "Einstein"),
        ("Python (programming language)", "Python"),
    ],
)
def test_real_lookups_are_speakable(topic, must_contain):
    """
    Each of these was broken against the real archive in a different way:
    India and Moon opened with infobox fragments, Ada Lovelace lost her own
    name to the title de-duplication and ran into the licence footer, and
    Python opened with a hatnote.
    """
    got = get_wiki().summary(topic)
    assert got, f"no article for {topic}"
    assert must_contain.lower() in got.lower(), "the subject is missing"
    for artefact in ("<", "{", "}", "mw-parser-output", "Creative Commons"):
        assert artefact not in got, f"{artefact!r} leaked into spoken text"
    assert _is_prose(got)


@needs_archive
def test_nonsense_topic_returns_nothing():
    assert get_wiki().summary("qwertyuiop asdfghjkl zxcvbnm") == ""
