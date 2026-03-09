"""Pricing constants and configuration."""

import datetime

# Istanbul timezone (UTC+3)
ISTANBUL_TZ = datetime.timezone(datetime.timedelta(hours=3))

# Bar display width
BAR_W = 20

# Pricing per million tokens: (input, output, cache_write, cache_read)
PRICING = {
    "claude-opus-4-6":              (5.00, 25.00, 6.25, 0.50),
    "claude-opus-4-5-20251101":     (5.00, 25.00, 6.25, 0.50),
    "claude-sonnet-4-6":            (3.00, 15.00, 3.75, 0.30),
    "claude-sonnet-4-5-20251101":   (3.00, 15.00, 3.75, 0.30),
    "claude-sonnet-4-5-20250929":   (3.00, 15.00, 3.75, 0.30),
    "claude-sonnet-4-20250514":     (3.00, 15.00, 3.75, 0.30),
    "claude-haiku-4-5-20251001":    (1.00,  5.00, 1.25, 0.10),
    "claude-haiku-4-5-20251101":    (1.00,  5.00, 1.25, 0.10),
}
DEFAULT_PRICING = (3.00, 15.00, 3.75, 0.30)
