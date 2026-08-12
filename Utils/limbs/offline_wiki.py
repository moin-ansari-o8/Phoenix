"""
Offline encyclopedia, from a Kiwix ZIM archive.

The honest answer to "what is the population of France" with no network is "I
don't know". But most of what `search_web` was actually used for is not
volatile - "who was Ada Lovelace", "what is a transformer network", "how far is
the moon" are settled facts that happen to live on Wikipedia. Those do not need
the internet; they need a local copy.

So: drop a `.zim` into `data/zim/` and Phoenix answers encyclopedic questions
with no network at all. Nothing else changes - `tool_registry` consults this
first and only then decides whether to refuse or go online.

Getting an archive (any one of these works, largest last):

    https://download.kiwix.org/zim/wikipedia/
      wikipedia_en_simple_all_mini_<date>.zim    ~450 MB  article intros
      wikipedia_en_simple_all_nopic_<date>.zim   ~940 MB  full text
      wikipedia_en_all_nopic_<date>.zim          ~50 GB   full English

`_mini` is the natural fit: it holds lead paragraphs, and a voice assistant
speaks one or two sentences. Downloading the full text to read out 30 words of
it is mostly wasted disk.

Design notes:

- **The archive is opened once and kept.** Opening is cheap but not free, and
  the file is memory-mapped, so holding it costs little.
- **Title lookup first, full-text search second.** An exact title match is both
  faster and far more accurate than a relevance ranking; the search index is
  the fallback for phrasings like "who invented the telephone".
- **HTML is stripped here**, not by the caller. What comes back is meant to be
  read out loud, so it must be plain prose with no markup, no reference
  markers, and no "[edit]".
- **Missing or corrupt archive is not an error.** It simply means no offline
  encyclopedia, and the caller falls back to whatever it would otherwise do.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from typing import Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ZIM_DIR = os.path.join(_BASE, "data", "zim")

logger = logging.getLogger("OfflineWiki")

# Markup and artefacts that must never reach the speech engine.
#
# Elements whose CONTENT is not prose. Stripping tags alone is not enough:
# a <style> block's body survives as text, and the first thing Phoenix said
# about Mahatma Gandhi was ".mw-parser-output .infobox-subbox{padding:0;
# border:none...}" read aloud. Wikipedia ships per-article CSS inline, so this
# is the normal case, not an edge one.
_DROP_ELEMENT = re.compile(
    r"<(style|script|sup|table)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)
# Infoboxes and navigation boxes are tables of fragments - "Born 2 October 1869
# Porbandar" - which read as a list of disconnected nouns.
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_CSS_RULE = re.compile(r"[.#@][\w-]+[^{}]*\{[^{}]*\}")
_TAG = re.compile(r"<[^>]+>")
_REFERENCE = re.compile(r"\[\d+\]|\[edit\]|\[citation needed\]", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")
# Parenthesised pronunciation/etymology clutter: "(/ˈɡɑːndi/; 2 October 1869 ...)"
_PRONUNCIATION = re.compile(r"\((?:[^()]*[/ˈːɡɑ][^()]*)\)")


def _strip_html(html: str) -> str:
    text = html or ""
    # Content-bearing junk first, while the element boundaries still exist.
    text = _DROP_ELEMENT.sub(" ", text)
    text = _CSS_COMMENT.sub(" ", text)
    text = _CSS_RULE.sub(" ", text)
    text = _TAG.sub(" ", text)
    for entity, char in (
        ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&quot;", '"'), ("&#39;", "'"), ("&apos;", "'"),
    ):
        text = text.replace(entity, char)
    text = _REFERENCE.sub("", text)
    text = _PRONUNCIATION.sub("", text)
    return _WHITESPACE.sub(" ", text).strip()


_PARAGRAPH = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)

# Text that is on the page but is not about the subject.
_BOILERPLATE = re.compile(
    r"This article is issued from Wikipedia.*|"
    r"The text is available under Creative Commons.*|"
    r"Additional terms may apply.*",
    re.IGNORECASE | re.DOTALL,
)
# Hatnotes: "This article is about Earth's moon. For moons in general, see ..."
_HATNOTE = re.compile(
    r"^\s*(this article is about|for other uses|for the .{0,40}, see|not to be "
    r"confused with|see also)\b",
    re.IGNORECASE,
)


def _is_prose(text: str) -> bool:
    """
    Is this a paragraph a person would want read aloud?

    Rejects hatnotes, licence boilerplate, and infobox residue. The last is the
    interesting one: an infobox flattens to many short capitalised fragments
    with few verbs, so a paragraph with almost no lowercase connective words is
    a table, not a sentence.
    """
    if not text or len(text) < 60:
        return False
    if _HATNOTE.match(text):
        return False
    if _BOILERPLATE.match(text.strip()):
        return False
    # A real sentence contains function words. "Flag State Emblem Motto Anthem"
    # does not.
    words = text.split()
    if len(words) < 8:
        return False
    connectives = sum(
        1
        for w in words
        if w.lower().strip(".,;:()\"'")
        in {"the", "a", "an", "of", "is", "was", "are", "were", "in", "on",
            "and", "to", "for", "with", "that", "which", "as", "by", "it",
            "he", "she", "they", "has", "have", "had", "from", "at", "its"}
    )
    return connectives / len(words) >= 0.12


def _first_sentences(text: str, max_chars: int) -> str:
    """Whole sentences up to max_chars - never a fragment cut mid-word."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    for terminator in (". ", "! ", "? "):
        index = cut.rfind(terminator)
        if index > max_chars // 3:
            return cut[: index + 1].strip()
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut).strip()


class OfflineWiki:
    """Read-only view over one ZIM archive."""

    def __init__(self, zim_dir: str = ZIM_DIR):
        self.zim_dir = zim_dir
        self.path: Optional[str] = None
        self._archive = None
        self._lock = threading.Lock()
        self._unavailable = False

    # ------------------------------------------------------------- discovery

    def _find_archive(self) -> Optional[str]:
        if not os.path.isdir(self.zim_dir):
            return None
        candidates = [
            os.path.join(self.zim_dir, name)
            for name in sorted(os.listdir(self.zim_dir))
            if name.lower().endswith(".zim")
        ]
        if not candidates:
            return None
        # Largest wins: if someone has both _mini and _nopic, the fuller one is
        # the better answer and the extra size is already paid for.
        return max(candidates, key=os.path.getsize)

    @property
    def archive(self):
        """The open Archive, or None. Opened once, lazily."""
        if self._archive is not None or self._unavailable:
            return self._archive

        with self._lock:
            if self._archive is not None or self._unavailable:
                return self._archive
            path = self._find_archive()
            if not path:
                self._unavailable = True
                logger.info("[offline_wiki] no .zim archive in %s", self.zim_dir)
                return None
            try:
                from libzim.reader import Archive

                self._archive = Archive(path)
                self.path = path
                logger.info(
                    "[offline_wiki] %s (%d articles, %.0f MB)",
                    os.path.basename(path),
                    self._archive.article_count,
                    os.path.getsize(path) / 1e6,
                )
            except Exception as exc:
                self._unavailable = True
                logger.warning("[offline_wiki] could not open %s: %s", path, exc)
            return self._archive

    @property
    def available(self) -> bool:
        return self.archive is not None

    # ---------------------------------------------------------------- lookup

    def _entry_text(self, entry, max_chars: int) -> str:
        try:
            item = entry.get_item()
            raw = bytes(item.content).decode("utf-8", errors="replace")
        except Exception:
            return ""

        # Take the first real PARAGRAPH, not the first N characters of the
        # cleaned page. Flattening the whole document and slicing produced, in
        # order: the title twice (it is also an <h1>), then the infobox read as
        # a list of fragments - "Flag State Emblem Motto: ... Anthem:" for
        # India, "Apparent magnitude -2.5 to -12.9" for the Moon - and for
        # short articles the Creative Commons footer. A <p> is the unit that
        # actually corresponds to prose.
        for block in _PARAGRAPH.findall(raw):
            candidate = _strip_html(block)
            if _is_prose(candidate):
                return _first_sentences(candidate, max_chars)

        # No usable paragraph: fall back to the flattened page, minus the
        # boilerplate, so a differently-built ZIM still yields something.
        text = _BOILERPLATE.sub(" ", _strip_html(raw))
        text = _WHITESPACE.sub(" ", text).strip()
        return _first_sentences(text, max_chars) if _is_prose(text) else ""

    def _by_title(self, topic: str):
        archive = self.archive
        for candidate in (topic, topic.title(), topic.capitalize()):
            try:
                if archive.has_entry_by_title(candidate):
                    return archive.get_entry_by_title(candidate)
            except Exception:
                continue
        return None

    def _by_search(self, topic: str):
        archive = self.archive
        if not archive.has_fulltext_index:
            return None
        try:
            from libzim.search import Query, Searcher

            search = Searcher(archive).search(Query().set_query(topic))
            for path in search.getResults(0, 1):
                return archive.get_entry_by_path(path)
        except Exception as exc:
            logger.debug("[offline_wiki] search failed for %r: %s", topic, exc)
        return None

    def summary(self, topic: str, max_chars: int = 700) -> str:
        """
        Plain-prose summary of `topic`, or "" if there is no usable answer.

        Returning "" rather than raising is deliberate: no archive, no article
        and a corrupt archive are the same thing to the caller - there is no
        offline answer, so fall through to whatever is next.
        """
        topic = (topic or "").strip()
        if not topic or not self.available:
            return ""

        entry = self._by_title(topic) or self._by_search(topic)
        if entry is None:
            return ""

        try:
            # Redirects: "Gandhi" -> "Mahatma Gandhi".
            if entry.is_redirect:
                entry = entry.get_redirect_entry()
        except Exception:
            pass

        text = self._entry_text(entry, max_chars)
        # A stub of a few words is worse than admitting we do not know: it
        # sounds like an answer while carrying no information.
        return text if len(text) >= 60 else ""


_instance = None
_instance_lock = threading.Lock()


def get_wiki() -> OfflineWiki:
    """Process-wide instance; the archive is memory-mapped and worth reusing."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = OfflineWiki()
    return _instance
