# -*- coding: utf-8 -*-
"""
cli.py - Unified entry point for PyInstaller bundling.

Dispatches to main.py (scan) or retry_failed.py (retry) based on
the first argument or --mode flag. This allows a single exe to
handle both workflows.

Usage (when bundled as mp3tospotify.exe):
    mp3tospotify.exe scan <username> [options]
    mp3tospotify.exe retry <username> [options]
"""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "MP3toSpotify - Match local music to Spotify\n\n"
            "Commands:\n"
            "  scan   <username> [options]   Scan local files and match\n"
            "  retry  <username> [options]   Retry failed matches\n\n"
            "Examples:\n"
            '  mp3tospotify scan myuser -d "C:/Music"\n'
            "  mp3tospotify retry myuser -i failed_matches.txt\n"
        )
        sys.exit(0)

    command = sys.argv[1].lower()
    # Remove the command from argv so argparse in submodules works correctly
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if command == "scan":
        from main import main as scan_main
        scan_main()
    elif command == "retry":
        from retry_failed import main as retry_main
        retry_main()
    else:
        print(f"Unknown command: {command}")
        print("Use 'scan' or 'retry'. Run without arguments for help.")
        sys.exit(1)


if __name__ == "__main__":
    main()
