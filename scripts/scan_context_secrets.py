#!/usr/bin/env python3
"""Compatibility entry point for scan_secrets.py. Usage: scan_context_secrets.py [ROOT]

Run me when: I need the old secret scan command. It runs the same checks as scan_secrets.py.
"""
from __future__ import annotations

import sys

from scan_secrets import main


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
