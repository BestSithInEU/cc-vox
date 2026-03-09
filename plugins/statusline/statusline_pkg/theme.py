"""ANSI escape helpers, palette system, and format utilities."""

import json
import pathlib


def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


def bg(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"


RST  = "\033[0m"
DIM  = "\033[2m"
BOLD = "\033[1m"
ITAL = "\033[3m"


# ── Palette definitions ──────────────────────────────────────────────
# Each palette maps semantic role names to (r, g, b) tuples.

PALETTES = {
    "catppuccin": {
        "rosewater": (245, 224, 220),
        "flamingo":  (242, 205, 205),
        "pink":      (245, 194, 231),
        "mauve":     (203, 166, 247),
        "red":       (243, 139, 168),
        "maroon":    (235, 160, 172),
        "peach":     (250, 179, 135),
        "yellow":    (249, 226, 175),
        "green":     (166, 227, 161),
        "teal":      (148, 226, 213),
        "sky":       (137, 220, 235),
        "sapphire":  (116, 199, 236),
        "blue":      (137, 180, 250),
        "lavender":  (180, 190, 254),
        "text":      (205, 214, 244),
        "subtext1":  (186, 194, 222),
        "subtext0":  (166, 173, 200),
        "overlay2":  (147, 153, 178),
        "overlay1":  (127, 132, 156),
        "overlay0":  (108, 112, 134),
        "surface2":  (88, 91, 112),
        "surface1":  (69, 71, 90),
        "surface0":  (49, 50, 68),
        "base":      (30, 30, 46),
        "bar_track":    (40, 42, 54),
        # Bar gradient endpoints
        "bar_ctx_healthy_start":  (148, 226, 213),
        "bar_ctx_healthy_end":    (166, 227, 161),
        "bar_ctx_warm_start":     (249, 226, 175),
        "bar_ctx_warm_end":       (250, 179, 135),
        "bar_ctx_hot_start":      (250, 179, 135),
        "bar_ctx_hot_end":        (243, 139, 168),
        "bar_win_healthy_start":  (137, 220, 235),
        "bar_win_healthy_end":    (148, 226, 213),
        "bar_win_warm_start":     (249, 226, 175),
        "bar_win_warm_end":       (250, 179, 135),
        "bar_win_hot_start":      (250, 179, 135),
        "bar_win_hot_end":        (243, 139, 168),
        "bar_wk_healthy_start":   (137, 180, 250),
        "bar_wk_healthy_end":     (148, 226, 213),
        "bar_wk_warm_start":      (249, 226, 175),
        "bar_wk_warm_end":        (250, 179, 135),
        "bar_wk_hot_start":       (250, 179, 135),
        "bar_wk_hot_end":         (243, 139, 168),
        # Accent gradient
        "accent_healthy": (148, 226, 213),
        "accent_warm":    (250, 179, 135),
        "accent_hot":     (243, 139, 168),
    },

    "synthwave": {
        "rosewater": (255, 150, 200),   # hot pink glow
        "flamingo":  (255, 113, 206),   # neon pink
        "pink":      (255, 113, 206),   # neon pink
        "mauve":     (185, 103, 255),   # electric purple
        "red":       (255, 56, 100),    # neon red
        "maroon":    (255, 78, 120),    # hot rose
        "peach":     (255, 165, 48),    # amber glow
        "yellow":    (255, 230, 109),   # neon yellow
        "green":     (114, 255, 148),   # neon green
        "teal":      (0, 255, 213),     # electric cyan
        "sky":       (0, 210, 255),     # neon sky
        "sapphire":  (80, 170, 255),    # electric blue
        "blue":      (108, 140, 255),   # deep neon blue
        "lavender":  (190, 160, 255),   # soft violet
        "text":      (230, 225, 255),   # cool white with violet tint
        "subtext1":  (200, 195, 230),   # muted violet white
        "subtext0":  (170, 165, 200),   # dimmed violet
        "overlay2":  (140, 130, 170),   # mid dim
        "overlay1":  (115, 105, 145),   # label dim
        "overlay0":  (95, 85, 125),     # muted purple
        "surface2":  (72, 60, 100),     # dark purple border
        "surface1":  (55, 40, 85),      # deep purple
        "surface0":  (38, 25, 65),      # darker purple
        "base":      (20, 10, 40),      # midnight void
        "bar_track":    (30, 18, 55),   # deep void track
        # Bar gradients — neon cyan -> green -> yellow -> red
        "bar_ctx_healthy_start":  (0, 255, 213),
        "bar_ctx_healthy_end":    (114, 255, 148),
        "bar_ctx_warm_start":     (255, 230, 109),
        "bar_ctx_warm_end":       (255, 165, 48),
        "bar_ctx_hot_start":      (255, 113, 206),
        "bar_ctx_hot_end":        (255, 56, 100),
        "bar_win_healthy_start":  (80, 170, 255),
        "bar_win_healthy_end":    (0, 255, 213),
        "bar_win_warm_start":     (255, 230, 109),
        "bar_win_warm_end":       (255, 165, 48),
        "bar_win_hot_start":      (255, 113, 206),
        "bar_win_hot_end":        (255, 56, 100),
        "bar_wk_healthy_start":   (108, 140, 255),
        "bar_wk_healthy_end":     (0, 255, 213),
        "bar_wk_warm_start":      (255, 230, 109),
        "bar_wk_warm_end":        (255, 165, 48),
        "bar_wk_hot_start":       (255, 113, 206),
        "bar_wk_hot_end":         (255, 56, 100),
        # Accent
        "accent_healthy": (0, 255, 213),
        "accent_warm":    (255, 165, 48),
        "accent_hot":     (255, 56, 100),
    },
}


# ── Load active theme ────────────────────────────────────────────────
def _load_theme_name():
    """Read theme name from ~/.claude/statusline_theme.json or default."""
    try:
        cfg_path = pathlib.Path.home() / ".claude" / "statusline_theme.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            name = cfg.get("theme", "synthwave")
            if name in PALETTES:
                return name
    except Exception:
        pass
    return "synthwave"


_THEME = _load_theme_name()
_P = PALETTES[_THEME]


def _c(name):
    return rgb(*_P[name])


def palette_rgb(name):
    """Get raw (r,g,b) tuple for a palette color."""
    return _P[name]


# ── Semantic color exports ───────────────────────────────────────────
ROSEWATER = _c("rosewater")
FLAMINGO  = _c("flamingo")
PINK      = _c("pink")
MAUVE     = _c("mauve")
RED       = _c("red")
MAROON    = _c("maroon")
PEACH     = _c("peach")
YELLOW    = _c("yellow")
GREEN     = _c("green")
TEAL      = _c("teal")
SKY       = _c("sky")
SAPPHIRE  = _c("sapphire")
BLUE      = _c("blue")
LAVENDER  = _c("lavender")
TEXT      = _c("text")
SUBTEXT1  = _c("subtext1")
SUBTEXT0  = _c("subtext0")
OVERLAY2  = _c("overlay2")
OVERLAY1  = _c("overlay1")
OVERLAY0  = _c("overlay0")
SURFACE2  = _c("surface2")
SURFACE1  = _c("surface1")
SURFACE0  = _c("surface0")
BASE      = _c("base")

# ── Visual primitives ────────────────────────────────────────────────
DOT  = f" {SURFACE2}\u00b7{RST} "
PIPE = f" {SURFACE2}\u2502{RST} "


# ── Format helpers ───────────────────────────────────────────────────
def fmt_tok(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_cost(c):
    if c >= 100:
        return f"${c:.0f}"
    if c >= 10:
        return f"${c:.1f}"
    return f"${c:.2f}"


def cost_color(val):
    if val >= 50:  return PEACH
    if val >= 20:  return YELLOW
    if val >= 5:   return SAPPHIRE
    return TEAL
