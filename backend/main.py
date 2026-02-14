# -*- coding: utf-8 -*-
"""
main.py - Scan local music files and match them on Spotify.

Reads audio metadata (title, artist) from local files using TinyTag,
searches Spotify for matches, and adds found tracks to a playlist.
Unmatched songs are written to a failure log for later retry.

Usage:
    python main.py <username> [options]

Examples:
    python main.py myusername -d "C:/Music"
    python main.py myusername -d "C:/Music" -p 37i9dQZF1DXcBWIGoYBM5M
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Generator

from tinytag import TinyTag

from encoding_utils import fix_mojibake
from gui_utils import emit
from spotify_client import SpotifyClient


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Match local music files to Spotify and add to a playlist.",
        epilog="Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET env vars first.",
    )
    parser.add_argument("username", nargs="?", default="", help="Spotify username or user URI")
    parser.add_argument(
        "-p", "--playlist-id", default="", help="Existing Spotify playlist ID (optional)"
    )
    parser.add_argument(
        "-d", "--music-dir", default="", help="Path to local music directory"
    )
    parser.add_argument(
        "-o", "--output", default="failed_matches.txt",
        help="Output file for unmatched songs (default: failed_matches.txt)",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Output JSON lines for Electron GUI (internal use)",
    )
    return parser.parse_args()


# ── Helpers ────────────────────────────────────────────────────────────────

def get_music_dir(music_dir: str, gui_mode: bool) -> str:
    """Validate or prompt for the music directory path."""
    if music_dir and os.path.isdir(music_dir):
        if not gui_mode:
            print(f"Found valid path: {music_dir}")
        return music_dir

    if gui_mode:
        emit(True, {"type": "error", "text": f"Invalid music directory: {music_dir}"})
        sys.exit(1)

    if music_dir:
        print(f"Warning: '{music_dir}' is not a valid directory.")

    while True:
        music_dir = input("Please paste the path to your music directory: ").strip()
        if os.path.isdir(music_dir):
            return music_dir
        print("The provided path is not valid. Please try again.\n(Press Ctrl+C to exit)")


def scan_music_files(music_dir: str, gui_mode: bool = False) -> Generator[tuple[str, str], None, None]:
    """Recursively scan audio files and yield (query, display_name) pairs.

    Uses TinyTag to read metadata. Applies mojibake recovery to handle
    ID3v1 tags with legacy encodings (CP949, Shift-JIS, etc.).

    Args:
        music_dir: Root directory to scan.
        gui_mode: Whether running inside the Electron GUI.

    Yields:
        Tuples of (spotify_query, "artist - title") for each audio file.
    """
    supported_exts = (
        ".mp3", ".flac", ".ogg", ".opus", ".wma", ".wav",
        ".m4a", ".aac", ".aiff", ".dsf", ".wv"
    )
    files_read = 0

    for subdir, _, files in os.walk(music_dir):
        for file in files:
            if not file.lower().endswith(supported_exts):
                continue
                
            filepath = os.path.join(subdir, file)
            title = ""
            artist = ""
            
            try:
                tag = TinyTag.get(filepath)
                title = fix_mojibake(tag.title or "")
                artist = fix_mojibake(tag.artist or "")
            except Exception:
                # Metadata read failed, fallback to filename
                pass

            # Fallback if metadata missing or read failed
            if not title:
                title = os.path.splitext(file)[0]
            if not artist:
                artist = "Unknown"

            files_read += 1
            query = f"track:{title} artist:{artist}"
            display = f"{artist} - {title}"
            yield query, display

    if files_read == 0:
        msg = (
            "No audio files found at the specified location. "
            "Please check the path to the directory is correct."
        )
        if gui_mode:
            emit(True, {"type": "error", "text": msg})
        else:
            print(f"\n{msg}")
        sys.exit(1)

    if not gui_mode:
        print(f"\nRead {files_read} audio files.")


def _count_audio_files(music_dir: str) -> int:
    """Count audio files without reading metadata (fast pre-scan)."""
    count = 0
    for _, _, files in os.walk(music_dir):
        for f in files:
            if f.lower().endswith(
                (".mp3", ".flac", ".ogg", ".opus", ".wma", ".wav",
                 ".m4a", ".aac", ".aiff", ".dsf", ".wv")
            ):
                count += 1
    return count


def main() -> None:
    """Main entry point."""
    args = parse_args()
    gui = args.gui

    if not args.username:
        if gui:
            emit(True, {"type": "error", "text": "Username is required."})
            sys.exit(1)
        print("Error: username is required.\nUsage: python main.py <username> -d <music_dir>")
        sys.exit(1)

    client = SpotifyClient(args.username)
    music_dir = get_music_dir(args.music_dir, gui)

    # Pre-count files for accurate progress bar
    total_count = _count_audio_files(music_dir)
    if gui and total_count > 0:
        emit(True, {"type": "total", "count": total_count})

    track_ids: list[str] = []
    seen_ids: set[str] = set()          # deduplication
    searched = 0

    with open(args.output, "w", encoding="utf-8") as failed_file:
        for query, display in scan_music_files(music_dir, gui_mode=gui):
            searched += 1

            if gui:
                emit(True, {
                    "type": "progress",
                    "text": display,
                    "current": searched,
                    "total": total_count,
                })

            try:
                track_id = client.search(query)
            except Exception as e:
                # If search fails (API error, network, etc), treat as no match
                if gui:
                    emit(True, {"type": "error", "text": f"Error searching '{display}': {str(e)}"})
                track_id = None

            if track_id:
                if track_id not in seen_ids:
                    seen_ids.add(track_id)
                    track_ids.append(track_id)
                if gui:
                    emit(True, {"type": "match", "name": display, "trackId": track_id})
                else:
                    print(f"  {searched}: {display} ✓")
            else:
                failed_file.write(f"{display}\n")
                if gui:
                    emit(True, {"type": "fail", "name": display})
                else:
                    print(f"  {searched}: {display} ✗ NO MATCH")

    # Summary
    matched = len(track_ids)
    if gui:
        emit(True, {
            "type": "summary",
            "total": searched,
            "matched": matched,
            "failed": searched - matched,
        })
    elif searched > 0:
        rate = matched / searched * 100
        print(f"\n{'='*50}")
        print(f"  Total scanned : {searched}")
        print(f"  Matched       : {matched} ({rate:.1f}%)")
        print(f"  Unmatched     : {searched - matched}")
        print(f"{'='*50}\n")
    else:
        print("\nNo songs were searched.")
        return

    # In GUI mode, don't auto-add — let the user select via checkboxes
    if gui:
        return

    # CLI mode: add all matched tracks to playlist
    if track_ids:
        playlist_id = client.ensure_playlist(args.playlist_id)
        added = client.add_tracks(playlist_id, track_ids)
        print(f"Successfully added {added} songs to the playlist.")

    if searched > matched:
        print(
            f"\n{searched - matched} unmatched songs written to '{args.output}'.\n"
            "Use retry_failed.py to retry with advanced search strategies."
        )
    print("\nDone! Thank you for using MP3toSpotify.")


if __name__ == "__main__":
    main()
