# MP3toSpotify

[![Build & Release](https://github.com/Topasm/MP3toSpotify/actions/workflows/release.yml/badge.svg)](https://github.com/Topasm/MP3toSpotify/actions/workflows/release.yml)

> **🌐 Language / 언어:** [English](README.md) · **한국어**

**최고의 음악 마이그레이션 도구 (The Ultimate Music Migration Tool)**

**로컬 음악 라이브러리**와 **YouTube 플레이리스트**를 Spotify와 손쉽게 동기화하세요.  
**Compare Mode(비교 모드)**를 사용하여 플레이리스트에서 누락된 곡을 찾아 즉시 채울 수 있습니다.  
모던한 **데스크톱 앱** (Windows / macOS / Linux) 및 **CLI**로 제공됩니다.

![MP3toSpotify Banner](docs/banner.png)


**주요 기능:**
- 🖥️ Electron 기반 데스크톱 GUI — 실시간 진행 상황 표시
- 🎵 로컬 음악 디렉토리 재귀 스캔 (TinyTag)
- ▶️ YouTube 플레이리스트 가져오기 (yt-dlp — 다운로드 불필요)
- 🔍 다중 검색 전략으로 Spotify 매칭 (괄호 제거, feat. 제거 등)
- ☑️ 체크박스 기반 트랙 선택 — 원하는 곡만 골라서 플레이리스트에 추가
- 📋 기존 Spotify 플레이리스트 탐색 및 선택 — 플레이리스트 ID를 직접 복사할 필요 없음
- 🔀 중복 트랙 자동 감지 및 제거
- 🌏 인코딩 깨짐 자동 복구 — `chardet`를 이용해 CP949, Shift-JIS 등 레거시 인코딩 자동 감지
- 📦 독립 실행형 빌드 — Python 설치 없이 바로 사용

**지원 오디오 포맷:** MP3, FLAC, OGG, Opus, WMA, WAV, M4A, AAC, AIFF, DSF, WavPack

---

## 다운로드

**➡️ [최신 릴리즈 다운로드](https://github.com/Topasm/MP3toSpotify/releases/latest)**

| 플랫폼 | 파일 | 비고 |
|--------|------|------|
| **Windows** | `MP3toSpotify-*.exe` | 포터블 (설치 불필요) |
| **macOS** | `MP3toSpotify-*.dmg` | Applications로 드래그 |
| **Linux** | `MP3toSpotify-*.AppImage` | `chmod +x` 후 실행 |

> **Python이나 Node.js 설치 불필요** — 모든 것이 내장되어 있습니다.

---

## 사용 방법

### 1. Spotify API 크리덴셜 발급

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)에서 앱 생성
2. **Create an App** 클릭
3. **Redirect URI**를 `http://127.0.0.1:8080`으로 설정
4. **Client ID**와 **Client Secret**을 복사

### 2. 앱 실행 및 설정

1. 앱을 다운로드하고 실행
2. **Settings** 탭으로 이동
3. **Client ID**, **Client Secret**, **Spotify 사용자명** 입력
4. **Save Settings** 클릭

### 3. 음악 매칭

![Import Tab](docs/import_tab.png)

| 섹션 (Section) | 기능 |
|----------------|------|
| **Local Music** | 로컬 음악 폴더 선택 → 파일 스캔 → Spotify 매칭 |
| **YouTube Playlist** | YouTube 플레이리스트 URL 입력 → Spotify 매칭 |
| **Retry Failed** | 매칭 실패 곡을 더 스마트한 검색 전략으로 재시도 |

**사용 흐름:**
1. **Import** 탭으로 이동합니다.
2. 소스를 선택하고 "Import" 또는 "Browse"를 클릭합니다.
   - **Local Music**: 폴더 선택
   - **YouTube**: URL 입력
   - **Retry**: 실패 파일 선택
3. 대시보드에서 실시간 진행 상황을 확인합니다 (Scanned / Matched / Failed).
4. 완료되면 녹색 **"Review Songs"** 버튼을 클릭합니다.

![Import Success](docs/imported.png)

5. **체크박스**로 추가할 곡을 선택합니다.
6. **"Add to Playlist"**를 클릭합니다.
7. **새 플레이리스트 생성** 또는 기존 플레이리스트 선택이 가능합니다.

![Playlist Tab](docs/playlist_tab.png)

**팁:**
- 결과 필터링 — 전체, 매칭, 실패 보기
- 전체 선택 / 전체 해제 토글
- 중복 트랙은 자동으로 건너뜀

### 4. 음악 비교 모드 (Compare Mode)

로컬 음악 파일과 기존 Spotify 플레이리스트를 비교하여 누락된 트랙을 쉽게 추가할 수 있습니다.

![Compare Mode](docs/compare_mode.png)

1. **Playlist** 탭으로 이동합니다.
2. 드롭다운에서 대상 플레이리스트를 선택합니다.
3. **Compare** 버튼을 클릭합니다.
4. 결과를 확인합니다:
   - 이미 플레이리스트에 있는 곡은 **"In Playlist"**로 표시되며 자동으로 선택 해제됩니다.
   - 누락된 곡은 **"Missing"**으로 표시되며 선택된 상태로 유지됩니다.
5. **"Show Missing"**을 클릭하여 누락된 곡만 필터링할 수 있습니다.
6. **"Add to Playlist"**를 클릭하여 새로운 곡만 추가합니다.

---

## CLI 사용법

커맨드 라인 사용 시 (Python 필요 — 아래 [개발자 설정](#개발자-설정) 참조):

```bash
# 로컬 파일 스캔
python backend/main.py <사용자명> -d "C:/Music"

# 실패 매칭 재시도
python backend/retry_failed.py <사용자명>

# YouTube 플레이리스트 가져오기
python backend/youtube_import.py <사용자명> -u "https://www.youtube.com/playlist?list=PLxxx"
```

<details>
<summary>CLI 옵션 상세</summary>

**로컬 파일 스캔:**

| 옵션 | 설명 |
|------|------|
| `-d, --music-dir` | 음악 디렉토리 경로 |
| `-p, --playlist-id` | 기존 플레이리스트에 추가 (선택) |
| `-o, --output` | 실패 매칭 출력 파일 (기본: `failed_matches.txt`) |

**실패 매칭 재시도:**

| 옵션 | 설명 |
|------|------|
| `-i, --input` | 재시도할 실패 매칭 파일 (기본: `failed_matches.txt`) |
| `-p, --playlist-id` | 기존 플레이리스트에 추가 (선택) |
| `-o, --output` | 여전히 실패한 출력 파일 (기본: `still_failed.txt`) |

**YouTube 가져오기:**

| 옵션 | 설명 |
|------|------|
| `-u, --url` | YouTube 플레이리스트 또는 비디오 URL **(필수)** |
| `-p, --playlist-id` | 기존 Spotify 플레이리스트에 추가 (선택) |
| `-o, --output` | 매칭 실패 곡 출력 파일 (기본: `yt_failed_matches.txt`) |

</details>

### Spotify 사용자명 찾기

[Spotify 계정 개요](https://www.spotify.com/account/overview/)에서 확인하거나, 프로필 우클릭 → 공유 → Spotify URI 복사.

---

## 개발자 설정

> 소스에서 직접 실행하거나 기여하려는 경우에만 필요합니다. 일반 사용자는 위의 [다운로드](#다운로드)를 이용하세요.

### 사전 요구사항

- **Python 3.10+**
- **Node.js 18+** (GUI만 해당)

### 설치

```bash
git clone https://github.com/Topasm/MP3toSpotify.git
cd MP3toSpotify

# Python 의존성
pip install -r backend/requirements.txt

# Electron GUI (선택)
npm install
```

### 크리덴셜 설정

```bash
cp .env.example .env
```

`.env` 파일 편집:

```
SPOTIPY_CLIENT_ID=여기에_클라이언트_ID_입력
SPOTIPY_CLIENT_SECRET=여기에_클라이언트_시크릿_입력
```

> GUI 앱의 Settings 탭에서도 직접 입력할 수 있습니다.

### 실행

```bash
npm start           # GUI 앱
cd backend && python main.py <사용자명> -d "C:/Music"  # CLI
```

### 독립 실행 파일 빌드

```bash
cd backend
pip install pyinstaller
pyinstaller mp3tospotify.spec
# 출력: backend/dist/mp3tospotify[.exe]
```

### 프로젝트 구조

```
MP3toSpotify/
├── .github/workflows/
│   └── release.yml            # CI: 태그 푸시 시 Win/Mac/Linux 자동 빌드
├── electron/                  # Electron 데스크톱 앱
│   ├── main.js                # 메인 프로세스 (윈도우, IPC, 서브프로세스)
│   ├── preload.js             # 보안 IPC 브리지
│   └── renderer/
│       ├── index.html         # UI 레이아웃
│       ├── styles.css         # 다크 테마 스타일링
│       └── app.js             # 프론트엔드 로직
├── backend/                   # Python 코어
│   ├── cli.py                 # 통합 진입점 (PyInstaller)
│   ├── main.py                # 로컬 파일 스캔 → Spotify 매칭
│   ├── retry_failed.py        # 고급 검색 전략으로 재시도
│   ├── youtube_import.py      # YouTube → Spotify 가져오기
│   ├── spotify_client.py      # SpotifyClient (API 래퍼)
│   ├── encoding_utils.py      # 인코딩 깨짐 복구 (chardet)
│   ├── gui_utils.py           # GUI 출력 헬퍼
│   ├── search_strategies.py   # 검색 폴백 로직
│   ├── mp3tospotify.spec      # PyInstaller 빌드 스펙
│   └── requirements.txt       # Python 의존성
├── .env.example               # 크리덴셜 템플릿
├── package.json
└── LICENSE                    # GPLv3
```



---

> 원래 [BoscoDomingo/SpotifyMatcher](https://github.com/BoscoDomingo/SpotifyMatcher)에서 포크됨. [GPLv3](LICENSE) 라이선스.
