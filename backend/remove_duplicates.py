# -*- coding: utf-8 -*-
"""
remove_duplicates.py - Identify and remove duplicate tracks from a playlist.

Safety features:
- Creates a timestamped backup JSON before removing any tracks.
- Supports --scan-only mode to preview duplicates without removing.
- All operations are logged to the console/GUI.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

from gui_utils import emit
from spotify_client import SpotifyClient

# Backup directory: save in user's Documents/MP3toSpotify/backups/
# This ensures backups are user-visible and survive app updates
BACKUP_DIR = os.path.join(os.path.expanduser("~"), "Documents", "MP3toSpotify", "backups")


def _ensure_backup_dir():
    """Create backups directory if it doesn't exist."""
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _save_backup(playlist_id: str, playlist_name: str, removed_tracks: list[dict]) -> str:
    """Save removed tracks to a timestamped JSON backup file.
    
    Returns the backup file path.
    """
    _ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in playlist_name)
    filename = f"backup_{safe_name}_{timestamp}.json"
    filepath = os.path.join(BACKUP_DIR, filename)

    backup_data = {
        "playlist_id": playlist_id,
        "playlist_name": playlist_name,
        "timestamp": datetime.now().isoformat(),
        "removed_count": len(removed_tracks),
        "tracks": removed_tracks,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)

    return filepath


def _remove_duplicates(client: SpotifyClient, playlist_id: str, gui: bool, scan_only: bool = False):
    """Find and remove duplicate tracks, with logging and backup."""
    if gui:
        emit(True, {"type": "log", "text": "Fetching playlist tracks..."})
    else:
        print("Fetching playlist tracks...")

    # Fetch all tracks
    tracks = client.get_playlist_tracks_with_positions(playlist_id)

    # Get playlist name for backup file naming
    try:
        playlist_info = client.sp.playlist(playlist_id, fields="name")
        playlist_name = playlist_info.get("name", "unknown")
    except Exception:
        playlist_name = "unknown"

    # Identify duplicates: map track_id -> list of occurrences
    track_map = defaultdict(list)
    for t in tracks:
        track_map[t["id"]].append(t)

    duplicates_to_remove = []
    duplicate_details = []  # For backup/logging

    for tid, occurrences in track_map.items():
        if len(occurrences) > 1:
            # Keep the first one (lowest position), remove the rest
            occurrences.sort(key=lambda x: x["pos"])

            for dup in occurrences[1:]:
                duplicates_to_remove.append({
                    "uri": dup["uri"],
                    "positions": [dup["pos"]]
                })
                duplicate_details.append({
                    "id": dup["id"],
                    "uri": dup["uri"],
                    "name": dup["name"],
                    "artist": dup["artist"],
                    "position": dup["pos"],
                    "total_occurrences": len(occurrences),
                })

    count = len(duplicates_to_remove)

    if count == 0:
        if gui:
            emit(True, {"type": "success", "text": "No duplicates found.", "count": 0})
        else:
            print("No duplicates found.")
        return

    # If scan-only mode, output the duplicate list and stop
    if scan_only:
        if gui:
            emit(True, {
                "type": "duplicates_found",
                "count": count,
                "tracks": duplicate_details,
            })
        else:
            print(f"Found {count} duplicates:")
            for d in duplicate_details:
                print(f"  - {d['name']} by {d['artist']} (appears {d['total_occurrences']} times)")
        return

    # Save backup BEFORE removing
    if gui:
        emit(True, {"type": "log", "text": f"Found {count} duplicates. Saving backup..."})
    else:
        print(f"Found {count} duplicates. Saving backup...")

    backup_path = _save_backup(playlist_id, playlist_name, duplicate_details)

    if gui:
        emit(True, {"type": "log", "text": f"Backup saved. Removing {count} duplicates..."})
    else:
        print(f"Backup saved to: {backup_path}")
        print(f"Removing {count} duplicates...")

    # Remove duplicates
    client.remove_tracks(playlist_id, duplicates_to_remove)

    if gui:
        emit(True, {
            "type": "success",
            "text": f"Removed {count} duplicates. Backup saved.",
            "count": count,
            "backup": backup_path,
        })
    else:
        print(f"Successfully removed {count} duplicates.")
        print(f"Backup file: {backup_path}")



def main():
    parser = argparse.ArgumentParser(description="Remove duplicates from a Spotify playlist.")
    parser.add_argument("username", help="Spotify username")
    parser.add_argument("-p", "--playlist-id", required=True, help="Spotify Playlist ID")
    parser.add_argument("--gui", action="store_true", help="Enable GUI JSON output")
    parser.add_argument("--scan-only", action="store_true", help="Only scan for duplicates, don't remove")
    args = parser.parse_args()

    gui = args.gui
    client = SpotifyClient(args.username)
    _remove_duplicates(client, args.playlist_id, gui, scan_only=args.scan_only)


if __name__ == "__main__":
    # Force UTF-8 for Windows console
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
