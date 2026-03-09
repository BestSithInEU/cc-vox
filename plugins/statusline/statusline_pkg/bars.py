"""Gradient progress bars with sub-character precision and factory selection."""

from .theme import rgb, RST, TEAL, YELLOW, RED, GREEN, palette_rgb

BLOCKS = " \u258f\u258e\u258d\u258c\u258b\u258a\u2589\u2588"


def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def make_bar(pct, width, c_start, c_end, track_c=None):
    """Gradient bar with sub-character precision and soft track."""
    if track_c is None:
        track_c = palette_rgb("bar_track")
    total_eighths = int(pct * width * 8 / 100)
    full = total_eighths // 8
    partial = total_eighths % 8
    has_partial = partial > 0
    empties = width - full - (1 if has_partial else 0)

    bar = ""
    for i in range(full):
        t = i / max(width - 1, 1)
        bar += rgb(*lerp(c_start, c_end, t)) + "\u2588"

    if has_partial:
        t = full / max(width - 1, 1)
        bar += rgb(*lerp(c_start, c_end, t)) + BLOCKS[partial]

    bar += rgb(*track_c) + "\u2588" * empties + RST
    return bar


def _build_styles():
    """Build bar styles from active palette."""
    return {
        "context": [
            (50,  palette_rgb("bar_ctx_healthy_start"), palette_rgb("bar_ctx_healthy_end"), TEAL),
            (80,  palette_rgb("bar_ctx_warm_start"),    palette_rgb("bar_ctx_warm_end"),    YELLOW),
            (100, palette_rgb("bar_ctx_hot_start"),     palette_rgb("bar_ctx_hot_end"),     RED),
        ],
        "window": [
            (60,  palette_rgb("bar_win_healthy_start"), palette_rgb("bar_win_healthy_end"), GREEN),
            (85,  palette_rgb("bar_win_warm_start"),    palette_rgb("bar_win_warm_end"),    YELLOW),
            (100, palette_rgb("bar_win_hot_start"),     palette_rgb("bar_win_hot_end"),     RED),
        ],
        "weekly": [
            (50,  palette_rgb("bar_wk_healthy_start"),  palette_rgb("bar_wk_healthy_end"),  GREEN),
            (80,  palette_rgb("bar_wk_warm_start"),     palette_rgb("bar_wk_warm_end"),     YELLOW),
            (100, palette_rgb("bar_wk_hot_start"),      palette_rgb("bar_wk_hot_end"),      RED),
        ],
    }


_STYLES = _build_styles()


def get_bar(name, pct, width):
    """Factory: return (bar_string, label_color) for a named bar style."""
    for threshold, c_start, c_end, label_color in _STYLES[name]:
        if pct < threshold:
            return make_bar(pct, width, c_start, c_end), label_color
    _, c_start, c_end, label_color = _STYLES[name][-1]
    return make_bar(pct, width, c_start, c_end), label_color
