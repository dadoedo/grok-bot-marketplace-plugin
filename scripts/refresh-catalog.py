#!/usr/bin/env python3
"""Refresh the checked-in Grok Bot marketplace catalog snapshot."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog import main

if __name__ == "__main__":
    sys.exit(main(["refresh", *sys.argv[1:]]))
