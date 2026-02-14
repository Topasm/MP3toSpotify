# -*- coding: utf-8 -*-
"""
search_strategies.py - Shared Spotify search strategies.

Provides multiple search query generation and fallback search logic
used by retry_failed.py, youtube_import.py, and the addtracks command.
Eliminates duplicated search logic across scripts.
"""

from __future__ import annotations

import re
from time import sleep

from spotify_client import SpotifyClient


def parse_song_line(line: str) -> tuple[str, str]:
    """Parse 'Artist - Title' line into (artist, title).

    Args:
        line: A song line, optionally in 'Artist - Title' format.

    Returns:
        Tuple of (artist, title). Artist may be empty.
    """
    line = line.strip()
    if not line:
        return "", ""
    if " - " in line:
        artist, title = line.split(" - ", 1)
        return " ".join(artist.split()), " ".join(title.split())
    return "", " ".join(line.split())


def remove_brackets(title: str) -> str:
    """Remove parenthesized and bracketed content from a title."""
    clean = re.sub(r"\([^)]*\)", "", title).strip()
    clean = re.sub(r"\[[^\]]*\]", "", clean).strip()
    return clean


def remove_feat(title: str) -> str | None:
    """Remove feat./ft. patterns from a title.

    Returns:
        Cleaned title, or None if no feat. pattern was found or
        the result is unchanged.
    """
    if not re.search(r"feat\.?|ft\.?", title, re.IGNORECASE):
        return None
    result = re.sub(
        r"[\(\[]?\s*(?:feat|ft)\.?\s*[^\)\]]*[\)\]]?", "",
        title, flags=re.IGNORECASE,
    ).strip()
    return result if result and result != title else None


def build_search_queries(
    artist: str,
    title: str,
    channel: str = "",
) -> list[str]:
    """Generate multiple search query variations for better matching.

    Produces queries in order of specificity: exact structured search,
    free-text search, title-only, channel fallback, bracket-removed,
    and feat.-removed variations.

    Args:
        artist: Artist name (may be empty).
        title: Song title.
        channel: YouTube channel name (optional, used as artist fallback).

    Returns:
        List of Spotify search query strings.
    """
    queries: list[str] = []

    # Exact structured search
    if artist and title:
        queries.append(f"track:{title} artist:{artist}")
        queries.append(f"{artist} {title}")
    if title:
        queries.append(f"track:{title}")

    # Channel name as fallback artist (YouTube)
    if channel and not artist:
        clean_channel = re.sub(
            r"\s*[-\u2013]?\s*(Topic|VEVO|Official).*$", "",
            channel, flags=re.IGNORECASE,
        ).strip()
        if clean_channel:
            queries.append(f"track:{title} artist:{clean_channel}")
            queries.append(f"{clean_channel} {title}")

    # Remove brackets/parentheses
    clean_title = remove_brackets(title)
    if clean_title and clean_title != title:
        if artist:
            queries.append(f"track:{clean_title} artist:{artist}")
        queries.append(
            f"{artist} {clean_title}" if artist else f"track:{clean_title}"
        )

    # Remove feat./ft.
    no_feat = remove_feat(title)
    if no_feat and no_feat != clean_title:
        if artist:
            queries.append(f"track:{no_feat} artist:{artist}")
        queries.append(
            f"{artist} {no_feat}" if artist else f"track:{no_feat}"
        )

    return queries


def search_with_fallback(
    client: SpotifyClient,
    artist: str,
    title: str,
    channel: str = "",
) -> str | None:
    """Try multiple search queries until a match is found.

    Args:
        client: Authenticated SpotifyClient instance.
        artist: Artist name.
        title: Song title.
        channel: YouTube channel name (optional).

    Returns:
        Spotify track ID or None if no match found.
    """
    for query in build_search_queries(artist, title, channel):
        track_id = client.search(query)
        if track_id:
            return track_id
        sleep(0.05)
    return None
