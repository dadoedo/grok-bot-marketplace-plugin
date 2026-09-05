#!/usr/bin/env python3
"""Refresh the checked-in Grok Bot marketplace catalog snapshot."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog import main


def extra_args(argv: list[str]) -> list[str]:
    """Drop a redundant leading ``refresh`` so both invocation styles work."""
    args = argv[1:]
    if args and args[0] == "refresh":
        args = args[1:]
    return args


if __name__ == "__main__":
    sys.exit(main(["refresh", *extra_args(sys.argv)]))
