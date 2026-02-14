// electron/preload.js - Secure IPC bridge between main and renderer.
// Exposes only specific channels, preventing renderer from accessing Node.js directly.

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  // Dialog pickers
  selectFolder: () => ipcRenderer.invoke("select-folder"),
  selectFile: () => ipcRenderer.invoke("select-file"),
  saveFile: (options) => ipcRenderer.invoke("save-file", options),
  writeFile: (options) => ipcRenderer.invoke("write-file", options),

  // Process control
  startScan: (options) => ipcRenderer.invoke("start-scan", options),
  startRetry: (options) => ipcRenderer.invoke("start-retry", options),
  startYoutube: (options) => ipcRenderer.invoke("start-youtube", options),
  addTracks: (options) => ipcRenderer.invoke("add-tracks", options),
  listPlaylists: (options) => ipcRenderer.invoke("list-playlists", options),
  getPlaylistItems: (options) => ipcRenderer.invoke("get-playlist-items", options),
  search: (options) => ipcRenderer.invoke("search", options),
  removeDuplicates: (options) => ipcRenderer.invoke("remove-duplicates", options),
  scanDuplicates: (options) => ipcRenderer.invoke("scan-duplicates", options),
  cancelProcess: () => ipcRenderer.invoke("cancel-process"),

  // Listen for Python subprocess messages
  onPythonMessage: (callback) => {
    const handler = (_event, message) => callback(message);
    ipcRenderer.on("python-message", handler);
    // Return cleanup function
    return () => ipcRenderer.removeListener("python-message", handler);
  },
});
