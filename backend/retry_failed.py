# -*- coding: utf-8 -*-
"""
retry_failed.py - Retry unmatched songs with advanced search strategies.

Reads a failed-matches file (from main.py) and retries Spotify search
using multiple query variations: bracket removal, feat. stripping,
title-only search, etc. Automatically recovers mojibake encoding.

Usage:
    python retry_failed.py <username> [options]

Examples:
    python retry_failed.py myusername
    python retry_failed.py myusername -i failed_matches.txt -p 37i9dQZF1DXcBWIGoYBM5M
"""

from __future__ import annotations

import argparse
import sys
from time import sleep

from encoding_utils import fix_song_line
from gui_utils import emit
from search_strategies import parse_song_line, search_with_fallback
from spotify_client import SpotifyClient


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Retry failed matches with advanced Spotify search strategies.",
        epilog="Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET env vars first.",
    )
    parser.add_argument("username", nargs="?", default="", help="Spotify username or user URI")
    parser.add_argument(
        "-p", "--playlist-id", default="", help="Existing Spotify playlist ID (optional)"
    )
    parser.add_argument(
        "-i", "--input", default="failed_matches.txt",
        help="Input file with failed matches (default: failed_matches.txt)",
    )
    parser.add_argument(
        "-o", "--output", default="still_failed.txt",
        help="Output file for still-unmatched songs (default: still_failed.txt)",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Output JSON lines for Electron GUI (internal use)",
    )
    return parser.parse_args()

# ── Helpers ────────────────────────────────────────────────────────────────


def read_failed_songs(filepath: str) -> list[str]:
    """Read and fix encoding of failed matches file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [fix_song_line(line) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="latin-1") as f:
            lines = [fix_song_line(line) for line in f if line.strip()]
    return lines


def main() -> None:
    """Main entry point."""
    args = parse_args()
    gui = args.gui

    if not args.username:
        if gui:
            emit(True, {"type": "error", "text": "Username is required."})
            sys.exit(1)
        print("Error: username is required.\nUsage: python retry_failed.py <username>")
        sys.exit(1)

    client = SpotifyClient(args.username)

    # Read failed songs
    songs = read_failed_songs(args.input)
    total = len(songs)

    if total == 0:
        msg = f"No songs found in '{args.input}'."
        if gui:
            emit(True, {"type": "error", "text": msg})
        else:
            print(msg)
        return

    if gui:
        emit(True, {"type": "total", "count": total})
        emit(True, {"type": "progress", "text": f"Loaded {total} songs", "total": total, "current": 0})
    else:
        print(f"\n{'='*50}")
        print(f"  MP3toSpotify - Retry Failed Matches")
        print(f"  Input : {args.input} ({total} songs)")
        print(f"{'='*50}\n")

    track_ids: list[str] = []
    seen_ids: set[str] = set()          # deduplication
    still_failed: list[str] = []

    for i, song_line in enumerate(songs, 1):
        artist, title = parse_song_line(song_line)

        if gui:
            emit(True, {"type": "progress", "text": song_line, "current": i, "total": total})

        if not title:
            still_failed.append(song_line)
            if gui:
                emit(True, {"type": "no_match", "name": song_line})
            else:
                print(f"  [{i:>4}/{total}] {song_line[:65].ljust(65)} SKIP")
            continue

        track_id = search_with_fallback(client, artist, title)

        if track_id:
            if track_id not in seen_ids:
                seen_ids.add(track_id)
                track_ids.append(track_id)
            if gui:
                emit(True, {"type": "match", "name": song_line, "trackId": track_id})
            else:
                print(f"  [{i:>4}/{total}] {song_line[:65].ljust(65)} ✓ FOUND")
        else:
            still_failed.append(song_line)
            if gui:
                emit(True, {"type": "no_match", "name": song_line})
            else:
                print(f"  [{i:>4}/{total}] {song_line[:65].ljust(65)} ✗ NOT FOUND")

        if i % 10 == 0:
            sleep(0.1)

    # Summary
    matched = len(track_ids)
    failed = len(still_failed)

    if gui:
        emit(True, {"type": "summary", "total": total, "matched": matched, "failed": failed})
    else:
        print(f"\n{'='*50}")
        print(f"  Results")
        print(f"  Found     : {matched}")
        print(f"  Not found : {failed}")
        print(f"{'='*50}\n")

    # Save still-failed
    if still_failed:
        with open(args.output, "w", encoding="utf-8") as f:
            for song in still_failed:
                f.write(song + "\n")
        if not gui:
            print(f"Still-failed songs written to '{args.output}'.")

    # In GUI mode, don't auto-add — let the user select via checkboxes
    if gui:
        return

    # CLI mode: add all matched tracks to playlist
    if track_ids:
        playlist_id = client.ensure_playlist(args.playlist_id, name="MP3toSpotify - Retry")
        added = client.add_tracks(playlist_id, track_ids)
        print(f"\nSuccessfully added {added} songs to the playlist!")
    else:
        print("No songs found to add.")

    print("\nDone!")


if __name__ == "__main__":
    main()
