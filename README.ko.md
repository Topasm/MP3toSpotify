# MP3toSpotify

[![Build & Release](https://github.com/Topasm/MP3toSpotify/actions/workflows/release.yml/badge.svg)](https://github.com/Topasm/MP3toSpotify/actions/workflows/release.yml)

> **🌐 Language / 언어:** [English](README.md) · **한국어**

로컬 음악 파일 또는 **YouTube 플레이리스트**를 Spotify에서 자동으로 매칭하여 플레이리스트를 생성합니다.  
**독립 실행형 데스크톱 앱** (Windows / macOS / Linux)과 **CLI 도구** 두 가지 방식으로 사용할 수 있습니다.

![MP3toSpotify GUI](./screenshot.png)

**주요 기능:**
- 🖥️ Electron 기반 데스크톱 GUI — 실시간 진행 상황 표시
- 🎵 로컬 음악 디렉토리 재귀 스캔 (TinyTag)
- ▶️ YouTube 플레이리스트 가져오기 (yt-dlp — 다운로드 불필요)
- 🔍 다중 검색 전략으로 Spotify 매칭 (괄호 제거, feat. 제거 등)
- ☑️ 체크박스 기반 트랙 선택 — 원하는 곡만 골라서 플레이리스트에 추가
- 📋 기존 Spotify 플레이리스트 탐색 및 선택 — 플레이리스트 ID를 직접 복사할 필요 없음
- 🔀 중복 트랙 자동 감지 및 제거
- 🌏 인코딩 깨짐(mojibake) 자동 복구 — `chardet`를 이용해 CP949, Shift-JIS 등 레거시 인코딩 자동 감지
- 🔐 환경변수 기반 크리덴셜 관리 (하드코딩 없음)
- 📦 독립 실행형 빌드 — Python 설치 없이 바로 사용

**지원 오디오 포맷:** MP3, FLAC, OGG, Opus, WMA, WAV, M4A, AAC, AIFF, DSF, WavPack

> 원래 [BoscoDomingo/SpotifyMatcher](https://github.com/BoscoDomingo/SpotifyMatcher)에서 포크됨. GPLv3 라이선스.

---

## 다운로드

**➡️ [최신 릴리즈 다운로드](https://github.com/Topasm/MP3toSpotify/releases/latest)**

| 플랫폼 | 파일 | 비고 |
|--------|------|------|
| **Windows** | `MP3toSpotify-Setup-*.exe` | 설치형 |
| **Windows** | `MP3toSpotify-*.exe` | 포터블 (설치 불필요) |
| **macOS** | `MP3toSpotify-*.dmg` | Applications로 드래그 |
| **Linux** | `MP3toSpotify-*.AppImage` | `chmod +x` 후 실행 |

> **Python이나 Node.js 설치 불필요** — 모든 것이 내장되어 있습니다.

---

## 소스에서 설치 (개발자용)

> 위의 빌드된 다운로드를 사용하지 않고 소스에서 직접 실행하려는 경우에만 필요합니다.

### 1. 사전 요구사항

- **Python 3.10+**
- **Node.js 18+** (GUI만 해당)
- [Spotify Developer](https://developer.spotify.com/dashboard) 앱

### 2. Spotify 앱 생성

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)로 이동
2. **Create an App** 클릭
3. **Redirect URI**를 `http://127.0.0.1:8080`으로 설정
4. **Client ID**와 **Client Secret**을 복사

### 3. 설치

```bash
git clone https://github.com/Topasm/MP3toSpotify.git
cd MP3toSpotify

# Python 의존성
pip install -r backend/requirements.txt

# Electron GUI (선택)
npm install
```

### 4. 크리덴셜 설정

```bash
cp .env.example .env
```

`.env` 파일에 크리덴셜 입력:

```
SPOTIPY_CLIENT_ID=여기에_클라이언트_ID_입력
SPOTIPY_CLIENT_SECRET=여기에_클라이언트_시크릿_입력
```

> **참고:** GUI 앱의 Settings 탭에서도 직접 입력할 수 있습니다.

### 5. 독릭 실행 파일 빌드 (선택)

```bash
cd backend
pip install pyinstaller
pyinstaller mp3tospotify.spec
# 출력: backend/dist/mp3tospotify[.exe]
```

---

## 사용법

### 🖥️ 데스크톱 GUI (권장)

```bash
npm start
```

앱은 네 개의 탭을 제공합니다:

| 탭 | 설명 |
|----|------|
| **Scan & Match** | 음악 폴더를 선택하고, 파일을 스캔하고, Spotify에서 매칭 |
| **Retry Failed** | 고급 검색 전략으로 매칭 실패 곡 재시도 |
| **YouTube Import** | YouTube 플레이리스트 URL을 Spotify로 가져오기 |
| **Settings** | Spotify 크리덴셜 입력 (로컬 저장) |

**사용 흐름:**
1. **Settings** 탭에서 Spotify 크리덴셜 입력
2. 소스 선택 (로컬 폴더, 실패 파일, 또는 YouTube URL)
3. **📋 Browse** 버튼을 클릭하여 기존 Spotify 플레이리스트 선택 (선택사항)
4. **Start** 클릭 — 실시간으로 매칭 진행 확인
5. 스캔 완료 후 ✓/✗ 결과 확인
6. **체크박스**로 원하는 곡 선택/해제
7. **"Add Selected to Playlist"** 클릭하여 선택한 곡만 추가

**추가 기능:**
- 결과 필터링 — 전체, 매칭, 실패 보기
- 전체 선택 / 전체 해제 토글
- 중복 트랙 자동 감지 및 제거

### ⌨️ 커맨드 라인

#### 로컬 파일 스캔 및 매칭

```bash
cd backend
python main.py <사용자명> [옵션]
```

| 옵션 | 설명 |
|------|------|
| `-d, --music-dir` | 음악 디렉토리 경로 |
| `-p, --playlist-id` | 기존 플레이리스트에 추가 (선택) |
| `-o, --output` | 실패 매칭 출력 파일 (기본: `failed_matches.txt`) |

```bash
python main.py myusername -d "C:/Music"
python main.py myusername -d "C:/Music" -p 37i9dQZF1DXcBWIGoYBM5M
```

#### 실패 매칭 재시도

```bash
cd backend
python retry_failed.py <사용자명> [옵션]
```

| 옵션 | 설명 |
|------|------|
| `-i, --input` | 재시도할 실패 매칭 파일 (기본: `failed_matches.txt`) |
| `-p, --playlist-id` | 기존 플레이리스트에 추가 (선택) |
| `-o, --output` | 여전히 실패한 출력 파일 (기본: `still_failed.txt`) |

```bash
python retry_failed.py myusername
python retry_failed.py myusername -i my_failures.txt -o final_failures.txt
```

#### YouTube 플레이리스트 가져오기

```bash
cd backend
python youtube_import.py <사용자명> -u <youtube_url> [옵션]
```

| 옵션 | 설명 |
|------|------|
| `-u, --url` | YouTube 플레이리스트 또는 비디오 URL **(필수)** |
| `-p, --playlist-id` | 기존 Spotify 플레이리스트에 추가 (선택) |
| `-o, --output` | 매칭 실패 곡 출력 파일 (기본: `yt_failed_matches.txt`) |

```bash
python youtube_import.py myusername -u "https://www.youtube.com/playlist?list=PLxxx"
python youtube_import.py myusername -u "https://youtu.be/dQw4w9WgXcQ" -p 37i9dQZF1DXcBWIGoYBM5M
```

### Spotify 사용자명 찾기

[Spotify 계정 개요](https://www.spotify.com/account/overview/)에서 확인하거나, 프로필 우클릭 → 공유 → Spotify URI 복사.

---

## 인코딩 복구 원리

많은 MP3 파일 (특히 한국어, 일본어, 중국어)이 레거시 형식 (CP949, Shift-JIS 등)으로 인코딩된 ID3v1 태그를 가지고 있습니다. 이를 Latin-1 (ID3v1 기본값)으로 읽으면 텍스트가 깨집니다 (mojibake).

**MP3toSpotify**는 이를 자동으로 감지하고 수정합니다:

1. 깨진 텍스트를 Latin-1으로 원시 바이트로 다시 인코딩
2. `chardet`를 사용하여 실제 인코딩 감지
3. 올바른 인코딩으로 디코딩

```
수정 전: °Å¹Ì - Ä£±¸¶óµµ µÉ °É ±×·¨¾î
수정 후: 거미 - 친구라도 될 걸 그랬어
```

---

## 프로젝트 구조

```
MP3toSpotify/
├── .github/workflows/
│   └── release.yml            # CI: 태그 푸시 시 Win/Mac/Linux 자동 빌드
├── electron/                  # Electron 데스크톱 앱
│   ├── main.js                # 메인 프로세스 (윈도우, IPC, 서브프로세스)
│   ├── preload.js             # 보안 IPC 브리지
│   └── renderer/
│       ├── index.html         # UI 레이아웃 (4탭 + 결과)
│       ├── styles.css         # 다크 테마 스타일링
│       └── app.js             # 프론트엔드 로직 (체크박스, 중복제거)
├── backend/                   # Python 코어
│   ├── cli.py                 # 통합 진입점 (PyInstaller)
│   ├── main.py                # 로컬 파일 스캔 → Spotify 매칭
│   ├── retry_failed.py        # 고급 검색 전략으로 재시도
│   ├── youtube_import.py      # YouTube 플레이리스트 → Spotify 가져오기
│   ├── spotify_client.py      # SpotifyClient 클래스 (API 래퍼)
│   ├── encoding_utils.py      # 자동 인코딩 깨짐 복구 (chardet)
│   ├── gui_utils.py           # 공유 GUI 출력 헬퍼 (emit)
│   ├── search_strategies.py   # 공유 검색 로직 (폴백 쿼리)
│   ├── mp3tospotify.spec      # PyInstaller 빌드 스펙
│   └── requirements.txt       # Python 의존성
├── .env.example               # 크리덴셜 템플릿
├── package.json               # Electron 설정 & 스크립트
├── pyproject.toml
├── LICENSE                    # GPLv3
└── README.md
```

---

## 라이선스

이 프로젝트는 [GNU General Public License v3.0](LICENSE) 하에 라이선스됩니다.
