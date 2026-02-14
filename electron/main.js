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

app.whenReady().then(createWindow);

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
    title: "Select Failed Matches File",
    filters: [{ name: "Text Files", extensions: ["txt"] }],
  });
  return result.canceled ? null : result.filePaths[0];
});

// Start scan & match process
ipcMain.handle("start-scan", async (_event, options) => {
  return runPython("main.py", options);
});

// Start retry process
ipcMain.handle("start-retry", async (_event, options) => {
  return runPython("retry_failed.py", options);
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
    const command = script === "retry_failed.py" ? "retry" : "scan";
    const exePath = getExePath();
    const args = [command, "--gui"];

    // Build argument list from options
    if (options.username) args.push(options.username);
    if (options.musicDir) args.push("-d", options.musicDir);
    if (options.playlistId) args.push("-p", options.playlistId);
    if (options.inputFile) args.push("-i", options.inputFile);
    if (options.outputFile) args.push("-o", options.outputFile);

    // Set environment variables for Spotify credentials
    const env = { ...process.env };
    if (options.clientId) env.SPOTIPY_CLIENT_ID = options.clientId;
    if (options.clientSecret) env.SPOTIPY_CLIENT_SECRET = options.clientSecret;

    pythonProcess = spawn(exePath, args, {
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });

    pythonProcess.stdout.on("data", (data) => {
      const lines = data.toString().split("\n").filter(Boolean);
      for (const line of lines) {
        try {
          const msg = JSON.parse(line);
          mainWindow?.webContents.send("python-message", msg);
        } catch {
          // Non-JSON output (legacy print statements)
          mainWindow?.webContents.send("python-message", {
            type: "log",
            text: line,
          });
        }
      }
    });

    pythonProcess.stderr.on("data", (data) => {
      const text = data.toString().trim();
      if (text) {
        mainWindow?.webContents.send("python-message", {
          type: "error",
          text,
        });
      }
    });

    pythonProcess.on("close", (code) => {
      pythonProcess = null;
      mainWindow?.webContents.send("python-message", {
        type: "done",
        code,
      });
      resolve({ success: code === 0 });
    });

    pythonProcess.on("error", (err) => {
      pythonProcess = null;
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
