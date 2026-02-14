// electron/renderer/app.js - Frontend logic for MP3toSpotify GUI.

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  isRunning: false,
  scanned: 0,
  matched: 0,
  failed: 0,
  total: 0,
  songs: [],       // { name, status: 'matched'|'failed' }
  filter: "all",
  cleanup: null,    // Listener cleanup function
};

// ── DOM Elements ──────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
  // Tabs & Panels
  tabs: $$(".tab"),
  scanPanel: $("#scan-panel"),
  retryPanel: $("#retry-panel"),
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
  els.settingsPanel.style.display = tabName === "settings" ? "" : "none";
}

// ── UI Helpers ────────────────────────────────────────────────────────────
function resetStats() {
  state.scanned = 0;
  state.matched = 0;
  state.failed = 0;
  state.total = 0;
  state.songs = [];
  updateStats();
  els.songList.innerHTML = "";
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

function addSongToList(name, status) {
  const song = { name, status };
  state.songs.push(song);

  if (state.filter === "all" || state.filter === status) {
    appendSongElement(song, state.songs.length);
  }
}

function appendSongElement(song, index) {
  const div = document.createElement("div");
  div.className = `song-item ${song.status}`;
  div.innerHTML = `
    <span class="song-index">${index}</span>
    <span class="song-status">${song.status === "matched" ? "✓" : "✗"}</span>
    <span class="song-name" title="${escapeHtml(song.name)}">${escapeHtml(song.name)}</span>
  `;
  els.songList.appendChild(div);
  els.songList.scrollTop = els.songList.scrollHeight;
}

function filterSongs(filter) {
  state.filter = filter;
  els.filterButtons.forEach((b) => b.classList.toggle("active", b.dataset.filter === filter));
  els.songList.innerHTML = "";
  state.songs.forEach((song, i) => {
    if (filter === "all" || filter === song.status) {
      appendSongElement(song, i + 1);
    }
  });
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
  els.btnStartScan.disabled = running;
  els.btnStartRetry.disabled = running;
  els.resultsSection.style.display = "";
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
    case "progress":
      state.scanned = msg.current || state.scanned;
      state.total = msg.total || state.total;
      els.progressLabel.textContent = msg.text || "Processing...";
      updateStats();
      break;

    case "match":
      state.scanned++;
      state.matched++;
      addSongToList(msg.name, "matched");
      updateStats();
      break;

    case "no_match":
      state.scanned++;
      state.failed++;
      addSongToList(msg.name, "failed");
      updateStats();
      break;

    case "summary":
      state.total = msg.total || state.scanned;
      state.matched = msg.matched || state.matched;
      state.failed = msg.failed || state.failed;
      state.scanned = state.total;
      updateStats();
      els.progressLabel.textContent = "Complete!";
      break;

    case "done":
      setRunning(false);
      els.progressLabel.textContent =
        msg.code === 0 ? "✓ Complete!" : `Process exited with code ${msg.code}`;
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
  // In Electron, we use shell.openExternal via a simple workaround
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

  // Clean up previous listener
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

// Cancel
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

// Filters
els.filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => filterSongs(btn.dataset.filter));
});

// ── Init ──────────────────────────────────────────────────────────────────
loadSettings();
