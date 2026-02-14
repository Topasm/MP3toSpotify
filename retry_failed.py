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
    parser.add_argument("username", help="Spotify username or user URI")
    parser.add_argument(
        "-p", "--playlist-id", default="", help="Existing Spotify playlist ID (optional)"
    )
    parser.add_argument(
        "-i",
        "--input",
        default="failed_matches.txt",
        help="Input file with failed matches (default: failed_matches.txt)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="still_failed.txt",
        help="Output file for still-unmatched songs (default: still_failed.txt)",
    )
    return parser.parse_args()


def parse_song_line(line: str) -> tuple[str, str]:
    """Parse 'Artist - Title' line into (artist, title).

    Handles various formats:
        - Artist - Title
        - Artist - Title (feat. Someone)
        - Artist/Artist2 - Title

    Args:
        line: A song line to parse.

    Returns:
        Tuple of (artist, title). Artist may be empty if no separator found.
    """
    line = line.strip()
    if not line:
        return "", ""

    if " - " in line:
        artist, title = line.split(" - ", 1)
        return " ".join(artist.split()), " ".join(title.split())

    return "", " ".join(line.split())


def build_search_queries(artist: str, title: str) -> list[str]:
    """Generate multiple search query variations for better matching.

    Tries progressively looser queries:
        1. Exact track + artist
        2. Simple text search
        3. Title only
        4. Brackets/parentheses removed
        5. feat./ft. removed

    Args:
        artist: Artist name.
        title: Song title.

    Returns:
        List of search query strings, ordered from most to least specific.
    """
    queries: list[str] = []

    # 1. Exact: track + artist
    if artist and title:
        queries.append(f"track:{title} artist:{artist}")

    # 2. Simple text search
    if artist and title:
        queries.append(f"{artist} {title}")

    # 3. Title only
    if title:
        queries.append(f"track:{title}")

    # 4. Remove brackets and parentheses
    clean_title = re.sub(r"\([^)]*\)", "", title).strip()
    clean_title = re.sub(r"\[[^\]]*\]", "", clean_title).strip()
    if clean_title and clean_title != title:
        if artist:
            queries.append(f"track:{clean_title} artist:{artist}")
        queries.append(f"{artist} {clean_title}" if artist else f"track:{clean_title}")

    # 5. Remove feat./ft.
    if re.search(r"feat\.?|ft\.?", title, re.IGNORECASE):
        no_feat = re.sub(
            r"[\(\[]?\s*(?:feat|ft)\.?\s*[^\)\]]*[\)\]]?",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()
        if no_feat and no_feat != title and no_feat != clean_title:
            if artist:
                queries.append(f"track:{no_feat} artist:{artist}")
            queries.append(f"{artist} {no_feat}" if artist else f"track:{no_feat}")

    return queries


def search_with_fallback(
    client: SpotifyClient, artist: str, title: str
) -> str | None:
    """Try multiple search queries until a match is found.

    Args:
        client: SpotifyClient instance.
        artist: Artist name.
        title: Song title.

    Returns:
        Track ID if found, None otherwise.
    """
    queries = build_search_queries(artist, title)

    for query in queries:
        track_id = client.search(query)
        if track_id:
            return track_id
        sleep(0.05)  # Brief pause between queries to avoid rate limiting.

    return None


def read_failed_songs(filepath: str) -> list[str]:
    """Read and fix encoding of failed matches file.

    Each line is run through mojibake recovery before being returned.

    Args:
        filepath: Path to the failed matches file.

    Returns:
        List of (possibly encoding-fixed) song lines.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [fix_song_line(line) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except UnicodeDecodeError:
        # Try with latin-1 as fallback for files saved in legacy encoding.
        with open(filepath, "r", encoding="latin-1") as f:
            lines = [fix_song_line(line) for line in f if line.strip()]

    return lines


def main() -> None:
    """Main entry point."""
    args = parse_args()
    client = SpotifyClient(args.username)

    # Read failed songs
    songs = read_failed_songs(args.input)
    total = len(songs)

    if total == 0:
        print(f"No songs found in '{args.input}'.")
        return

    print(f"\n{'='*50}")
    print(f"  MP3toSpotify - Retry Failed Matches")
    print(f"  Input : {args.input} ({total} songs)")
    print(f"{'='*50}\n")

    track_ids: list[str] = []
    still_failed: list[str] = []

    for i, song_line in enumerate(songs, 1):
        artist, title = parse_song_line(song_line)
        display = song_line[:65].ljust(65)
        print(f"  [{i:>4}/{total}] {display}", end=" ")

        if not title:
            print("SKIP (no title)")
            still_failed.append(song_line)
            continue

        track_id = search_with_fallback(client, artist, title)
        if track_id:
            print("✓ FOUND")
            track_ids.append(track_id)
        else:
            print("✗ NOT FOUND")
            still_failed.append(song_line)

        # Brief pause every 10 songs to respect rate limits.
        if i % 10 == 0:
            sleep(0.1)

    # Summary
    matched = len(track_ids)
    failed = len(still_failed)
    print(f"\n{'='*50}")
    print(f"  Results")
    print(f"  Found     : {matched}")
    print(f"  Not found : {failed}")
    print(f"{'='*50}\n")

    # Save still-failed songs
    if still_failed:
        with open(args.output, "w", encoding="utf-8") as f:
            for song in still_failed:
                f.write(song + "\n")
        print(f"Still-failed songs written to '{args.output}'.")

    # Add to playlist
    if track_ids:
        playlist_id = client.ensure_playlist(args.playlist_id, name="MP3toSpotify - Retry")
        added = client.add_tracks(playlist_id, track_ids)
        print(f"\nSuccessfully added {added} songs to the playlist!")
    else:
        print("No songs found to add.")

    print("\nDone!")


if __name__ == "__main__":
    main()
