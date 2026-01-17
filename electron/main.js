const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const https = require('https');
const http = require('http');
const { initializeFDC3Bridge } = require('./fdc3-bridge');

let mainWindow = null;
let serverProcess = null;
const SERVER_PORT = 8000;
const SERVER_URL = `http://localhost:${SERVER_PORT}`;

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
    mainWindow.loadFile(path.join(__dirname, '../client/dist/index.html'));
  }
  
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
}

function startServer() {
  const serverScript = path.join(__dirname, '../server.py');
  const pythonExecutable = process.platform === 'win32' 
    ? 'python' 
    : 'python3';
  
  serverProcess = spawn(pythonExecutable, [serverScript], {
    cwd: path.join(__dirname, '..'),
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
