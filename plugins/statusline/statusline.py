"""Claude Code statusline — luxury instrument panel."""
import sys
import os

# Ensure the package is importable from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from statusline_pkg.__main__ import main

main()
