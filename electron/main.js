const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');
const fs = require('fs');
const https = require('https');
const http = require('http');
const { initializeFDC3Bridge } = require('./fdc3-bridge');

// Use a user-writable cache dir to avoid "Access is denied" / "Unable to create cache" on Windows
const cacheBase = process.platform === 'win32'
  ? (process.env.LOCALAPPDATA || process.env.APPDATA || os.homedir())
  : (process.env.XDG_CACHE_HOME || path.join(os.homedir(), '.cache'));
app.commandLine.appendSwitch('disk-cache-dir', path.join(cacheBase, 'CreditNexus', 'electron-cache'));

let mainWindow = null;
let serverProcess = null;
const SERVER_PORT = 8000;
const SERVER_URL = `http://localhost:${SERVER_PORT}`;

// #region agent log
function _debugLog(location, message, data, hypothesisId) {
  try {
    const logPath = app.isPackaged
      ? path.join(app.getPath('userData'), 'debug.log')
      : path.join(__dirname, '..', '.cursor', 'debug.log');
    const dir = path.dirname(logPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(logPath, JSON.stringify({ location, message, data, hypothesisId, timestamp: Date.now(), sessionId: 'debug-session' }) + '\n');
  } catch (_) {}
}
// #endregion

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: true
    },
    icon: path.join(__dirname, '../assets/icon.png'),
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    show: false
  });
  
  // Load app
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    const loadPath = path.join(__dirname, '../client/dist/index.html');
    const assetsDir = path.join(__dirname, '../client/dist/assets');
    // #region agent log
    _debugLog('electron/main.js:createWindow', 'loadFile path check', {
      loadPath,
      indexExists: fs.existsSync(loadPath),
      assetsDirExists: fs.existsSync(assetsDir),
      __dirname,
      appPath: app.getAppPath(),
      isPackaged: app.isPackaged
    }, 'H1');
    // #endregion
    mainWindow.loadFile(loadPath);
  }

  const openDevTools = () => { try { mainWindow.webContents.openDevTools(); } catch (_) {} };
  mainWindow.webContents.on('did-fail-load', (_e, code, desc, url) => {
    // #region agent log
    _debugLog('electron/main.js:did-fail-load', 'page load failed', { errorCode: code, errorDescription: desc, url }, 'H1');
    // #endregion
    openDevTools();
  });
  mainWindow.webContents.on('did-finish-load', () => {
    // #region agent log
    mainWindow.webContents.executeJavaScript(
      `(function(){ var r=document.getElementById('root'); return { rootEmpty: !r || !r.innerHTML, scriptSrc: (document.querySelector('script[src]')||{}).src, href: (document.querySelector('link[href]')||{}).href }; })()`
    ).then((o) => {
      _debugLog('electron/main.js:did-finish-load', 'page loaded', o || {}, 'H2');
    }).catch(() => { _debugLog('electron/main.js:did-finish-load', 'page loaded', { executeError: true }, 'H2'); });
    // #endregion
    if (process.env.NODE_ENV !== 'development' && process.env.ELECTRON_OPEN_DEVTOOLS === '1') openDevTools();
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
}

function startServer() {
  const serverScript = path.join(__dirname, '../server.py');
  const cwd = path.join(__dirname, '..');
  const venvPython = process.platform === 'win32'
    ? path.join(cwd, '.venv', 'Scripts', 'python.exe')
    : path.join(cwd, '.venv', 'bin', 'python');
  const pythonExecutable = fs.existsSync(venvPython) ? venvPython : (process.platform === 'win32' ? 'python' : 'python3');

  serverProcess = spawn(pythonExecutable, [serverScript], {
    cwd,
    env: { ...process.env, PORT: SERVER_PORT }
  });
  
  serverProcess.stdout.on('data', (data) => {
    console.log(`Server: ${data}`);
  });
  
  serverProcess.stderr.on('data', (data) => {
    console.error(`Server Error: ${data}`);
  });
  
  serverProcess.on('error', (error) => {
    console.error(`Failed to start server: ${error.message}`);
  });
}

function stopServer() {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
}

// IPC handlers for client-server communication
ipcMain.handle('get-server-url', () => SERVER_URL);

ipcMain.handle('check-server-health', async () => {
  return new Promise((resolve) => {
    http.get(`${SERVER_URL}/api/health`, (res) => {
      resolve(res.statusCode === 200);
    }).on('error', () => resolve(false));
  });
});

ipcMain.handle('open-external', async (event, url) => {
  await shell.openExternal(url);
});

ipcMain.handle('get-version', () => {
  return app.getVersion();
});

app.whenReady().then(() => {
  initializeFDC3Bridge();
  startServer();
  createWindow();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopServer();
    app.quit();
  }
});

app.on('before-quit', () => {
  stopServer();
});
