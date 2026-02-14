# MP3toSpotify

[![Build & Release](https://github.com/Topasm/MP3toSpotify/actions/workflows/release.yml/badge.svg)](https://github.com/Topasm/MP3toSpotify/actions/workflows/release.yml)

> **🌐 Language / 언어:** **English** · [한국어](README.ko.md)

Match your local music library **or YouTube playlists** to Spotify and automatically create playlists.  
Available as a **standalone desktop app** (Windows / macOS / Linux) and a **CLI tool**.

![MP3toSpotify GUI](./screenshot.png)

Scans audio files, reads metadata (title & artist), searches Spotify, and adds matched songs to a playlist. Also imports YouTube playlists via yt-dlp. Unmatched songs are saved for retry with advanced search strategies.

**Key Features:**
- 🖥️ Modern desktop GUI (Electron) with real-time progress
- 🎵 Recursive local music directory scanning via TinyTag
- ▶️ YouTube playlist import (via yt-dlp — no download required)
- 🔍 Smart Spotify search with multiple fallback strategies
- 🔄 Retry failed matches with bracket/feat. removal, title-only search
- ☑️ Checkbox-based track selection — choose which songs to add to your playlist
- 📋 Browse & select existing Spotify playlists — no need to manually copy playlist IDs
- 🔀 Automatic duplicate detection (by track ID and display name)
- 🌏 Automatic encoding recovery (CJK mojibake fix via chardet)
- 🔐 Secure credential management via environment variables
- 📦 Standalone builds — no Python installation required

**Supported Audio Formats:**
MP3, FLAC, OGG, Opus, WMA, WAV, M4A, AAC, AIFF, DSF, WavPack

> Originally forked from [BoscoDomingo/SpotifyMatcher](https://github.com/BoscoDomingo/SpotifyMatcher). Licensed under GPLv3.

---

## Download

**➡️ [Latest Release](https://github.com/Topasm/MP3toSpotify/releases/latest)**

| Platform | File | Notes |
|----------|------|-------|
| **Windows** | `MP3toSpotify-Setup-*.exe` | Installer (NSIS) |
| **Windows** | `MP3toSpotify-*.exe` | Portable (no install) |
| **macOS** | `MP3toSpotify-*.dmg` | Drag to Applications |
| **Linux** | `MP3toSpotify-*.AppImage` | `chmod +x` then run |

> **No Python or Node.js installation required** — everything is bundled.

---

## Setup (from source)

> Only needed if you want to run from source instead of using the prebuilt downloads above.

### 1. Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for GUI only)
- A [Spotify Developer](https://developer.spotify.com/dashboard) app

### 2. Create a Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click **Create an App**
3. Set **Redirect URI** to `http://127.0.0.1:8080`
4. Copy your **Client ID** and **Client Secret**

### 3. Install

```bash
git clone https://github.com/Topasm/MP3toSpotify.git
cd MP3toSpotify

# Python dependencies
pip install -r backend/requirements.txt

# Electron GUI (optional)
npm install
```

### 4. Configure Credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your Spotify credentials:

```
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
```

> **Note:** The GUI app has a Settings tab where you can also enter credentials directly.

### 5. Build Standalone Executable (optional)

```bash
cd backend
pip install pyinstaller
pyinstaller mp3tospotify.spec
# Output: backend/dist/mp3tospotify[.exe]
```

---

## Usage

### 🖥️ Desktop GUI (Recommended)

```bash
npm start
```

The app provides four tabs:

| Tab | Description |
|-----|-------------|
| **Scan & Match** | Select a music folder, scan files, match to Spotify |
| **Retry Failed** | Retry unmatched songs with advanced search strategies |
| **YouTube Import** | Import a YouTube playlist URL into Spotify |
| **Settings** | Enter Spotify credentials (saved locally) |

**Workflow:**
1. Enter your Spotify credentials in the **Settings** tab
2. Choose a source (local folder, failed matches file, or YouTube URL)
3. Optionally click **📋 Browse** to select an existing Spotify playlist
4. Click **Start** — watch real-time progress as songs are matched
5. After scanning, **review results** with ✓/✗ indicators
6. Use **checkboxes** to select/deselect which matched songs to add
7. Click **"Add Selected to Playlist"** to add only the songs you want

**Additional features:**
- Filter results — view All, Matched only, or Failed only
- Select All / Deselect All toggle
- Duplicate tracks are automatically detected and removed

### ⌨️ Command Line

#### Scan & Match Local Files

```bash
cd backend
python main.py <username> [options]
```

| Option | Description |
|---|---|
| `-d, --music-dir` | Path to your music directory |
| `-p, --playlist-id` | Add to an existing playlist (optional) |
| `-o, --output` | Failed matches output file (default: `failed_matches.txt`) |

**Examples:**

```bash
python main.py myusername -d "C:/Music"
python main.py myusername -d "C:/Music" -p 37i9dQZF1DXcBWIGoYBM5M
```

#### Retry Failed Matches

```bash
cd backend
python retry_failed.py <username> [options]
```

| Option | Description |
|---|---|
| `-i, --input` | Failed matches file to retry (default: `failed_matches.txt`) |
| `-p, --playlist-id` | Add to an existing playlist (optional) |
| `-o, --output` | Still-failed output file (default: `still_failed.txt`) |

**Examples:**

```bash
python retry_failed.py myusername
python retry_failed.py myusername -i my_failures.txt -o final_failures.txt
```

#### YouTube Playlist Import

```bash
cd backend
python youtube_import.py <username> -u <youtube_url> [options]
```

| Option | Description |
|---|---|
| `-u, --url` | YouTube playlist or video URL **(required)** |
| `-p, --playlist-id` | Add to an existing Spotify playlist (optional) |
| `-o, --output` | Unmatched songs output file (default: `yt_failed_matches.txt`) |

**Examples:**

```bash
python youtube_import.py myusername -u "https://www.youtube.com/playlist?list=PLxxx"
python youtube_import.py myusername -u "https://youtu.be/dQw4w9WgXcQ" -p 37i9dQZF1DXcBWIGoYBM5M
```

### Find Your Spotify Username

Your username can be found at [Spotify Account Overview](https://www.spotify.com/account/overview/) or by copying your **Spotify URI** (right-click your profile → Share → Copy Spotify URI).

---

## Project Structure

```
MP3toSpotify/
├── .github/workflows/
│   └── release.yml            # CI: auto-build Win/Mac/Linux on tag push
├── electron/                  # Electron desktop app
│   ├── main.js                # Main process (window, IPC, subprocess)
│   ├── preload.js             # Secure IPC bridge
│   └── renderer/
│       ├── index.html         # UI layout (4 tabs + results)
│       ├── styles.css         # Dark theme styling
│       └── app.js             # Frontend logic (checkboxes, dedup)
├── backend/                   # Python core
│   ├── cli.py                 # Unified entry point (PyInstaller)
│   ├── main.py                # Scan local files → Spotify match
│   ├── retry_failed.py        # Retry with advanced search strategies
│   ├── youtube_import.py      # YouTube playlist → Spotify import
│   ├── spotify_client.py      # SpotifyClient class (API wrapper)
│   ├── encoding_utils.py      # Automatic mojibake recovery (chardet)
│   ├── gui_utils.py           # Shared GUI output helper (emit)
│   ├── search_strategies.py   # Shared search logic (fallback queries)
│   ├── mp3tospotify.spec      # PyInstaller build spec
│   └── requirements.txt       # Python dependencies
├── .env.example               # Credential template
├── package.json               # Electron config & scripts
├── pyproject.toml
├── LICENSE                    # GPLv3
└── README.md
```

---

## How Encoding Recovery Works

Many MP3 files (especially Korean, Japanese, Chinese) have ID3v1 tags encoded in legacy formats (CP949, Shift-JIS, etc.). When these are read as Latin-1 (the ID3v1 default), the text becomes garbled (mojibake).

**MP3toSpotify** automatically detects and fixes this:

1. Re-encode the garbled text back to raw bytes using Latin-1
2. Detect the actual encoding using `chardet`
3. Decode with the correct encoding

```
Before: °Å¹Ì - Ä£±¸¶óµµ µÉ °É ±×·¨¾î
After:  거미 - 친구라도 될 걸 그랬어
```

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
