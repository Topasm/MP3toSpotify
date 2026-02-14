# -*- coding: utf-8 -*-
"""
cli.py - Unified entry point for PyInstaller bundling.

Dispatches to main.py (scan), retry_failed.py (retry), or
youtube_import.py (youtube) based on the first argument.
This allows a single exe to handle all workflows.

Usage (when bundled as mp3tospotify.exe):
    mp3tospotify.exe scan <username> [options]
    mp3tospotify.exe retry <username> [options]
    mp3tospotify.exe youtube <username> -u <url> [options]
"""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "MP3toSpotify - Match local music to Spotify\n\n"
            "Commands:\n"
            "  scan    <username> [options]            Scan local files and match\n"
            "  retry   <username> [options]            Retry failed matches\n"
            "  youtube <username> -u <url> [options]   Import YouTube playlist\n\n"
            "Examples:\n"
            '  mp3tospotify scan myuser -d "C:/Music"\n'
            "  mp3tospotify retry myuser -i failed_matches.txt\n"
            '  mp3tospotify youtube myuser -u "https://www.youtube.com/playlist?list=PLxxx"\n'
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
    elif command == "youtube":
        from youtube_import import main as youtube_main
        youtube_main()
    else:
        print(f"Unknown command: {command}")
        print("Use 'scan' or 'retry'. Run without arguments for help.")
        sys.exit(1)


if __name__ == "__main__":
    main()
