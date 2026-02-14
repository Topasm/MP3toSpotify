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
import json
import re
import sys
from time import sleep

from encoding_utils import fix_song_line
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


# ── GUI-aware output ───────────────────────────────────────────────────────

def emit(gui_mode: bool, msg: dict) -> None:
    """Send a JSON message to stdout (for GUI)."""
    if gui_mode:
        print(json.dumps(msg, ensure_ascii=False), flush=True)


# ── Song parsing & search logic ────────────────────────────────────────────

def parse_song_line(line: str) -> tuple[str, str]:
    """Parse 'Artist - Title' line into (artist, title)."""
    line = line.strip()
    if not line:
        return "", ""

    if " - " in line:
        artist, title = line.split(" - ", 1)
        return " ".join(artist.split()), " ".join(title.split())

    return "", " ".join(line.split())


def build_search_queries(artist: str, title: str) -> list[str]:
    """Generate multiple search query variations for better matching."""
    queries: list[str] = []

    if artist and title:
        queries.append(f"track:{title} artist:{artist}")
    if artist and title:
        queries.append(f"{artist} {title}")
    if title:
        queries.append(f"track:{title}")

    # Remove brackets/parentheses
    clean_title = re.sub(r"\([^)]*\)", "", title).strip()
    clean_title = re.sub(r"\[[^\]]*\]", "", clean_title).strip()
    if clean_title and clean_title != title:
        if artist:
            queries.append(f"track:{clean_title} artist:{artist}")
        queries.append(f"{artist} {clean_title}" if artist else f"track:{clean_title}")

    # Remove feat./ft.
    if re.search(r"feat\.?|ft\.?", title, re.IGNORECASE):
        no_feat = re.sub(
            r"[\(\[]?\s*(?:feat|ft)\.?\s*[^\)\]]*[\)\]]?", "",
            title, flags=re.IGNORECASE,
        ).strip()
        if no_feat and no_feat != title and no_feat != clean_title:
            if artist:
                queries.append(f"track:{no_feat} artist:{artist}")
            queries.append(f"{artist} {no_feat}" if artist else f"track:{no_feat}")

    return queries


def search_with_fallback(client: SpotifyClient, artist: str, title: str) -> str | None:
    """Try multiple search queries until a match is found."""
    for query in build_search_queries(artist, title):
        track_id = client.search(query)
        if track_id:
            return track_id
        sleep(0.05)
    return None


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
        emit(True, {"type": "progress", "text": f"Loaded {total} songs", "total": total, "current": 0})
    else:
        print(f"\n{'='*50}")
        print(f"  MP3toSpotify - Retry Failed Matches")
        print(f"  Input : {args.input} ({total} songs)")
        print(f"{'='*50}\n")

    track_ids: list[str] = []
    still_failed: list[str] = []

    for i, song_line in enumerate(songs, 1):
        artist, title = parse_song_line(song_line)

        if not title:
            still_failed.append(song_line)
            if gui:
                emit(True, {"type": "no_match", "name": song_line})
            else:
                print(f"  [{i:>4}/{total}] {song_line[:65].ljust(65)} SKIP")
            continue

        track_id = search_with_fallback(client, artist, title)

        if track_id:
            track_ids.append(track_id)
            if gui:
                emit(True, {"type": "match", "name": song_line})
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

    # Add to playlist
    if track_ids:
        playlist_id = client.ensure_playlist(args.playlist_id, name="MP3toSpotify - Retry")
        added = client.add_tracks(playlist_id, track_ids)
        if not gui:
            print(f"\nSuccessfully added {added} songs to the playlist!")
    elif not gui:
        print("No songs found to add.")

    if not gui:
        print("\nDone!")


if __name__ == "__main__":
    main()
