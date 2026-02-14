// electron/renderer/app.js - Frontend logic for MP3toSpotify GUI.

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  isRunning: false,
  scanned: 0,
  matched: 0,
  failed: 0,
  total: 0,
  // Each song: { name, status: 'matched'|'failed', trackId?, checked }
  songs: [],
  seenNames: new Set(),   // dedup by display name
  filter: "all",
  cleanup: null,           // Listener cleanup function
};

// ── Helpers ───────────────────────────────────────────────────────────────
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── DOM Elements ──────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
  // Tabs & Panels
  tabs: $$(".tab"),
  scanPanel: $("#scan-panel"),
  retryPanel: $("#retry-panel"),
  youtubePanel: $("#youtube-panel"),
  settingsPanel: $("#settings-panel"),

  // Settings
  clientId: $("#client-id"),
  clientSecret: $("#client-secret"),
  username: $("#username"),
  saveSettings: $("#save-settings"),
  settingsStatus: $("#settings-status"),

  // Scan
  musicDir: $("#music-dir"),
  btnSelectFolder: $("#btn-select-folder"),
  playlistId: $("#playlist-id"),
  btnStartScan: $("#btn-start-scan"),
  btnCancel: $("#btn-cancel"),

  // Retry
  retryInput: $("#retry-input"),
  btnSelectFile: $("#btn-select-file"),
  retryPlaylistId: $("#retry-playlist-id"),
  btnStartRetry: $("#btn-start-retry"),
  btnCancelRetry: $("#btn-cancel-retry"),

  // YouTube
  youtubeUrl: $("#youtube-url"),
  ytPlaylistId: $("#yt-playlist-id"),
  btnStartYoutube: $("#btn-start-youtube"),
  btnCancelYoutube: $("#btn-cancel-youtube"),

  // Results
  resultsSection: $("#results-section"),
  progressLabel: $("#progress-label"),
  progressPct: $("#progress-pct"),
  progressBar: $("#progress-bar"),
  statScanned: $("#stat-scanned"),
  statMatched: $("#stat-matched"),
  statFailed: $("#stat-failed"),
  statRate: $("#stat-rate"),
  songList: $("#song-list"),
  filterButtons: $$(".filter-btn"),

  // Playlist toolbar
  playlistToolbar: $("#playlist-toolbar"),
  selectAllCheckbox: $("#select-all-checkbox"),
  selectedCount: $("#selected-count"),
  btnAddToPlaylist: $("#btn-add-to-playlist"),

  // External link
  linkSpotifyDev: $("#link-spotify-dev"),
};

// ── Settings Persistence (localStorage) ───────────────────────────────────
function loadSettings() {
  els.clientId.value = localStorage.getItem("mp3ts_clientId") || "";
  els.clientSecret.value = localStorage.getItem("mp3ts_clientSecret") || "";
  els.username.value = localStorage.getItem("mp3ts_username") || "";
}

function saveSettings() {
  localStorage.setItem("mp3ts_clientId", els.clientId.value.trim());
  localStorage.setItem("mp3ts_clientSecret", els.clientSecret.value.trim());
  localStorage.setItem("mp3ts_username", els.username.value.trim());
  els.settingsStatus.textContent = "✓ Saved!";
  setTimeout(() => (els.settingsStatus.textContent = ""), 2000);
}

function getCredentials() {
  return {
    clientId: els.clientId.value.trim() || localStorage.getItem("mp3ts_clientId") || "",
    clientSecret: els.clientSecret.value.trim() || localStorage.getItem("mp3ts_clientSecret") || "",
    username: els.username.value.trim() || localStorage.getItem("mp3ts_username") || "",
  };
}

// ── Tab Switching ─────────────────────────────────────────────────────────
function switchTab(tabName) {
  els.tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));
  els.scanPanel.style.display = tabName === "scan" ? "" : "none";
  els.retryPanel.style.display = tabName === "retry" ? "" : "none";
  els.youtubePanel.style.display = tabName === "youtube" ? "" : "none";
  els.settingsPanel.style.display = tabName === "settings" ? "" : "none";
}

// ── UI Helpers ────────────────────────────────────────────────────────────
function resetStats() {
  state.scanned = 0;
  state.matched = 0;
  state.failed = 0;
  state.total = 0;
  state.songs = [];
  state.seenNames.clear();
  updateStats();
  els.songList.innerHTML = "";
  els.playlistToolbar.style.display = "none";
}

function updateStats() {
  els.statScanned.textContent = state.scanned;
  els.statMatched.textContent = state.matched;
  els.statFailed.textContent = state.failed;

  const rate = state.scanned > 0 ? ((state.matched / state.scanned) * 100).toFixed(1) : "0";
  els.statRate.textContent = `${rate}%`;

  const pct = state.total > 0 ? Math.round((state.scanned / state.total) * 100) : 0;
  els.progressPct.textContent = `${pct}%`;
  els.progressBar.style.width = `${pct}%`;
}

function updateSelectedCount() {
  const matched = state.songs.filter((s) => s.status === "matched");
  const checked = matched.filter((s) => s.checked);
  els.selectedCount.textContent = `${checked.length} / ${matched.length} selected`;
  els.selectAllCheckbox.checked = matched.length > 0 && checked.length === matched.length;
  els.selectAllCheckbox.indeterminate =
    checked.length > 0 && checked.length < matched.length;
}

function addSongToList(name, status, trackId = null) {
  // Dedup by display name (case-insensitive)
  const key = name.toLowerCase().trim();
  if (state.seenNames.has(key)) return;
  state.seenNames.add(key);

  const song = { name, status, trackId, checked: status === "matched" };
  state.songs.push(song);

  if (state.filter === "all" || state.filter === status) {
    appendSongElement(song, state.songs.length - 1);
  }
}

function appendSongElement(song, index) {
  const div = document.createElement("div");
  div.className = `song-item ${song.status}`;
  div.dataset.index = index;

  const checkbox =
    song.status === "matched"
      ? `<input type="checkbox" class="song-checkbox" data-index="${index}" ${song.checked ? "checked" : ""}>`
      : `<span class="song-checkbox-placeholder"></span>`;

  div.innerHTML = `
    ${checkbox}
    <span class="song-index">${index + 1}</span>
    <span class="song-status">${song.status === "matched" ? "✓" : "✗"}</span>
    <span class="song-name" title="${escapeHtml(song.name)}">${escapeHtml(song.name)}</span>
  `;
  els.songList.appendChild(div);
  els.songList.scrollTop = els.songList.scrollHeight;
}

function rerenderSongList() {
  els.songList.innerHTML = "";
  state.songs.forEach((song, i) => {
    if (state.filter === "all" || state.filter === song.status) {
      appendSongElement(song, i);
    }
  });
}

function filterSongs(filter) {
  state.filter = filter;
  els.filterButtons.forEach((b) => b.classList.toggle("active", b.dataset.filter === filter));
  rerenderSongList();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function setRunning(running) {
  state.isRunning = running;
  els.btnStartScan.style.display = running ? "none" : "";
  els.btnCancel.style.display = running ? "" : "none";
  els.btnStartRetry.style.display = running ? "none" : "";
  els.btnCancelRetry.style.display = running ? "" : "none";
  els.btnStartYoutube.style.display = running ? "none" : "";
  els.btnCancelYoutube.style.display = running ? "" : "none";
  els.btnStartScan.disabled = running;
  els.btnStartRetry.disabled = running;
  els.btnStartYoutube.disabled = running;
  els.resultsSection.style.display = "";
}

function showPlaylistToolbar() {
  const hasMatched = state.songs.some((s) => s.status === "matched" && s.trackId);
  if (hasMatched) {
    els.playlistToolbar.style.display = "";
    updateSelectedCount();
  }
}

function validateCredentials() {
  const creds = getCredentials();
  if (!creds.clientId || !creds.clientSecret || !creds.username) {
    alert("Please fill in your Spotify credentials in the Settings tab first.");
    switchTab("settings");
    return null;
  }
  return creds;
}

// ── Python Message Handler ────────────────────────────────────────────────
function handlePythonMessage(msg) {
  switch (msg.type) {
    case "total":
      // Pre-scan total count for accurate progress bar
      state.total = msg.count || 0;
      updateStats();
      break;

    case "progress":
      // Update progress bar without incrementing match/fail counts
      state.scanned = msg.current || state.scanned;
      if (msg.total) state.total = msg.total;
      els.progressLabel.textContent = msg.text || "Processing...";
      updateStats();
      break;

    case "match":
      state.matched++;
      addSongToList(msg.name, "matched", msg.trackId || null);
      updateStats();
      break;

    case "no_match":
      state.failed++;
      addSongToList(msg.name, "failed");
      updateStats();
      break;

    case "summary":
      state.total = msg.total || state.scanned;
      state.matched = msg.matched || state.matched;
      state.failed = msg.failed || state.failed;
      state.scanned = state.matched + state.failed;
      updateStats();
      els.progressLabel.textContent = "Complete!";
      showPlaylistToolbar();
      break;

    case "done":
      setRunning(false);
      if (msg.code === 0) {
        els.progressLabel.textContent = "✓ Complete!";
        showPlaylistToolbar();
      } else {
        els.progressLabel.textContent = `Process exited with code ${msg.code}`;
      }
      break;

    case "error":
      console.error("Python error:", msg.text);
      els.progressLabel.textContent = `Error: ${msg.text}`;
      break;

    case "log":
      console.log("Python:", msg.text);
      break;

    default:
      console.log("Unknown message:", msg);
  }
}

// ── Event Handlers ────────────────────────────────────────────────────────

// Tabs
els.tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

// Settings
els.saveSettings.addEventListener("click", saveSettings);

// External link (open in default browser)
els.linkSpotifyDev.addEventListener("click", (e) => {
  e.preventDefault();
  window.open("https://developer.spotify.com/dashboard", "_blank");
});

// Folder picker
els.btnSelectFolder.addEventListener("click", async () => {
  const folder = await window.api.selectFolder();
  if (folder) els.musicDir.value = folder;
});

// File picker
els.btnSelectFile.addEventListener("click", async () => {
  const file = await window.api.selectFile();
  if (file) els.retryInput.value = file;
});

// Start Scan
els.btnStartScan.addEventListener("click", async () => {
  const creds = validateCredentials();
  if (!creds) return;

  const musicDir = els.musicDir.value;
  if (!musicDir) {
    alert("Please select a music directory first.");
    return;
  }

  resetStats();
  setRunning(true);
  els.progressLabel.textContent = "Scanning music files...";

  if (state.cleanup) state.cleanup();
  state.cleanup = window.api.onPythonMessage(handlePythonMessage);

  await window.api.startScan({
    username: creds.username,
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    musicDir,
    playlistId: els.playlistId.value.trim(),
  });
});

// Start Retry
els.btnStartRetry.addEventListener("click", async () => {
  const creds = validateCredentials();
  if (!creds) return;

  const inputFile = els.retryInput.value;
  if (!inputFile) {
    alert("Please select a failed matches file first.");
    return;
  }

  resetStats();
  setRunning(true);
  els.progressLabel.textContent = "Retrying failed matches...";

  if (state.cleanup) state.cleanup();
  state.cleanup = window.api.onPythonMessage(handlePythonMessage);

  await window.api.startRetry({
    username: creds.username,
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    inputFile,
    playlistId: els.retryPlaylistId.value.trim(),
  });
});

// Cancel buttons
els.btnCancel.addEventListener("click", async () => {
  await window.api.cancelProcess();
  setRunning(false);
  els.progressLabel.textContent = "Cancelled.";
});

els.btnCancelRetry.addEventListener("click", async () => {
  await window.api.cancelProcess();
  setRunning(false);
  els.progressLabel.textContent = "Cancelled.";
});

// Start YouTube Import
els.btnStartYoutube.addEventListener("click", async () => {
  const creds = validateCredentials();
  if (!creds) return;

  const url = els.youtubeUrl.value.trim();
  if (!url) {
    alert("Please enter a YouTube playlist URL.");
    return;
  }

  resetStats();
  setRunning(true);
  els.progressLabel.textContent = "Fetching YouTube playlist...";

  if (state.cleanup) state.cleanup();
  state.cleanup = window.api.onPythonMessage(handlePythonMessage);

  await window.api.startYoutube({
    username: creds.username,
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    youtubeUrl: url,
    playlistId: els.ytPlaylistId.value.trim(),
  });
});

els.btnCancelYoutube.addEventListener("click", async () => {
  await window.api.cancelProcess();
  setRunning(false);
  els.progressLabel.textContent = "Cancelled.";
});

// Filters
els.filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => filterSongs(btn.dataset.filter));
});

// ── Checkbox / Playlist Toolbar ───────────────────────────────────────────

// Delegate checkbox clicks from song list
els.songList.addEventListener("change", (e) => {
  if (e.target.classList.contains("song-checkbox")) {
    const idx = parseInt(e.target.dataset.index, 10);
    if (state.songs[idx]) {
      state.songs[idx].checked = e.target.checked;
      updateSelectedCount();
    }
  }
});

// Select All / Deselect All
els.selectAllCheckbox.addEventListener("change", () => {
  const val = els.selectAllCheckbox.checked;
  state.songs.forEach((s) => {
    if (s.status === "matched") s.checked = val;
  });
  rerenderSongList();
  updateSelectedCount();
});

// Add Selected to Playlist
els.btnAddToPlaylist.addEventListener("click", async () => {
  const creds = validateCredentials();
  if (!creds) return;

  const selected = state.songs.filter((s) => s.status === "matched" && s.checked && s.trackId);
  if (selected.length === 0) {
    alert("No matched songs selected. Check the songs you want to add.");
    return;
  }

  const trackIds = selected.map((s) => s.trackId).join(",");

  // Determine which playlist ID field is relevant
  const playlistId =
    els.playlistId.value.trim() ||
    els.retryPlaylistId.value.trim() ||
    els.ytPlaylistId.value.trim() ||
    "";

  els.btnAddToPlaylist.disabled = true;
  els.btnAddToPlaylist.textContent = "Adding...";

  if (state.cleanup) state.cleanup();
  state.cleanup = window.api.onPythonMessage((msg) => {
    if (msg.type === "summary") {
      const added = msg.matched || 0;
      els.progressLabel.textContent = `✓ Added ${added} tracks to playlist!`;
    } else if (msg.type === "error") {
      els.progressLabel.textContent = `Error: ${msg.text}`;
    } else if (msg.type === "done") {
      els.btnAddToPlaylist.disabled = false;
      els.btnAddToPlaylist.innerHTML = '<span class="btn-icon">➕</span> Add Selected to Playlist';
    }
  });

  await window.api.addTracks({
    username: creds.username,
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    playlistId,
    trackIds,
  });
});

// ── Playlist Picker ──────────────────────────────────────────────────────
const playlistModal = {
  el: $("#playlist-modal"),
  list: $("#playlist-list"),
  closeBtn: $(".close-modal"),
  targetInput: null,

  open(targetInputId) {
    this.targetInput = $(`#${targetInputId}`);
    this.el.style.display = "block";
    this.loadPlaylists();
  },

  close() {
    this.el.style.display = "none";
    this.targetInput = null;
    this.list.innerHTML = '<div class="loading-spinner">Loading playlists...</div>';
  },

  async loadPlaylists() {
    const creds = validateCredentials();
    if (!creds) {
      this.close();
      return;
    }

    try {
      this.list.innerHTML = '<div class="loading-spinner">Fetching playlists from Spotify...</div>';
      const playlists = await window.api.listPlaylists({
        username: creds.username,
        clientId: creds.clientId,
        clientSecret: creds.clientSecret,
      });

      if (!playlists || playlists.length === 0) {
        this.list.innerHTML = '<div class="error-message">No playlists found.</div>';
        return;
      }

      this.render(playlists);
    } catch (err) {
      console.error(err);
      this.list.innerHTML = `<div class="error-message">Error: ${err.message || "Failed to load playlists"}</div>`;
    }
  },

  render(playlists) {
    this.list.innerHTML = "";
    playlists.forEach((p) => {
      const div = document.createElement("div");
      div.className = "playlist-item";
      div.innerHTML = `
        <div class="playlist-info">
          <span class="playlist-name">${escapeHtml(p.name)}</span>
          <span class="playlist-meta">${p.tracks_total} tracks • ID: ${p.id}</span>
        </div>
        <button class="playlist-select-btn">Select</button>
      `;
      div.addEventListener("click", () => {
        if (this.targetInput) {
          this.targetInput.value = p.id;
          // Flash input to show update
          this.targetInput.style.borderColor = "var(--accent)";
          setTimeout(() => (this.targetInput.style.borderColor = ""), 500);
        }
        this.close();
      });
      this.list.appendChild(div);
    });
  },
};

// Event Listeners for Playlist Picker
$$(".btn-browse-playlist").forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.target;
    if (target) playlistModal.open(target);
  });
});

playlistModal.closeBtn.addEventListener("click", () => playlistModal.close());

// Close modal when clicking outside
window.addEventListener("click", (e) => {
  if (e.target === playlistModal.el) {
    playlistModal.close();
  }
});

// ── Init ──────────────────────────────────────────────────────────────────
loadSettings();
