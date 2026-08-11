"""
Theme tests: contrast is measured, and the palette is enforced.

Two of these are guards rather than checks. The old TUI did not have a bad
palette because someone chose one - it had six unrelated hues because styles
were written inline at the call site, one at a time, each reasonable on its
own. So:

  * test_no_inline_colours   fails if a colour literal reappears in the TUI
  * test_every_used_style_is_defined  fails if a style name is used but unnamed

Together they mean the palette cannot quietly drift back.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pytest W:\\workplace-1\\Phoenix\\tests\\test_theme.py -q
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.theme import (  # noqa: E402
    BACKGROUND,
    DARK,
    LIGHT,
    PALETTES,
    build_styles,
    contrast_ratio,
    resolve_mode,
    safe_chars,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAIN = os.path.join(ROOT, "main.py")

# Colours that are separators, not text. A rule must be quiet; holding it to
# text contrast would make it a second accent.
NON_TEXT = {"surface"}

# The 16 ANSI names. Every terminal profile remaps these, so a palette built
# from them cannot be verified or kept consistent across machines.
ANSI_NAMES = {
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
}


def test_palettes_have_the_same_keys():
    """A key in one theme and not the other is a crash in that theme only."""
    assert set(DARK) == set(LIGHT)


@pytest.mark.parametrize("mode", ["dark", "light"])
def test_text_colours_meet_wcag_aa(mode):
    bg = BACKGROUND[mode]
    for name, colour in PALETTES[mode].items():
        if name in NON_TEXT:
            continue
        ratio = contrast_ratio(colour, bg)
        assert ratio >= 4.5, (
            f"{mode}/{name} {colour} on {bg} is {ratio:.2f}:1, below AA (4.5:1)"
        )


@pytest.mark.parametrize("mode", ["dark", "light"])
def test_separator_is_visible_but_quiet(mode):
    """A rule you cannot see is decoration; one you cannot ignore is noise."""
    ratio = contrast_ratio(PALETTES[mode]["surface"], BACKGROUND[mode])
    assert 1.2 <= ratio <= 2.5, f"{mode} rule is {ratio:.2f}:1"


@pytest.mark.parametrize("mode", ["dark", "light"])
def test_styles_build_for_both_modes(mode):
    styles = build_styles(mode)
    assert styles
    for name, value in styles.items():
        assert value, f"{name} is empty"
        for token in value.replace("bold ", "").split():
            if token.startswith("#"):
                assert re.fullmatch(r"#[0-9a-fA-F]{6}", token), f"{name}: {token}"
            else:
                assert token not in ANSI_NAMES, (
                    f"{name} uses the ANSI name {token!r}; terminals remap those"
                )


def test_resolve_mode():
    assert resolve_mode("dark") == "dark"
    assert resolve_mode("light") == "light"
    assert resolve_mode("DARK") == "dark"
    assert resolve_mode("auto") in ("dark", "light")
    # Junk must not raise, and must not land on light: dark text on a dark
    # terminal is unreadable, the reverse is merely ugly.
    assert resolve_mode("banana") == "dark"
    assert resolve_mode(None) in ("dark", "light")


def test_safe_chars_falls_back_on_a_narrow_console():
    class Cp1252:
        encoding = "cp1252"

    class Utf8:
        encoding = "utf-8"

    assert safe_chars(Utf8())["rule"] == "─"
    ascii_only = safe_chars(Cp1252())
    assert ascii_only["rule"] == "-"
    for value in ascii_only.values():
        value.encode("cp1252")  # must not raise


def _used_styles(path):
    src = open(path, encoding="utf-8").read()
    return set(re.findall(r'style="([a-z_]+)"', src))


def test_every_used_style_is_defined():
    """A style name rich cannot resolve renders as unstyled text, silently."""
    defined = set(build_styles("dark"))
    for used in _used_styles(MAIN):
        assert used in defined, f"main.py uses style {used!r}, absent from the theme"


def test_no_inline_colours():
    """
    The actual regression guard. This is how the rainbow grew the first time:
    not by choosing six hues, but by writing one colour at a time at the call
    site, each defensible on its own.
    """
    src = open(MAIN, encoding="utf-8").read()
    offenders = []

    for match in re.finditer(r'style="([^"]+)"', src):
        for token in match.group(1).replace("bold ", "").replace("dim ", "").split():
            if token in ANSI_NAMES or token.startswith("#"):
                offenders.append(match.group(1))

    # rich console markup, e.g. "[bold magenta]...[/]"
    for match in re.finditer(r"\[(/?[a-z_ ]+)\]", src):
        for token in match.group(1).split():
            if token in ANSI_NAMES:
                offenders.append(match.group(1))

    assert not offenders, (
        "inline colours in main.py: "
        + ", ".join(sorted(set(offenders)))
        + " - name them in core/theme.py instead"
    )


def test_no_emoji_in_tui_sources():
    """
    The project's own rule (CLAUDE.md): no emoji in console output. manager.py
    carried a parallel emoji formatter, and its noise filter matched on those
    emoji - so changing a message's prefix silently disabled the filter.
    """
    targets = [MAIN, os.path.join(ROOT, "Utils", "runners", "manager.py")]
    bad = []
    for path in targets:
        for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
            for ch in line:
                if ord(ch) > 0x2100 and ch not in "─│┌┐└┘├┤┬┴┼—–‘’“”·…":
                    bad.append(f"{os.path.basename(path)}:{lineno} {ch!r}")
    assert not bad, "emoji/pictographs in console output: " + ", ".join(bad[:8])
