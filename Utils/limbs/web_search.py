"""Web search and page extraction for answering questions.

Every function is failure-tolerant: on any network/parse error they return an
empty result rather than raising, so Phoenix degrades to "I couldn't find that"
instead of crashing.
"""

import logging
import warnings

# The `wikipedia` package builds BeautifulSoup without naming a parser, which
# emits a multi-line GuessedAtParserWarning into the TUI on every lookup.
warnings.filterwarnings("ignore", category=UserWarning, module="wikipedia")
try:
    from bs4 import GuessedAtParserWarning

    warnings.filterwarnings("ignore", category=GuessedAtParserWarning)
except Exception:
    pass

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def search(query: str, max_results: int = 5) -> list:
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
    if not url:
        return ""
    try:
        import requests
        import trafilatura

        r = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            return ""
        return (
            trafilatura.extract(r.text, include_comments=False, include_tables=False)
            or ""
        )
    except Exception as e:
        logging.warning(f"[web_search] fetch failed for {url}: {e}")
        return ""


def wiki_summary(topic: str, sentences: int = 4) -> str:
    """Wikipedia summary for an entity. Returns '' if not found/ambiguous."""
    if not topic:
        return ""
    try:
        import wikipedia

        return wikipedia.summary(topic, sentences=sentences, auto_suggest=True)
    except Exception as e:
        # DisambiguationError stringifies to the full candidate list (dozens of
        # lines), which floods the TUI. Log only the first line.
        first = str(e).splitlines()[0] if str(e) else e.__class__.__name__
        logging.warning(f"[web_search] wiki failed for {topic!r}: {first[:120]}")
        return ""


def gather_context(
    query: str, max_chars: int = 3000, max_results: int = 5, timeout: int = 8
) -> str:
    """Build a plain-text evidence block for the answer model. Never raises."""
    parts = []

    wiki = wiki_summary(query)
    if wiki:
        parts.append(f"[Wikipedia] {wiki}")
        # A solid encyclopedia hit is enough. Skipping the search saves a
        # network round trip (~2-3s) and keeps the prompt short, which on this
        # hardware costs roughly 1.85ms per character of answer latency.
        if len(wiki) >= 400:
            return wiki[:max_chars]

    for r in search(query, max_results=max_results):
        snippet = (r.get("body") or "").strip()
        if snippet:
            parts.append(f"[{r.get('title', 'result')}] {snippet}")
        if sum(len(p) for p in parts) > max_chars:
            break

    # Only pay for a full page fetch if snippets were too thin to answer from.
    if sum(len(p) for p in parts) < 400:
        for r in search(query, max_results=2):
            body = fetch_clean(r.get("href", ""), timeout=timeout)
            if body:
                parts.append(f"[{r.get('title', 'page')}] {body[:1500]}")
                break

    return "\n\n".join(parts)[:max_chars]
