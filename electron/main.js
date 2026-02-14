// electron/main.js - Electron main process
// Handles window lifecycle, IPC communication, and Python subprocess management.

const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let mainWindow = null;
let pythonProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 960,
    height: 720,
    minWidth: 800,
    minHeight: 600,
    title: "MP3toSpotify",
    backgroundColor: "#1a1a2e",
    icon: path.join(__dirname, "assets", "icon.ico"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
  mainWindow.setMenuBarVisibility(false);

  mainWindow.on("closed", () => {
    killPython();
    mainWindow = null;
  });
}

const fs = require("fs");

async function generateIconIfNeeded() {
  const iconPath = path.join(__dirname, "assets", "icon.png");
  const svgPath = path.join(__dirname, "assets", "icon.svg");

  if (!fs.existsSync(iconPath) && fs.existsSync(svgPath)) {
    console.log("Generating icon.png from icon.svg...");
    const win = new BrowserWindow({ 
      show: false, 
      width: 512, 
      height: 512,
      webPreferences: { offscreen: true } 
    });
    
    const svgData = fs.readFileSync(svgPath);
    const dataUri = `data:image/svg+xml;base64,${svgData.toString("base64")}`;
    
    try {
      await win.loadURL(dataUri);
      // Give it a moment to render
      await new Promise(r => setTimeout(r, 500));
      const image = await win.webContents.capturePage();
      fs.writeFileSync(iconPath, image.toPNG());
      console.log("icon.png generated.");
    } catch (err) {
      console.error("Failed to generate icon:", err);
    } finally {
      win.close();
    }
  }
}

app.whenReady().then(async () => {
  await generateIconIfNeeded();
  createWindow();
});

app.on("window-all-closed", () => {
  killPython();
  app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

// ── IPC Handlers ──────────────────────────────────────────────────────────

// Open folder picker dialog
ipcMain.handle("select-folder", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
    title: "Select Music Directory",
  });
  return result.canceled ? null : result.filePaths[0];
});

// Open file picker dialog (for retry input)
ipcMain.handle("select-file", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile"],
    title: "Select Failed Matches File or M3U Playlist",
    filters: [{ name: "Text/Playlist", extensions: ["txt", "m3u", "m3u8"] }],
  });
  return result.canceled ? null : result.filePaths[0];
});

// Save file dialog (for M3U export)
ipcMain.handle("save-file", async (_event, options) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    title: options.title || "Save File",
    defaultPath: options.defaultPath || "playlist.m3u",
    filters: options.filters || [{ name: "M3U Playlist", extensions: ["m3u"] }],
  });
  return result.canceled ? null : result.filePath;
});

// Write file to disk (for M3U export)
ipcMain.handle("write-file", async (_event, options) => {
  const fs = require("fs");
  fs.writeFileSync(options.filePath, options.content, "utf-8");
  return { success: true };
});

// Start scan & match process
ipcMain.handle("start-scan", async (_event, options) => {
  return runPython("main.py", options);
});

// Start retry process
ipcMain.handle("start-retry", async (_event, options) => {
  return runPython("retry_failed.py", options);
});

// Start YouTube import process
ipcMain.handle("start-youtube", async (_event, options) => {
  return runPython("youtube_import.py", options);
});

// Add selected tracks to Spotify playlist
ipcMain.handle("add-tracks", async (_event, options) => {
  return runPython("addtracks", options);
});

// List user playlists
ipcMain.handle("list-playlists", async (_event, options) => {
  return runPython("listplaylists", options);
});

ipcMain.handle("search", async (_event, options) => {
  return runPython("search", options);
});

ipcMain.handle("get-playlist-items", async (_event, options) => {
  return runPython("playlist_items", options);
});

// Remove duplicate tracks
ipcMain.handle("remove-duplicates", async (_event, options) => {
  return runPython("remove_duplicates.py", options);
});

// Scan for duplicates only (preview mode)
ipcMain.handle("scan-duplicates", async (_event, options) => {
  return runPython("remove_duplicates.py", { ...options, scanOnly: true });
});

// Cancel running process
ipcMain.handle("cancel-process", async () => {
  killPython();
  return { success: true };
});

// ── Python Subprocess Management ──────────────────────────────────────────

/**
 * Resolve the path to the bundled mp3tospotify executable.
 * - Packaged: process.resourcesPath/backend/mp3tospotify[.exe]
 * - Development: <project>/backend/dist/mp3tospotify[.exe]
 */
function getExePath() {
  const exeName = process.platform === "win32" ? "mp3tospotify.exe" : "mp3tospotify";
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "backend", exeName);
  }
  return path.join(__dirname, "..", "backend", "dist", exeName);
}

function runPython(script, options) {
  return new Promise((resolve) => {
    if (pythonProcess) {
      resolve({ success: false, error: "A process is already running." });
      return;
    }

    // Map script name → cli.py command
    const commandMap = {
      "main.py": "scan",
      "retry_failed.py": "retry",
      "youtube_import.py": "youtube",
      "addtracks": "addtracks",
      "listplaylists": "listplaylists",
      "search": "search",
      "remove_duplicates.py": "remove_duplicates",
      "playlist_items": "playlist_items",
    };
    const command = commandMap[script] || "scan";
    const exePath = getExePath();

    // Build argument list: command username --gui [options]
    const args = [command];
    if (options.username) args.push(options.username);
    args.push("--gui");

    if (options.musicDir) args.push("-d", options.musicDir);
    if (options.playlistId) args.push("-p", options.playlistId);
    if (options.playlistName) args.push("-n", options.playlistName);
    if (options.inputFile) args.push("-i", options.inputFile);
    if (options.outputFile) args.push("-o", options.outputFile);
    if (options.youtubeUrl) args.push("-u", options.youtubeUrl);
    if (options.trackIds) args.push("--tracks", options.trackIds);
    if (options.query) args.push("-q", options.query);
    if (options.scanOnly) args.push("--scan-only");

    // Set environment variables for Spotify credentials
    const env = { ...process.env };
    if (options.clientId) env.SPOTIPY_CLIENT_ID = options.clientId;
    if (options.clientSecret) env.SPOTIPY_CLIENT_SECRET = options.clientSecret;
    // Force UTF-8 output from the Python executable (critical for CJK characters on Windows)
    env.PYTHONIOENCODING = "utf-8";
    env.PYTHONUTF8 = "1";

    let resolved = false;

    pythonProcess = spawn(exePath, args, {
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });

    // Ensure stdout is decoded as UTF-8
    pythonProcess.stdout.setEncoding("utf-8");

    let stdoutBuffer = "";

    pythonProcess.stdout.on("data", (data) => {
      stdoutBuffer += data.toString();
      
      let newlineIndex;
      while ((newlineIndex = stdoutBuffer.indexOf("\n")) !== -1) {
        const line = stdoutBuffer.slice(0, newlineIndex).trim();
        stdoutBuffer = stdoutBuffer.slice(newlineIndex + 1);
        
        if (!line) continue;

        try {
          const msg = JSON.parse(line);
          // If it's an array, it's the result of listplaylists or search
          if (Array.isArray(msg)) {
            resolved = true;
            if (pythonProcess) {
              pythonProcess.kill("SIGTERM");
              pythonProcess = null;
            }
            resolve(msg);
            return;
          }
          mainWindow?.webContents.send("python-message", msg);
        } catch {
          // If JSON parse fails, it might be a log message
          mainWindow?.webContents.send("python-message", {
            type: "log",
            text: line,
          });
        }
      }
    });

    let stderrBuffer = "";

    pythonProcess.stderr.on("data", (data) => {
      const text = data.toString().trim();
      if (text) {
        stderrBuffer += text + "\n";
        mainWindow?.webContents.send("python-message", {
          type: "error",
          text,
        });
      }
    });

    pythonProcess.on("close", (code) => {
      pythonProcess = null;
      if (!resolved) {
        mainWindow?.webContents.send("python-message", {
          type: "done",
          code,
        });
        resolve({ 
          success: code === 0,
          code,
          error: stderrBuffer.trim() || `Process exited with code ${code}` 
        });
      }
    });

    pythonProcess.on("error", (err) => {
      pythonProcess = null;
      if (resolved) return;
      resolved = true;
      const msg = err.message.includes("ENOENT")
        ? "Backend executable not found. The application may be corrupted — please reinstall."
        : `Failed to start process: ${err.message}`;
      mainWindow?.webContents.send("python-message", {
        type: "error",
        text: msg,
      });
      resolve({ success: false, error: msg });
    });
  });
}

function killPython() {
  if (pythonProcess) {
    pythonProcess.kill("SIGTERM");
    pythonProcess = null;
  }
}
