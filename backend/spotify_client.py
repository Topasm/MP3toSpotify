# -*- coding: utf-8 -*-
"""
spotify_client.py - Spotify API client wrapper for MP3toSpotify.

Encapsulates all Spotify API interactions in a single class,
eliminating global variables and manual token management.
Credentials are loaded from environment variables (SPOTIPY_CLIENT_ID,
SPOTIPY_CLIENT_SECRET) which spotipy reads natively.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from time import sleep

import spotipy
from spotipy import oauth2
from spotipy.exceptions import SpotifyException

_SCOPE = "playlist-modify-public playlist-modify-private user-library-modify"
_REDIRECT_URI = "http://127.0.0.1:8080"
_BATCH_SIZE = 100  # Spotify API limit for adding tracks per request.
_RATE_LIMIT_WAIT = 0.3  # Seconds to wait on rate-limit errors.
_MAX_RETRIES = 5  # Max retries for rate-limited batch adds.


class SpotifyClient:
    """High-level Spotify API client.

    Handles authentication, search, playlist management, and batch
    track addition. Token refresh is handled automatically by spotipy.

    Credentials are read from environment variables:
        - SPOTIPY_CLIENT_ID
        - SPOTIPY_CLIENT_SECRET

    Args:
        username: Spotify username or user URI.
    """

    def __init__(self, username: str) -> None:
        self.username = username

        client_id = os.environ.get("SPOTIPY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")

        if not client_id or not client_secret:
            print(
                "Error: Spotify credentials not found.\n"
                "Set the following environment variables:\n"
                "  SPOTIPY_CLIENT_ID=<your_client_id>\n"
                "  SPOTIPY_CLIENT_SECRET=<your_client_secret>\n\n"
                "Or copy .env.example to .env and fill in your credentials."
            )
            sys.exit(1)

        self._auth_manager = oauth2.SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=_REDIRECT_URI,
            scope=_SCOPE,
            username=username,
        )
        self.sp = spotipy.Spotify(auth_manager=self._auth_manager)

        # Warm up: verify credentials work.
        try:
            self.sp.search("test", limit=1)
        except SpotifyException as e:
            print(f"Error: Failed to authenticate with Spotify: {e}")
            sys.exit(1)

    def search(self, query: str, limit: int = 1) -> str | None:
        """Search for a track on Spotify.

        Args:
            query: Spotify search query string.
            limit: Maximum number of results to request.

        Returns:
            Track ID of the first result, or None if no match found.
        """
        try:
            results = self.sp.search(query, limit=limit)
            items = results["tracks"]["items"]
            if items:
                return items[0]["id"]
        except SpotifyException:
            return None
        except (KeyError, IndexError):
            return None
        return None

    def ensure_playlist(self, playlist_id: str = "", name: str = "MP3toSpotify") -> str:
        """Validate an existing playlist or create a new one.

        Args:
            playlist_id: Playlist ID to validate. If empty, creates a new one.
            name: Name for the new playlist (if creating).

        Returns:
            A valid playlist ID.
        """
        if playlist_id:
            try:
                self.sp.playlist(playlist_id)
                return playlist_id
            except SpotifyException:
                print(
                    f"\nPlaylist ID '{playlist_id}' not found. "
                    "Creating a new playlist..."
                )

        return self.create_playlist(name)

    def create_playlist(
        self, name: str = "MP3toSpotify", description: str = ""
    ) -> str:
        """Create a new Spotify playlist.

        Args:
            name: Playlist name.
            description: Playlist description. Auto-generated if empty.

        Returns:
            The new playlist ID.
        """
        if not description:
            date = datetime.now().strftime("%d %b %Y at %H:%M")
            description = (
                f"Playlist created by MP3toSpotify on {date}. "
                "https://github.com/Topasm/MP3toSpotify"
            )

        try:
            result = self.sp.user_playlist_create(
                self.username, name, description=description
            )
            playlist_id = result["id"]
            print(f"Created playlist: https://open.spotify.com/playlist/{playlist_id}")
            return playlist_id
        except SpotifyException as e:
            print(
                f"\nError creating playlist: {e}\n"
                "Please create one manually and provide its ID with --playlist-id."
            )
            sys.exit(1)

    def add_tracks(self, playlist_id: str, track_ids: list[str]) -> int:
        """Add tracks to a playlist in batches.

        Handles Spotify's 100-track-per-request limit and retries
        on rate-limit errors.

        Args:
            playlist_id: Target playlist ID.
            track_ids: List of track IDs to add.

        Returns:
            Number of tracks successfully added.
        """
        added = 0
        remaining = list(track_ids)

        while remaining:
            batch = remaining[:_BATCH_SIZE]
            for attempt in range(_MAX_RETRIES):
                try:
                    self.sp.playlist_add_items(playlist_id, batch)
                    added += len(batch)
                    remaining = remaining[_BATCH_SIZE:]
                    break
                except SpotifyException:
                    if attempt < _MAX_RETRIES - 1:
                        sleep(_RATE_LIMIT_WAIT * (attempt + 1))
                    else:
                        print(f"Warning: Failed to add batch after {_MAX_RETRIES} retries. Skipping.")
                        remaining = remaining[_BATCH_SIZE:]

        return added
