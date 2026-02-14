// electron/preload.js - Secure IPC bridge between main and renderer.
// Exposes only specific channels, preventing renderer from accessing Node.js directly.

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  // Dialog pickers
  selectFolder: () => ipcRenderer.invoke("select-folder"),
  selectFile: () => ipcRenderer.invoke("select-file"),

  // Process control
  startScan: (options) => ipcRenderer.invoke("start-scan", options),
  startRetry: (options) => ipcRenderer.invoke("start-retry", options),
  cancelProcess: () => ipcRenderer.invoke("cancel-process"),

  // Listen for Python subprocess messages
  onPythonMessage: (callback) => {
    const handler = (_event, message) => callback(message);
    ipcRenderer.on("python-message", handler);
    // Return cleanup function
    return () => ipcRenderer.removeListener("python-message", handler);
  },
});
