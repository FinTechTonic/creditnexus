/**
 * FDC3 Bridge for Electron
 * 
 * Provides FDC3 2.0 and OpenFin compatibility in Electron by bridging
 * FDC3 API calls between the renderer process and Electron main process.
 */

const { ipcMain, BrowserWindow } = require('electron');

// Store FDC3 context listeners
const contextListeners = new Map();
const intentListeners = new Map();

/**
 * Initialize FDC3 bridge in main process.
 * This should be called from electron/main.js after app.whenReady()
 */
function initializeFDC3Bridge() {
  // Context broadcast handler
  ipcMain.handle('fdc3-broadcast', (event, context) => {
    // Broadcast to all windows
    BrowserWindow.getAllWindows().forEach(window => {
      if (window !== event.sender) {
        window.webContents.send('fdc3-context', context);
      }
    });
  });

  // Context listener registration
  ipcMain.handle('fdc3-add-context-listener', (event, listenerId) => {
    const windowId = event.sender.id;
    if (!contextListeners.has(windowId)) {
      contextListeners.set(windowId, new Set());
    }
    contextListeners.get(windowId).add(listenerId);
  });

  // Context listener removal
  ipcMain.handle('fdc3-remove-context-listener', (event, listenerId) => {
    const windowId = event.sender.id;
    if (contextListeners.has(windowId)) {
      contextListeners.get(windowId).delete(listenerId);
    }
  });

  // Intent handler registration
  ipcMain.handle('fdc3-add-intent-listener', (event, intent, listenerId) => {
    const windowId = event.sender.id;
    const key = `${windowId}-${intent}`;
    if (!intentListeners.has(key)) {
      intentListeners.set(key, new Set());
    }
    intentListeners.get(key).add(listenerId);
  });

  // Intent listener removal
  ipcMain.handle('fdc3-remove-intent-listener', (event, intent, listenerId) => {
    const windowId = event.sender.id;
    const key = `${windowId}-${intent}`;
    if (intentListeners.has(key)) {
      intentListeners.get(key).delete(listenerId);
    }
  });

  // Intent raising
  ipcMain.handle('fdc3-raise-intent', (event, intent, context) => {
    // Find listeners for this intent across all windows
    const targetWindows = [];
    intentListeners.forEach((listeners, key) => {
      const [winId, intentName] = key.split('-');
      if (intentName === intent) {
        const window = BrowserWindow.fromId(parseInt(winId));
        if (window) {
          targetWindows.push({ window, listeners });
        }
      }
    });

    // Send intent to target windows
    targetWindows.forEach(({ window, listeners }) => {
      window.webContents.send('fdc3-intent', { intent, context, listeners: Array.from(listeners) });
    });

    return { success: true, targetCount: targetWindows.length };
  });

  // Cleanup on window close
  ipcMain.on('fdc3-window-closing', (event) => {
    const windowId = event.sender.id;
    contextListeners.delete(windowId);
    // Remove intent listeners for this window
    intentListeners.forEach((listeners, key) => {
      if (key.startsWith(`${windowId}-`)) {
        intentListeners.delete(key);
      }
    });
  });
}

module.exports = { initializeFDC3Bridge };
