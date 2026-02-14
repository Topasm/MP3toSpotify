# -*- coding: utf-8 -*-
"""
youtube_import.py - Import a YouTube playlist into Spotify.

Extracts video titles from a YouTube playlist using yt-dlp (no download),
cleans them, searches each on Spotify, and adds matched tracks to a playlist.

Usage:
    python youtube_import.py <username> -u <youtube_url> [options]

Examples:
    python youtube_import.py myusername -u "https://www.youtube.com/playlist?list=PLxxxxxxx"
    python youtube_import.py myusername -u "https://youtu.be/..." -p 37i9dQZF1DXcBWIGoYBM5M
"""

from __future__ import annotations

import argparse
import re
import sys
from time import sleep

from encoding_utils import fix_mojibake
from gui_utils import emit
from search_strategies import search_with_fallback
from spotify_client import SpotifyClient


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Import a YouTube playlist into Spotify.",
        epilog="Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET env vars first.",
    )
    parser.add_argument("username", nargs="?", default="", help="Spotify username or user URI")
    parser.add_argument(
        "-u", "--url", required=True,
        help="YouTube playlist URL",
    )
    parser.add_argument(
        "-p", "--playlist-id", default="",
        help="Existing Spotify playlist ID (optional — creates new if empty)",
    )
    parser.add_argument(
        "-o", "--output", default="yt_failed_matches.txt",
        help="Output file for unmatched songs (default: yt_failed_matches.txt)",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Output JSON lines for Electron GUI (internal use)",
    )
    return parser.parse_args()

# ── YouTube Extraction ─────────────────────────────────────────────────────

def extract_playlist(url: str, gui: bool = False) -> list[dict[str, str]]:
    """
    Extract video titles and channel names from a YouTube playlist.
    Returns list of dicts: [{"title": ..., "channel": ...}, ...]
    Uses yt-dlp --flat-playlist to avoid downloading any media.
    """
    try:
        import yt_dlp
    except ImportError:
        msg = "yt-dlp is required. Install it: pip install yt-dlp"
        if gui:
            emit(True, {"type": "error", "text": msg})
        else:
            print(msg)
        sys.exit(1)

    entries: list[dict[str, str]] = []

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        msg = f"Failed to fetch YouTube playlist: {e}"
        if gui:
            emit(True, {"type": "error", "text": msg})
        else:
            print(msg)
        sys.exit(1)

    if not info:
        return entries

    # Single video
    if info.get("_type") != "playlist" and info.get("title"):
        entries.append({
            "title": info.get("title", ""),
            "channel": info.get("uploader", info.get("channel", "")),
        })
        return entries

    # Playlist
    for entry in info.get("entries", []):
        if entry is None:
            continue
        entries.append({
            "title": entry.get("title", ""),
            "channel": entry.get("uploader", entry.get("channel", "")),
        })

    return entries


# ── Title Cleaning ─────────────────────────────────────────────────────────

# Single compiled regex combining all YouTube noise patterns
_NOISE_RE = re.compile(
    r"""
    \(Official\s*(?:Music\s*)?Video\)  |
    \(Official\s*Audio\)               |
    \(Official\s*Lyric\s*Video\)       |
    \(Lyrics?\)                        |
    \(Visuali[sz]er\)                  |
    \(Audio\)                          |
    \(MV\)                             |
    \[MV\]                             |
    \[Official\s*(?:Music\s*)?Video\]  |
    \[Official\s*Audio\]               |
    \[Lyrics?\]                        |
    \bM/?V\b                           |
    \bHD\b                             |
    \b4K\b                             |
    \blyrics?\b                        |
    \bofficial\s*(?:music\s*)?video\b  |
    \bofficial\s*audio\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def clean_youtube_title(title: str) -> tuple[str, str]:
    """
    Parse a YouTube video title into (artist, song_title).

    Handles common patterns:
      - "Artist - Song Title"
      - "Artist - Song Title (Official Video)"
      - "Song Title" (artist unknown)

    Removes noise like [MV], (Official Video), (Lyrics), etc.
    """
    title = fix_mojibake(title)

    # Remove all YouTube noise in one pass
    title = _NOISE_RE.sub("", title)

    # Clean extra whitespace
    title = re.sub(r"\s+", " ", title).strip()
    # Remove trailing/leading punctuation junk
    title = title.strip("-–—|·•/\\")
    title = title.strip()

    # Try "Artist - Title" split
    separators = [" - ", " – ", " — ", " | ", " // "]
    for sep in separators:
        if sep in title:
            parts = title.split(sep, 1)
            artist = parts[0].strip()
            song = parts[1].strip()
            if artist and song:
                return artist, song

    return "", title


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point."""
    args = parse_args()
    gui = args.gui

    if not args.username:
        if gui:
            emit(True, {"type": "error", "text": "Username is required."})
            sys.exit(1)
        print("Error: username is required.\nUsage: python youtube_import.py <username> -u <url>")
        sys.exit(1)

    # Extract YouTube playlist
    if gui:
        emit(True, {"type": "progress", "text": "Fetching YouTube playlist...", "total": 0, "current": 0})
    else:
        print("\nFetching YouTube playlist...")

    entries = extract_playlist(args.url, gui)
    total = len(entries)

    if total == 0:
        msg = "No videos found in the YouTube playlist."
        if gui:
            emit(True, {"type": "error", "text": msg})
        else:
            print(msg)
        return

    if gui:
        emit(True, {"type": "total", "count": total})
        emit(True, {"type": "progress", "text": f"Found {total} videos", "total": total, "current": 0})
    else:
        print(f"\n{'='*55}")
        print(f"  MP3toSpotify - YouTube Playlist Import")
        print(f"  URL    : {args.url}")
        print(f"  Videos : {total}")
        print(f"{'='*55}\n")

    # Connect to Spotify
    client = SpotifyClient(args.username)

    track_ids: list[str] = []
    seen_ids: set[str] = set()          # deduplication
    seen_titles: set[str] = set()       # skip duplicate YouTube entries
    failed: list[str] = []

    for i, entry in enumerate(entries, 1):
        raw_title = entry["title"]
        channel = entry.get("channel", "")
        artist, song_title = clean_youtube_title(raw_title)
        display_name = f"{artist} - {song_title}" if artist else song_title

        # Skip duplicate YouTube titles
        title_key = display_name.lower().strip()
        if title_key in seen_titles:
            if gui:
                emit(True, {"type": "progress", "text": f"(dup) {display_name}", "current": i, "total": total})
            continue
        seen_titles.add(title_key)

        if gui:
            emit(True, {"type": "progress", "text": display_name, "current": i, "total": total})

        track_id = search_with_fallback(client, artist, song_title, channel)

        if track_id:
            if track_id not in seen_ids:
                seen_ids.add(track_id)
                track_ids.append(track_id)
            if gui:
                emit(True, {"type": "match", "name": display_name, "trackId": track_id})
            else:
                print(f"  [{i:>4}/{total}] {display_name[:55].ljust(55)} ✓ MATCHED")
        else:
            failed.append(display_name)
            if gui:
                emit(True, {"type": "no_match", "name": display_name})
            else:
                print(f"  [{i:>4}/{total}] {display_name[:55].ljust(55)} ✗ FAILED")

    # Summary
    matched_count = len(track_ids)
    failed_count = len(failed)

    if gui:
        emit(True, {
            "type": "summary",
            "total": total,
            "matched": matched_count,
            "failed": failed_count,
        })

    # Save failed
    if failed:
        with open(args.output, "w", encoding="utf-8") as f:
            for song in failed:
                f.write(song + "\n")
        if not gui:
            print(f"  ✗ {failed_count} unmatched songs saved to '{args.output}'")

    # In GUI mode, don't auto-add — let the user select via checkboxes
    if gui:
        return

    # CLI mode: add all matched tracks to playlist
    if track_ids:
        playlist_id = client.ensure_playlist(
            args.playlist_id, "YouTube Import — MP3toSpotify"
        )
        client.add_tracks(playlist_id, track_ids)
        print(f"\n  ✓ Added {matched_count} tracks to playlist: {playlist_id}")

    if total > 0:
        rate = (matched_count / total * 100)
        print(f"\n{'='*55}")
        print(f"  Results: {matched_count}/{total} matched ({rate:.1f}%)")
        print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
