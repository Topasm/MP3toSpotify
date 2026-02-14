# Documentation and Branding
- [x] Documentation Updates
  - [x] Create `task.md`
  - [x] Fix `README.md` corruption in "Compare Mode" section
  - [x] Update README with screenshots and new sections
- [x] Branding Updates
  - [x] Generate new `icon.png` (MP3 -> Spotify theme)
  - [x] Update `package.json` to use `.png` for Windows icon
  - [x] Update `main.js` to set window icon

# Duplicate Remover Feature
- [x] Backend Implementation
    - [x] Create `remove_duplicates.py` script
    - [x] Implement `remove_duplicates` and `get_playlist_tracks_with_positions` in `SpotifyClient`
- [x] Frontend Implementation
    - [x] Add "Remove Duplicates" button to `index.html` (Playlist tab)
    - [x] Add IPC handler in `main.js`
    - [x] Add bridge in `preload.js`
    - [x] Implement button logic in `renderer/app.js`
- [ ] Verification
    - [ ] Test with a playlist containing duplicates
