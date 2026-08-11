"""
One palette for the whole TUI, in light and dark.

Set `ui.theme` in core/config.json to "dark", "light" or "auto".
"auto" follows the Windows apps-light-theme setting.

--------------------------------------------------------------------------
Why this file exists
--------------------------------------------------------------------------
main.py declared a three-entry rich.Theme and then bypassed it everywhere:
`dim cyan` for routing, `yellow` for ignored speech, `white` for the user,
`bright_white` for Phoenix, `bold magenta` for the banner, `bold red` for
errors. Six unrelated hues with no relationship to each other, plus a second
formatter in manager.py with its own emoji. That is the "rainbow" - not a
choice anyone made, just what accumulates when styles are written inline.

--------------------------------------------------------------------------
The rules
--------------------------------------------------------------------------
1. ONE accent hue plus a grey ramp. Everything is either the accent or a step
   on the ramp. Colour is not decoration; it means something.
2. Hierarchy comes from WEIGHT and DIMMING, not from hue. Timestamp, speaker
   and body separate by lightness on one hue, which survives both themes -
   three different colours do not.
3. Semantic colour (warn, error) is the only exception, and stays rare enough
   to still be a signal.
4. TRUECOLOR HEX, never the 16 ANSI names. `bright_blue` is remapped by every
   terminal profile, so an ANSI palette cannot be verified or kept consistent
   across machines. `dim bright_black` - the old timestamp style - is close to
   invisible on a light background, which is the classic failure this avoids.
5. AA contrast (>= 4.5:1) for body text in BOTH themes. Verified by
   `tests/test_theme.py`, which computes the ratios rather than trusting eyes.

The hue is blue-cyan: it is already Phoenix's identity colour, and it reads as
calm and technical rather than urgent. Red, magenta and yellow are gone as
decoration; they now mean only "something is wrong".
"""

from __future__ import annotations

import os
from typing import Dict

# Assumed terminal backgrounds. Not painted - the terminal owns its background -
# but every contrast ratio below is computed against these, so a user on a
# wildly different background gets a different (unverified) result.
BACKGROUND = {"dark": "#0d1117", "light": "#ffffff"}

# Slate-and-blue. Values are drawn from a palette already validated for
# accessible contrast rather than picked by eye.
DARK: Dict[str, str] = {
    "text": "#e6edf3",      # body
    "dim": "#8b949e",       # secondary: timestamps, hints
    # Tertiary. #6e7681 was the natural next step down the ramp but measures
    # 4.12:1 - under AA. Timestamps and ignored speech are quiet, not optional,
    # so the ramp bends here to keep them readable.
    "faint": "#7d8590",
    "accent": "#58a6ff",    # the one hue
    "accent_soft": "#79c0ff",
    "warn": "#d29922",
    "error": "#f85149",
    "surface": "#30363d",   # separators
}

LIGHT: Dict[str, str] = {
    "text": "#1f2328",
    "dim": "#57606a",
    "faint": "#6e7681",
    "accent": "#0969da",
    "accent_soft": "#0550ae",
    "warn": "#9a6700",
    "error": "#cf222e",
    "surface": "#d0d7de",
}

PALETTES = {"dark": DARK, "light": LIGHT}


def resolve_mode(setting: str = "auto") -> str:
    """'dark' | 'light' | 'auto' -> a concrete mode."""
    mode = str(setting or "auto").strip().lower()
    if mode in PALETTES:
        return mode
    if mode != "auto":
        return "dark"
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        apps_use_light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if apps_use_light else "dark"
    except Exception:
        # Terminals are far more often dark, and light-on-dark is the safer
        # miss: dark text on a dark terminal is unreadable, the reverse is not.
        return "dark"


def build_styles(mode: str = None, setting: str = "auto") -> Dict[str, str]:
    """
    Semantic style name -> rich style string.

    Every style used anywhere in the TUI must be named here. A style string
    written inline in main.py is, by definition, outside the palette - which is
    what makes a palette enforceable rather than aspirational.
    """
    mode = mode or resolve_mode(setting)
    c = PALETTES.get(mode, DARK)

    return {
        # identity
        "phoenix": f"bold {c['accent']}",
        "user": f"bold {c['text']}",
        "banner": f"bold {c['accent']}",
        "version": c["faint"],
        # message bodies - separated from their speaker label by weight, not hue
        "reply": c["text"],
        "said": c["text"],
        "time": c["faint"],
        # secondary information
        "muted": c["dim"],
        "route": c["dim"],
        "status": c["dim"],
        "hint": c["faint"],
        "rule": c["surface"],
        # speech Phoenix heard but did not act on. Deliberately the SAME dim
        # grey as other secondary text: it is not a problem, and colouring it
        # yellow made every ambient noise look like a warning.
        "ignored": c["faint"],
        "ignored_label": c["faint"],
        # the only two colours that mean something is wrong
        "warn": c["warn"],
        "error": f"bold {c['error']}",
        # state indicators - visible when looked for, never attention-grabbing
        "awake": c["accent"],
        "dormant": c["faint"],
        "offline": c["warn"],
    }


def build_theme(setting: str = "auto"):
    """A rich.Theme for the configured mode."""
    from rich.theme import Theme

    return Theme(build_styles(setting=setting))


def safe_chars(stream=None):
    """
    Box-drawing characters, or ASCII when the console cannot encode them.

    A Windows console still running cp1252 raises UnicodeEncodeError on U+2500,
    which takes down the whole TUI thread rather than printing a wrong glyph.
    main.py reconfigures stdout to UTF-8 at startup, so this is the belt to
    that braces - and it is what makes the header safe on a console we have not
    seen.
    """
    import sys

    stream = stream or sys.stdout
    encoding = getattr(stream, "encoding", None) or "ascii"
    fancy = {"rule": "─", "sep": "·"}
    try:
        for ch in fancy.values():
            ch.encode(encoding)
        return fancy
    except (UnicodeEncodeError, LookupError):
        return {"rule": "-", "sep": "|"}


def get_setting() -> str:
    """Read `ui.theme` from AppConfig without importing it at module load."""
    try:
        from core.config import AppConfig

        return str(getattr(AppConfig, "ui", {}).get("theme", "auto"))
    except Exception:
        return "auto"


# --------------------------------------------------------------------------
# Contrast, for the test suite. Kept here so the palette and the rule that
# validates it live in the same file and cannot drift apart.
# --------------------------------------------------------------------------


def _srgb_to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    r, g, b = (_srgb_to_linear(x) for x in (r, g, b))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 2.1 contrast ratio. 4.5 is AA for body text, 3.0 for large/UI."""
    a, b = relative_luminance(fg), relative_luminance(bg)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)
