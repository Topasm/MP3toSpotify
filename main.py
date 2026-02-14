# -*- coding: utf-8 -*-
"""
main.py - Scan local music files and match them on Spotify.

Reads audio metadata (title, artist) from local files using TinyTag,
searches Spotify for matches, and adds found tracks to a playlist.
Unmatched songs are written to a failure log for later retry.

Usage:
    python main.py <username> [options]

Examples:
    python main.py myusername
    python main.py myusername -d "C:/Music" -p 37i9dQZF1DXcBWIGoYBM5M
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Generator

from tinytag import TinyTag

from encoding_utils import fix_mojibake
from spotify_client import SpotifyClient


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Match local music files to Spotify and add to a playlist.",
        epilog="Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET env vars first.",
    )
    parser.add_argument("username", help="Spotify username or user URI")
    parser.add_argument(
        "-p", "--playlist-id", default="", help="Existing Spotify playlist ID (optional)"
    )
    parser.add_argument(
        "-d", "--music-dir", default="", help="Path to local music directory"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="failed_matches.txt",
        help="Output file for unmatched songs (default: failed_matches.txt)",
    )
    return parser.parse_args()


def get_music_dir(music_dir: str) -> str:
    """Validate or prompt for the music directory path.

    Args:
        music_dir: Path from CLI args. If empty, prompts the user.

    Returns:
        A validated directory path.
    """
    if music_dir and os.path.isdir(music_dir):
        print(f"Found valid path: {music_dir}")
        return music_dir

    if music_dir:
        print(f"Warning: '{music_dir}' is not a valid directory.")

    while True:
        music_dir = input("Please paste the path to your music directory: ").strip()
        if os.path.isdir(music_dir):
            return music_dir
        print(
            "The provided path is not valid. Please try again.\n"
            "(Press Ctrl+C to exit)"
        )


def scan_music_files(
    music_dir: str,
) -> Generator[tuple[str, str], None, None]:
    """Recursively scan audio files and yield (query, display_name) pairs.

    Uses TinyTag to read metadata. Applies mojibake recovery to handle
    ID3v1 tags with legacy encodings (CP949, Shift-JIS, etc.).

    Args:
        music_dir: Root directory to scan.

    Yields:
        Tuples of (spotify_query, "artist - title") for each audio file.
    """
    files_read = 0

    for subdir, _, files in os.walk(music_dir):
        for file in files:
            filepath = os.path.join(subdir, file)
            try:
                tag = TinyTag.get(filepath)
            except Exception:
                # Skip files TinyTag can't parse (non-audio, corrupted, etc.)
                continue

            title = fix_mojibake(tag.title or "") or os.path.splitext(file)[0]
            artist = fix_mojibake(tag.artist or "") or "Unknown"

            files_read += 1
            query = f"track:{title} artist:{artist}"
            display = f"{artist} - {title}"
            yield query, display

    if files_read == 0:
        print(
            "\nNo audio files found at the specified location.\n"
            "Please check the path to the directory is correct."
        )
        sys.exit(1)

    print(
        f"\nRead {files_read} audio files.\n"
        "Note: Some files may have been skipped due to unsupported formats "
        "or corrupted metadata.\n"
    )


def main() -> None:
    """Main entry point."""
    args = parse_args()
    client = SpotifyClient(args.username)
    music_dir = get_music_dir(args.music_dir)

    track_ids: list[str] = []
    searched = 0

    with open(args.output, "w", encoding="utf-8") as failed_file:
        for query, display in scan_music_files(music_dir):
            searched += 1
            print(f"  {searched}: {display}", end=" ")

            track_id = client.search(query)
            if track_id:
                print("✓")
                track_ids.append(track_id)
            else:
                print("✗ NO MATCH")
                failed_file.write(f"{display}\n")

    # Summary
    matched = len(track_ids)
    if searched > 0:
        rate = matched / searched * 100
        print(f"\n{'='*50}")
        print(f"  Total scanned : {searched}")
        print(f"  Matched       : {matched} ({rate:.1f}%)")
        print(f"  Unmatched     : {searched - matched}")
        print(f"{'='*50}\n")
    else:
        print("\nNo songs were searched.")
        return

    # Add to playlist
    if track_ids:
        playlist_id = client.ensure_playlist(args.playlist_id)
        added = client.add_tracks(playlist_id, track_ids)
        print(f"Successfully added {added} songs to the playlist.")
    else:
        print("No matched songs to add.")

    if searched > matched:
        print(
            f"\n{searched - matched} unmatched songs written to '{args.output}'.\n"
            "Use retry_failed.py to retry with advanced search strategies."
        )

    print("\nDone! Thank you for using MP3toSpotify.")


if __name__ == "__main__":
    main()
