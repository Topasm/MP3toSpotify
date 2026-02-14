# MP3toSpotify

Match your local music library to Spotify and automatically create playlists.

Scans audio files, reads metadata (title & artist), searches Spotify, and adds matched songs to a playlist. Unmatched songs are saved for retry with advanced search strategies.

**Key Features:**
- 🎵 Recursive local music directory scanning via TinyTag
- 🔍 Smart Spotify search with multiple fallback strategies
- 🔄 Retry failed matches with bracket/feat. removal, title-only search
- 🌏 Automatic encoding recovery (CJK mojibake fix via chardet)
- 🔐 Secure credential management via environment variables

> Originally forked from [BoscoDomingo/SpotifyMatcher](https://github.com/BoscoDomingo/SpotifyMatcher). Licensed under GPLv3.

---

## Setup

### 1. Prerequisites

- Python 3.10+
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
pip install -r requirements.txt
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

### 5. Find Your Spotify Username

Your username can be found at [Spotify Account Overview](https://www.spotify.com/account/overview/) or by copying your **Spotify URI** (right-click your profile → Share → Copy Spotify URI).

---

## Usage

### Scan & Match Local Files

```bash
python main.py <username> [options]
```

| Option | Description |
|---|---|
| `-d, --music-dir` | Path to your music directory |
| `-p, --playlist-id` | Add to an existing playlist (optional) |
| `-o, --output` | Failed matches output file (default: `failed_matches.txt`) |

**Examples:**

```bash
# Interactive: will prompt for music directory
python main.py myusername

# Specify directory and playlist
python main.py myusername -d "C:/Music" -p 37i9dQZF1DXcBWIGoYBM5M

# Custom output file
python main.py myusername -d "/home/user/music" -o my_failures.txt
```

### Retry Failed Matches

```bash
python retry_failed.py <username> [options]
```

| Option | Description |
|---|---|
| `-i, --input` | Failed matches file to retry (default: `failed_matches.txt`) |
| `-p, --playlist-id` | Add to an existing playlist (optional) |
| `-o, --output` | Still-failed output file (default: `still_failed.txt`) |

**Examples:**

```bash
# Retry with default files
python retry_failed.py myusername

# Custom input/output
python retry_failed.py myusername -i my_failures.txt -o final_failures.txt
```

---

## Project Structure

```
MP3toSpotify/
├── main.py               # Scan local files → Spotify match
├── retry_failed.py       # Retry with advanced search strategies
├── spotify_client.py     # SpotifyClient class (API wrapper)
├── encoding_utils.py     # Automatic mojibake recovery (chardet)
├── .env.example          # Credential template
├── requirements.txt
├── pyproject.toml
├── LICENSE               # GPLv3
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

로컬 음악 파일을 Spotify에서 자동으로 매칭하여 플레이리스트를 생성합니다.

### 주요 기능

- 🎵 로컬 음악 디렉토리 재귀 스캔 (TinyTag)
- 🔍 다중 검색 전략으로 Spotify 매칭 (괄호 제거, feat. 제거 등)
- 🌏 인코딩 깨짐(mojibake) 자동 복구 — `chardet`를 이용해 CP949, Shift-JIS 등 레거시 인코딩 자동 감지
- 🔐 환경변수 기반 크리덴셜 관리 (하드코딩 없음)

### 설치

```bash
git clone https://github.com/Topasm/MP3toSpotify.git
cd MP3toSpotify
pip install -r requirements.txt
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

### 사용법

**로컬 파일 스캔 및 매칭:**

```bash
python main.py <사용자명> -d "C:/Music"
```

**실패 곡 재시도:**

```bash
python retry_failed.py <사용자명>
```

### Spotify 사용자명 찾기

[Spotify 계정 개요](https://www.spotify.com/account/overview/)에서 확인하거나, 프로필 우클릭 → 공유 → Spotify URI 복사.

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
