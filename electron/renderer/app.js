// electron/renderer/app.js - Frontend logic for MP3toSpotify GUI.
// Flow: Import (additive) → Songs (review) → Playlist (add)

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  isRunning: false,
  scanned: 0,
  matched: 0,
  failed: 0,
  total: 0,
  songs: [],           // { name, status, trackId?, checked }
  seenNames: new Set(),
  filter: "all",
  cleanup: null,
};

// ── Helpers ───────────────────────────────────────────────────────────────
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── DOM ───────────────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
  // Tabs & Panels
  tabs: $$(".tab"),
  importPanel: $("#import-panel"),
  songsPanel: $("#songs-panel"),
  playlistPanel: $("#playlist-panel"),
  settingsPanel: $("#settings-panel"),

  // Settings
  clientId: $("#client-id"),
  clientSecret: $("#client-secret"),
  username: $("#username"),
  saveSettings: $("#save-settings"),
  settingsStatus: $("#settings-status"),

  // Import: Local
  musicDir: $("#music-dir"),
  btnSelectFolder: $("#btn-select-folder"),
  btnStartScan: $("#btn-start-scan"),

  // Import: Retry
  retryInput: $("#retry-input"),
  btnSelectFile: $("#btn-select-file"),
  btnStartRetry: $("#btn-start-retry"),

  // Import: YouTube
  youtubeUrl: $("#youtube-url"),
  btnStartYoutube: $("#btn-start-youtube"),

  // Import: Progress
  importProgress: $("#import-progress"),
  progressLabel: $("#progress-label"),
  progressPct: $("#progress-pct"),
  progressBar: $("#progress-bar"),
  btnCancel: $("#btn-cancel"),

  // Import: Summary
  importSummary: $("#import-summary"),
  statScanned: $("#stat-scanned"),
  statMatched: $("#stat-matched"),
  statFailed: $("#stat-failed"),
  statRate: $("#stat-rate"),
  btnGoToSongs: $("#btn-go-to-songs"),

  // Songs
  songList: $("#song-list"),
  filterButtons: $$(".filter-btn"),
  selectAllCheckbox: $("#select-all-checkbox"),
  selectedCount: $("#selected-count"),
  btnGoToPlaylist: $("#btn-go-to-playlist"),
  tabSongCount: $("#tab-song-count"),

  // Playlist
  newPlaylistName: $("#new-playlist-name"),
  btnCreateAndAdd: $("#btn-create-and-add"),
  btnRefreshPlaylists: $("#btn-refresh-playlists"),
  playlistList: $("#playlist-list"),
  playlistAddStatus: $("#playlist-add-status"),

  // External
  linkSpotifyDev: $("#link-spotify-dev"),
};

// ── Settings ──────────────────────────────────────────────────────────────
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
    username: els.username.value.trim(),
    clientId: els.clientId.value.trim(),
    clientSecret: els.clientSecret.value.trim(),
  };
}

function validateCredentials() {
  const creds = getCredentials();
  if (!creds.clientId || !creds.clientSecret || !creds.username) {
    alert("Please configure your Spotify credentials first.\nGo to the Settings tab.");
    return null;
  }
  return creds;
}

// ── Tab Switching ─────────────────────────────────────────────────────────
const panels = {
  import: els.importPanel,
  songs: els.songsPanel,
  playlist: els.playlistPanel,
  settings: els.settingsPanel,
};

function switchTab(tabName) {
  els.tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));
  Object.entries(panels).forEach(([name, panel]) => {
    panel.style.display = name === tabName ? "block" : "none";
  });
  // Auto-load playlists when switching to playlist tab
  if (tabName === "playlist" && els.playlistList.querySelector(".loading-spinner")) {
    loadPlaylists();
  }
}

els.tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

// ── Import Helpers ────────────────────────────────────────────────────────
function setImporting(running) {
  state.isRunning = running;
  els.importProgress.style.display = running ? "block" : "none";
  // Disable all import buttons during import
  els.btnStartScan.disabled = running;
  els.btnStartRetry.disabled = running;
  els.btnStartYoutube.disabled = running;
}

function updateStats() {
  els.statScanned.textContent = state.scanned;
  els.statMatched.textContent = state.matched;
  els.statFailed.textContent = state.failed;
  const rate = state.scanned > 0 ? Math.round((state.matched / state.scanned) * 100) : 0;
  els.statRate.textContent = `${rate}%`;

  if (state.total > 0) {
    const pct = Math.round((state.scanned / state.total) * 100);
    els.progressBar.style.width = `${pct}%`;
    els.progressPct.textContent = `${pct}%`;
  }

  // Update tab badge
  const matchCount = state.songs.filter((s) => s.status === "matched").length;
  if (matchCount > 0) {
    els.tabSongCount.style.display = "inline";
    els.tabSongCount.textContent = matchCount;
  }
}

function updateSelectedCount() {
  const count = state.songs.filter((s) => s.status === "matched" && s.checked).length;
  els.selectedCount.textContent = `${count} selected`;
}

// ── Song List ─────────────────────────────────────────────────────────────
function addSongToList(song) {
  if (state.seenNames.has(song.name)) return;
  state.seenNames.add(song.name);
  state.songs.push(song);
}

function renderSongItem(song, idx) {
  if (state.filter !== "all" && state.filter !== song.status) return;

  const row = document.createElement("div");
  row.className = `song-item song-${song.status}`;
  row.dataset.index = idx;

  const icon = song.status === "matched" ? "✓" : "✗";
  const iconClass = song.status === "matched" ? "song-icon-matched" : "song-icon-failed";
  const checkboxHtml = song.status === "matched"
    ? `<input type="checkbox" class="song-checkbox" data-index="${idx}" ${song.checked ? "checked" : ""}>`
    : "";

  row.innerHTML = `
    ${checkboxHtml}
    <span class="song-icon ${iconClass}">${icon}</span>
    <span class="song-name">${escapeHtml(song.name)}</span>
  `;
  els.songList.appendChild(row);
}

function rerenderSongList() {
  els.songList.innerHTML = "";
  if (state.songs.length === 0) {
    els.songList.innerHTML = `
      <div class="empty-state">
        <p>No songs imported yet.</p>
        <p class="hint">Go to the <strong>Import</strong> tab to add songs.</p>
      </div>`;
    return;
  }
  state.songs.forEach((song, idx) => renderSongItem(song, idx));
  updateSelectedCount();
}

function filterSongs(filter) {
  state.filter = filter;
  els.filterButtons.forEach((b) => b.classList.toggle("active", b.dataset.filter === filter));
  rerenderSongList();
}

// ── Python Message Handler ────────────────────────────────────────────────
function handlePythonMessage(msg) {
  switch (msg.type) {
    case "total":
      state.total += msg.count;
      els.progressLabel.textContent = `Processing ${msg.count} files...`;
      break;

    case "match":
      state.scanned++;
      state.matched++;
      addSongToList({
        name: msg.name,
        status: "matched",
        trackId: msg.trackId,
        checked: true,
      });
      updateStats();
      break;

    case "fail":
      state.scanned++;
      state.failed++;
      addSongToList({
        name: msg.name,
        status: "failed",
        trackId: null,
        checked: false,
      });
      updateStats();
      break;

    case "summary": {
      const m = msg.matched || 0;
      const f = msg.failed || 0;
      els.progressLabel.textContent = `Done! ${m} matched, ${f} failed.`;
      els.progressBar.style.width = "100%";
      els.progressPct.textContent = "100%";
      break;
    }

    case "done":
      setImporting(false);
      els.importSummary.style.display = "block";
      updateStats();
      rerenderSongList();
      break;

    case "error":
      els.progressLabel.textContent = `Error: ${msg.text}`;
      break;
  }
}

// ── Event Listeners: Settings ─────────────────────────────────────────────
els.saveSettings.addEventListener("click", saveSettings);
els.linkSpotifyDev.addEventListener("click", (e) => {
  e.preventDefault();
  // Open in default browser (works in Electron renderer)
  window.open("https://developer.spotify.com/dashboard", "_blank");
});

// ── Event Listeners: Import ───────────────────────────────────────────────

els.btnSelectFolder.addEventListener("click", async () => {
  const folder = await window.api.selectFolder();
  if (folder) els.musicDir.value = folder;
});

els.btnSelectFile.addEventListener("click", async () => {
  const file = await window.api.selectFile();
  if (file) els.retryInput.value = file;
});

// Local Scan
els.btnStartScan.addEventListener("click", async () => {
  const creds = validateCredentials();
  if (!creds) return;
  const musicDir = els.musicDir.value;
  if (!musicDir) { alert("Please select a music directory first."); return; }

  setImporting(true);
  els.importSummary.style.display = "none";
  els.progressLabel.textContent = "Scanning music files...";
  els.progressBar.style.width = "0%";
  els.progressPct.textContent = "0%";

  if (state.cleanup) state.cleanup();
  state.cleanup = window.api.onPythonMessage(handlePythonMessage);

  await window.api.startScan({
    username: creds.username,
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    musicDir,
  });
});

// YouTube Import
els.btnStartYoutube.addEventListener("click", async () => {
  const creds = validateCredentials();
  if (!creds) return;
  const url = els.youtubeUrl.value.trim();
  if (!url) { alert("Please enter a YouTube playlist URL."); return; }

  setImporting(true);
  els.importSummary.style.display = "none";
  els.progressLabel.textContent = "Fetching YouTube playlist...";
  els.progressBar.style.width = "0%";
  els.progressPct.textContent = "0%";

  if (state.cleanup) state.cleanup();
  state.cleanup = window.api.onPythonMessage(handlePythonMessage);

  await window.api.startYoutube({
    username: creds.username,
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    youtubeUrl: url,
  });
});

// Retry Failed
els.btnStartRetry.addEventListener("click", async () => {
  const creds = validateCredentials();
  if (!creds) return;
  const inputFile = els.retryInput.value;
  if (!inputFile) { alert("Please select a failed matches file first."); return; }

  setImporting(true);
  els.importSummary.style.display = "none";
  els.progressLabel.textContent = "Retrying failed matches...";
  els.progressBar.style.width = "0%";
  els.progressPct.textContent = "0%";

  if (state.cleanup) state.cleanup();
  state.cleanup = window.api.onPythonMessage(handlePythonMessage);

  await window.api.startRetry({
    username: creds.username,
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    inputFile,
  });
});

// Cancel
els.btnCancel.addEventListener("click", async () => {
  await window.api.cancelProcess();
  setImporting(false);
  els.progressLabel.textContent = "Cancelled.";
});

// Navigate to Songs tab after import
els.btnGoToSongs.addEventListener("click", () => switchTab("songs"));

// ── Event Listeners: Songs ────────────────────────────────────────────────

// Checkbox delegation
els.songList.addEventListener("change", (e) => {
  if (e.target.classList.contains("song-checkbox")) {
    const idx = parseInt(e.target.dataset.index, 10);
    if (state.songs[idx]) {
      state.songs[idx].checked = e.target.checked;
      updateSelectedCount();
    }
  }
});

// Select All
els.selectAllCheckbox.addEventListener("change", () => {
  const val = els.selectAllCheckbox.checked;
  state.songs.forEach((s) => { if (s.status === "matched") s.checked = val; });
  rerenderSongList();
});

// Filters
els.filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => filterSongs(btn.dataset.filter));
});

// Navigate to Playlist tab
els.btnGoToPlaylist.addEventListener("click", () => {
  const selected = state.songs.filter((s) => s.status === "matched" && s.checked && s.trackId);
  if (selected.length === 0) {
    alert("No matched songs selected. Check the songs you want to add.");
    return;
  }
  switchTab("playlist");
});

// ── Playlist Tab ──────────────────────────────────────────────────────────

async function loadPlaylists() {
  const creds = validateCredentials();
  if (!creds) return;

  try {
    els.playlistList.innerHTML = '<div class="loading-spinner">Fetching playlists from Spotify...</div>';
    const playlists = await window.api.listPlaylists({
      username: creds.username,
      clientId: creds.clientId,
      clientSecret: creds.clientSecret,
    });

    if (!playlists || playlists.length === 0) {
      els.playlistList.innerHTML = '<div class="loading-spinner">No playlists found. Create one above!</div>';
      return;
    }

    renderPlaylists(playlists);
  } catch (err) {
    console.error(err);
    els.playlistList.innerHTML = `<div class="loading-spinner" style="color:var(--danger)">Error: ${err.message || "Failed to load"}</div>`;
  }
}

function renderPlaylists(playlists) {
  els.playlistList.innerHTML = "";
  playlists.forEach((p) => {
    const div = document.createElement("div");
    div.className = "playlist-item";
    div.innerHTML = `
      <div class="playlist-info">
        <span class="playlist-name">${escapeHtml(p.name)}</span>
        <span class="playlist-meta">${p.tracks_total} tracks</span>
      </div>
      <button class="playlist-select-btn">Add here</button>
    `;
    div.addEventListener("click", () => addToPlaylist(p.id, ""));
    els.playlistList.appendChild(div);
  });
}

async function addToPlaylist(playlistId, playlistName) {
  const creds = validateCredentials();
  if (!creds) return;

  const selected = state.songs.filter((s) => s.status === "matched" && s.checked && s.trackId);
  if (selected.length === 0) {
    alert("No matched songs selected. Go to the Songs tab to select songs first.");
    return;
  }

  const trackIds = selected.map((s) => s.trackId).join(",");

  els.playlistAddStatus.textContent = "Adding tracks...";
  els.playlistAddStatus.style.color = "var(--text-secondary)";

  if (state.cleanup) state.cleanup();
  state.cleanup = window.api.onPythonMessage((msg) => {
    if (msg.type === "summary") {
      const added = msg.matched || 0;
      els.playlistAddStatus.textContent = `✓ Added ${added} tracks to playlist!`;
      els.playlistAddStatus.style.color = "var(--success, #1DB954)";
    } else if (msg.type === "error") {
      els.playlistAddStatus.textContent = `Error: ${msg.text}`;
      els.playlistAddStatus.style.color = "var(--danger)";
    }
  });

  await window.api.addTracks({
    username: creds.username,
    clientId: creds.clientId,
    clientSecret: creds.clientSecret,
    playlistId: playlistId || "",
    playlistName: playlistName || "",
    trackIds,
  });
}

// Create & Add
els.btnCreateAndAdd.addEventListener("click", () => {
  const name = els.newPlaylistName.value.trim();
  if (!name) {
    els.newPlaylistName.focus();
    els.newPlaylistName.style.borderColor = "var(--danger)";
    setTimeout(() => (els.newPlaylistName.style.borderColor = ""), 1000);
    return;
  }
  addToPlaylist("", name);
});

// Refresh playlists
els.btnRefreshPlaylists.addEventListener("click", loadPlaylists);

// ── Init ──────────────────────────────────────────────────────────────────
loadSettings();
