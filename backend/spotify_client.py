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

_SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private user-library-modify"
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
        # 1. Try exact search
        tid = self._do_search(query, limit)
        if tid:
            return tid

        # 2. Try cleaned search (remove parens/brackets)
        cleaned_query = self._clean_query(query)
        if cleaned_query != query:
            return self._do_search(cleaned_query, limit)
        
        return None

    def _do_search(self, query: str, limit: int) -> str | None:
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

    def search_candidates(self, query: str, limit: int = 5) -> list[dict]:
        """Search for a track and return a list of candidates.

        Args:
            query: Spotify search query string.
            limit: Maximum number of results.

        Returns:
            List of track dicts: {id, name, artist, album, url, image}
        """
        # 1. Try exact
        candidates = self._do_search_candidates(query, limit)
        if candidates:
            return candidates

        # 2. Try cleaned
        cleaned_query = self._clean_query(query)
        if cleaned_query != query:
            return self._do_search_candidates(cleaned_query, limit)
            
        return []

    def _do_search_candidates(self, query: str, limit: int) -> list[dict]:
        try:
            results = self.sp.search(query, limit=limit, type="track")
            if not results or "tracks" not in results or "items" not in results["tracks"]:
                return []
                
            items = results["tracks"]["items"]
            candidates = []
            for item in items:
                image = None
                if item["album"]["images"]:
                    image = item["album"]["images"][-1]["url"]

                candidates.append({
                    "id": item["id"],
                    "name": item["name"],
                    "artist": item["artists"][0]["name"],
                    "album": item["album"]["name"],
                    "url": item["external_urls"]["spotify"],
                    "image": image
                })
            return candidates
        except Exception:
            return []

    def _clean_query(self, query: str) -> str:
        """Remove text within parentheses or brackets."""
        import re
        # Remove (...) and [...] content
        cleaned = re.sub(r'\s*[\(\[][^)\]]*[\)\]]', '', query)
        return cleaned.strip()

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

    def get_user_playlists(self) -> list[dict]:
        """Fetch all playlists for the current user.

        Returns:
            List of dicts with 'id', 'name', 'tracks_total'.
        """
        playlists = []
        try:
            results = self.sp.current_user_playlists(limit=50)
            while results:
                for item in results["items"]:
                    if item:  # item can be None if playlist was deleted but still in cache
                        playlists.append({
                            "id": item["id"],
                            "name": item["name"],
                            "tracks_total": item["tracks"]["total"],
                        })
                if results["next"]:
                    results = self.sp.next(results)
                else:
                    results = None
        except SpotifyException as e:
            print(f"Error fetching playlists: {e}")
            return []
        
        return playlists

    def get_playlist_items(self, playlist_id: str) -> list[dict]:
        """Get all tracks in a playlist.
        
        Args:
            playlist_id: The Spotify ID of the playlist.
            
        Returns:
            List of track dicts: {id, name, artist, album}
        """
        results = []
        try:
            # Use offset based pagination similar to playlist_add_items
            offset = 0
            while True:
                response = self.sp.playlist_items(
                    playlist_id, 
                    offset=offset, 
                    # Request only necessary fields to reduce payload size
                    fields="items.track(id,name,artists,album(name)),next",
                    additional_types=("track",)
                )
                
                if not response or "items" not in response:
                    break
                
                for item in response["items"]:
                    track = item.get("track")
                    # Track can be None or sometimes local files without ID
                    if track and track.get("id"):
                        results.append({
                            "id": track["id"],
                            "name": track["name"],
                            "artist": track["artists"][0]["name"] if track["artists"] else "Unknown",
                            "album": track["album"]["name"] if track["album"] else "Unknown"
                        })
                
                if not response.get("next"):
                    break
                    
                offset += len(response["items"])
                
        except Exception:
            # Return partial results or empty list on error
            return results
            
    def get_playlist_tracks_with_positions(self, playlist_id: str) -> list[dict]:
        """Get all tracks with their positions and URIs.
        
        Needed for precise duplicate removal.
        
        Args:
            playlist_id: Playlist ID.
            
        Returns:
            List of dicts: {id, uri, pos, name, artist}
        """
        results = []
        try:
            offset = 0
            while True:
                response = self.sp.playlist_items(
                    playlist_id, 
                    offset=offset, 
                    fields="items.track(id,uri,name,artists),next",
                    additional_types=("track",)
                )
                
                if not response or "items" not in response:
                    break
                
                for i, item in enumerate(response["items"]):
                    track = item.get("track")
                    if track and track.get("id"):
                        results.append({
                            "id": track["id"],
                            "uri": track["uri"],
                            "pos": offset + i,
                            "name": track["name"],
                            "artist": track["artists"][0]["name"] if track["artists"] else "Unknown",
                        })
                
                if not response.get("next"):
                    break
                    
                offset += len(response["items"])
                
        except Exception as e:
            print(f"Error fetching tracks: {e}")
            return results
            
        return results

    def remove_tracks(self, playlist_id: str, tracks: list[dict]) -> int:
        """Remove tracks from a playlist.

        Args:
            playlist_id: Target playlist ID.
            tracks: List of dicts with {"uri": uri, "positions": [int]} 
                    or {"uri": uri} (removes all occurrences).
        
        Returns:
            Number of tracks removed (approximate based on request success).
        """
        removed = 0
        remaining = list(tracks)

        while remaining:
            batch = remaining[:_BATCH_SIZE]
            try:
                self.sp.playlist_remove_specific_occurrences_of_items(
                    playlist_id, batch
                )
                removed += len(batch)
                remaining = remaining[_BATCH_SIZE:]
            except SpotifyException as e:
                print(f"Error removing tracks: {e}")
                break

        return removed
