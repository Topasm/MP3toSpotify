# -*- coding: utf-8 -*-
"""
cli.py - Unified entry point for PyInstaller bundling.

Dispatches to main.py (scan), retry_failed.py (retry),
youtube_import.py (youtube), or addtracks (GUI selective add)
based on the first argument.
This allows a single exe to handle all workflows.

Usage (when bundled as mp3tospotify.exe):
    mp3tospotify.exe scan <username> [options]
    mp3tospotify.exe retry <username> [options]
    mp3tospotify.exe youtube <username> -u <url> [options]
    mp3tospotify.exe addtracks <username> -p <playlist_id> --tracks id1,id2,...
"""

from __future__ import annotations

import json
import sys


def _add_tracks_main() -> None:
    """Add selected track IDs to a Spotify playlist (called from GUI)."""
    import argparse

    parser = argparse.ArgumentParser(description="Add tracks to playlist")
    parser.add_argument("username", help="Spotify username")
    parser.add_argument("-p", "--playlist-id", default="", help="Playlist ID")
    parser.add_argument("-n", "--playlist-name", default="MP3toSpotify", help="Playlist name if creating new")
    parser.add_argument("--tracks", required=True, help="Comma-separated Spotify track IDs")
    parser.add_argument("--gui", action="store_true", help="JSON output mode")
    args = parser.parse_args()

    track_ids = [t.strip() for t in args.tracks.split(",") if t.strip()]
    if not track_ids:
        if args.gui:
            print(json.dumps({"type": "error", "text": "No tracks provided."}), flush=True)
        else:
            print("No tracks provided.")
        sys.exit(1)

    from spotify_client import SpotifyClient

    client = SpotifyClient(args.username)
    playlist_id = client.ensure_playlist(args.playlist_id, name=args.playlist_name)
    added = client.add_tracks(playlist_id, track_ids)

    if args.gui:
        print(json.dumps({
            "type": "summary",
            "total": len(track_ids),
            "matched": added,
            "failed": len(track_ids) - added,
        }), flush=True)
    else:
        print(f"Added {added} tracks to playlist {playlist_id}.")


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "MP3toSpotify - Match local music to Spotify\n\n"
            "Commands:\n"
            "  scan      <username> [options]            Scan local files and match\n"
            "  retry     <username> [options]            Retry failed matches\n"
            "  youtube   <username> -u <url> [options]   Import YouTube playlist\n"
            "  addtracks <username> --tracks id1,id2,..  Add tracks to playlist\n\n"
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
    elif command == "addtracks":
        _add_tracks_main()
    else:
        print(f"Unknown command: {command}")
        print("Use 'scan', 'retry', 'youtube', or 'addtracks'. Run without arguments for help.")
        sys.exit(1)


if __name__ == "__main__":
    main()
