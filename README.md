# MP3toSpotify

[![Build & Release](https://github.com/Topasm/MP3toSpotify/actions/workflows/release.yml/badge.svg)](https://github.com/Topasm/MP3toSpotify/actions/workflows/release.yml)

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
3. Click **Start** — watch real-time progress as songs are matched
4. After scanning, **review results** with ✓/✗ indicators
5. Use **checkboxes** to select/deselect which matched songs to add
6. Click **"Add Selected to Playlist"** to add only the songs you want

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

# 한국어 안내

## MP3toSpotify

로컬 음악 파일 또는 **YouTube 플레이리스트**를 Spotify에서 자동으로 매칭하여 플레이리스트를 생성합니다.  
**독립 실행형 데스크톱 앱** (Windows / macOS / Linux)과 **CLI 도구** 두 가지 방식으로 사용할 수 있습니다.

### 다운로드

**➡️ [최신 릴리즈 다운로드](https://github.com/Topasm/MP3toSpotify/releases/latest)**

| 플랫폼 | 파일 | 비고 |
|--------|------|------|
| **Windows** | `MP3toSpotify-Setup-*.exe` | 설치형 |
| **Windows** | `MP3toSpotify-*.exe` | 포터블 (설치 불필요) |
| **macOS** | `MP3toSpotify-*.dmg` | Applications로 드래그 |
| **Linux** | `MP3toSpotify-*.AppImage` | `chmod +x` 후 실행 |

> **Python이나 Node.js 설치 불필요** — 모든 것이 내장되어 있습니다.

### 주요 기능

- 🖥️ Electron 기반 데스크톱 GUI — 실시간 진행 상황 표시
- 🎵 로컬 음악 디렉토리 재귀 스캔 (TinyTag)
- ▶️ YouTube 플레이리스트 가져오기 (yt-dlp — 다운로드 불필요)
- 🔍 다중 검색 전략으로 Spotify 매칭 (괄호 제거, feat. 제거 등)
- ☑️ 체크박스 기반 트랙 선택 — 원하는 곡만 골라서 플레이리스트에 추가
- 🔀 중복 트랙 자동 감지 및 제거
- 🌏 인코딩 깨짐(mojibake) 자동 복구 — `chardet`를 이용해 CP949, Shift-JIS 등 레거시 인코딩 자동 감지
- 🔐 환경변수 기반 크리덴셜 관리 (하드코딩 없음)
- 📦 독립 실행형 빌드 — Python 설치 없이 바로 사용

**지원 오디오 포맷:** MP3, FLAC, OGG, Opus, WMA, WAV, M4A, AAC, AIFF, DSF, WavPack

### 소스에서 설치 (개발자용)

```bash
git clone https://github.com/Topasm/MP3toSpotify.git
cd MP3toSpotify

# Python 의존성
pip install -r backend/requirements.txt

# Electron GUI (선택)
npm install
```

### 크리덴셜 설정

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)에서 앱 생성
2. **Redirect URI**를 `http://127.0.0.1:8080`으로 설정
3. **Client ID**와 **Client Secret**을 복사

```bash
cp .env.example .env
```

`.env` 파일에 크리덴셜 입력:

```
SPOTIPY_CLIENT_ID=여기에_클라이언트_ID_입력
SPOTIPY_CLIENT_SECRET=여기에_클라이언트_시크릿_입력
```

> **참고:** GUI 앱의 Settings 탭에서도 직접 입력할 수 있습니다.

### 사용법

**GUI 앱 실행:**

```bash
npm start
```

**사용 흐름:**
1. **Settings** 탭에서 Spotify 크리덴셜 입력
2. 소스 선택 (로컬 폴더, 실패 파일, 또는 YouTube URL)
3. **Start** 클릭 — 실시간으로 매칭 진행 확인
4. 스캔 완료 후 ✓/✗ 결과 확인
5. **체크박스**로 원하는 곡 선택/해제
6. **"Add Selected to Playlist"** 클릭하여 선택한 곡만 추가

**CLI — 로컬 파일 스캔 및 매칭:**

```bash
cd backend
python main.py <사용자명> -d "C:/Music"
```

**CLI — 실패 곡 재시도:**

```bash
cd backend
python retry_failed.py <사용자명>
```

**CLI — YouTube 플레이리스트 가져오기:**

```bash
cd backend
python youtube_import.py <사용자명> -u "https://www.youtube.com/playlist?list=PLxxx"
```

### Spotify 사용자명 찾기

[Spotify 계정 개요](https://www.spotify.com/account/overview/)에서 확인하거나, 프로필 우클릭 → 공유 → Spotify URI 복사.

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
