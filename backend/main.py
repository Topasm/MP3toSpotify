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
import re
import sys
import traceback
from typing import Generator

from tinytag import TinyTag

from encoding_utils import fix_mojibake
from gui_utils import emit
from spotify_client import SpotifyClient
from search_strategies import search_with_fallback


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
            # Skip hidden files and macOS resource forks (._file.mp3)
            if file.startswith("."):
                continue

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

            # Fallback: parse artist/title from filename if metadata is missing
            if not title or not artist or artist == "Unknown":
                basename = os.path.splitext(file)[0]
                # Try common patterns: "Artist - Title", "Artist_-_Title", "Artist — Title"
                for sep in [" - ", " — ", " – ", "_-_"]:
                    if sep in basename:
                        parts = basename.split(sep, 1)
                        if not artist or artist == "Unknown":
                            artist = parts[0].strip()
                        if not title:
                            title = parts[1].strip()
                        break
                # If still no title, use full filename
                if not title:
                    title = basename.strip()
                # Clean up common junk from filenames
                # Remove leading track numbers like "01 ", "01. ", "01 - "
                title = re.sub(r"^\d{1,3}[\.\-\s]+\s*", "", title).strip()
                if not artist:
                    artist = "Unknown"

            files_read += 1
            # query = f"track:{title} artist:{artist}"
            display = f"{artist} - {title}"
            yield artist, title, display

    if files_read == 0:
        msg = (
            "No audio files found at the specified location. "
            "Please check the path to the directory is correct."
        )
        if gui_mode:
            emit(True, {"type": "error", "text": msg})
        else:
            print(msg)
        sys.exit(1)


def _count_audio_files(music_dir: str) -> int:
    """Count audio files without reading metadata (fast pre-scan)."""
    count = 0
    for _, _, files in os.walk(music_dir):
        for f in files:
            if f.startswith("."):
                continue
            if f.lower().endswith(
                (".mp3", ".flac", ".ogg", ".opus", ".wma", ".wav",
                 ".m4a", ".aac", ".aiff", ".dsf", ".wv")
            ):
                count += 1
    return count


def main() -> None:
    """Main entry point."""
    try:
        _main_logic()
    except Exception as e:
        # Catch unexpected crashes and report to GUI
        emit(True, {"type": "error", "text": f"Critical Error: {str(e)}"})
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _main_logic() -> None:
    """Core logic, wrapped by main() for error handling."""
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
    
    with open(args.output, "w", encoding="utf-8") as failed_file:
        for i, (artist, title, display_name) in enumerate(scan_music_files(music_dir, gui), 1):
            if gui:
                emit(True, {
                    "type": "progress",
                    "text": display_name,
                    "current": i,
                    "total": total_count,
                })

            track_id = search_with_fallback(client, artist, title)

            if track_id:
                if track_id not in seen_ids:
                    seen_ids.add(track_id)
                    track_ids.append(track_id)
                if gui:
                    emit(True, {
                        "type": "match",
                        "trackId": track_id,
                        "name": display_name 
                    })
                else:
                    print(f"  [{i}/{total_count}] {display_name[:60]:<60} ✓")
            else:
                if gui:
                    emit(True, {
                        "type": "no_match",
                        "name": display_name 
                    })
                else:
                    print(f"  [{i}/{total_count}] {display_name[:60]:<60} ✗")
                
                failed_file.write(f"{display_name}\n")
                failed_file.flush()

    # Summary
    found_count = len(track_ids)
    scanned_count = i if 'i' in locals() else 0
    
    if gui:
        emit(True, {
            "type": "summary",
            "total": total_count,
            "matched": found_count,
            "failed": scanned_count - found_count,
        })
    else:
        print(f"\nDone! Found {found_count} tracks.")
        print(f"Failed matches saved to '{args.output}'.")

    # Add to playlist (CLI only, GUI handles via IPC)
    if not gui and track_ids:
        if args.playlist_id:
            client.add_tracks(args.playlist_id, track_ids)
            print(f"Added {len(track_ids)} tracks to playlist.")
        elif args.playlist_name:
            pid = client.ensure_playlist(name=args.playlist_name)
            client.add_tracks(pid, track_ids)
            print(f"Added {len(track_ids)} tracks to playlist '{args.playlist_name}'.")
        else:
            print("No playlist specified. Tracks found but not added.")

    if not gui and scanned_count > found_count:
        print(
            f"\n{scanned_count - found_count} unmatched songs written to '{args.output}'.\n"
            "Use retry_failed.py to retry with advanced search strategies."
        )
    print("\nDone! Thank you for using MP3toSpotify.")


if __name__ == "__main__":
    main()
