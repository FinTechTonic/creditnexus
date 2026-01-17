const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getServerUrl: () => ipcRenderer.invoke('get-server-url'),
  checkServerHealth: () => ipcRenderer.invoke('check-server-health'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  getVersion: () => ipcRenderer.invoke('get-version'),
  platform: process.platform
});

// Expose FDC3 if available (for OpenFin compatibility)
if (typeof window !== 'undefined' && window.fdc3) {
  contextBridge.exposeInMainWorld('fdc3', window.fdc3);
}
