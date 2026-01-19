# Electron App Build & Run Requirements

## System Requirements

### Operating System
- **Windows**: Windows 10 or later (for Windows build)
- **macOS**: macOS 10.13 or later (for macOS build)
- **Linux**: Modern Linux distribution (for Linux build)

### Hardware
- Minimum 2GB RAM (4GB+ recommended)
- ~500MB free disk space for dependencies
- ~200MB for built application

## Software Requirements

### 1. Node.js & npm
- **Node.js**: v18.0.0 or later (v20+ recommended)
- **npm**: v9.0.0 or later (comes with Node.js)
- **Installation**: Download from [nodejs.org](https://nodejs.org/)

**Verify installation:**
```bash
node --version  # Should show v18+ or v20+
npm --version   # Should show v9+ or v10+
```

### 2. Python (Optional - for backend)
- **Python**: 3.10, 3.11, or 3.12
- **Purpose**: Required only if Electron app needs to run the Python backend
- **Package Manager**: `uv` (recommended) or `pip`
- **Installation**: Download from [python.org](https://www.python.org/)

**Note**: The Electron app can run with just the frontend if the backend is not needed, or if the backend runs separately.

### 3. Git (Optional - for cloning repository)
- **Git**: Any recent version
- **Purpose**: Only needed if cloning from a repository

## Build Requirements

### NPM Dependencies
Install root and client dependencies:

```bash
# Root dependencies (Electron, electron-builder)
npm install

# Client dependencies (React, TypeScript, Vite)
cd client
npm install
cd ..
```

**Key dependencies:**
- `electron`: ^28.0.0 (Electron runtime)
- `electron-builder`: ^24.9.1 (Build tool)
- `vite`: ^7.2.4 (Frontend build tool)
- `typescript`: ~5.9.3 (TypeScript compiler)

### Python Dependencies (if backend is needed)
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

## Build Process

### 1. Build Frontend (Client)
```bash
npm run client:build
# or
cd client && npm run build
```

This compiles TypeScript, bundles React app with Vite, and outputs to `client/dist/`.

### 2. Build Electron App
```bash
# Build for current platform
npm run electron:build

# Build for specific platform
npm run electron:build:win   # Windows
npm run electron:build:mac   # macOS
npm run electron:build:linux # Linux

# Build directory only (no installer)
npm run electron:build -- --dir
```

**Output locations:**
- Windows: `client/dist/desktop/win-unpacked/CreditNexus.exe`
- macOS: `client/dist/desktop/mac/CreditNexus.app`
- Linux: `client/dist/desktop/linux-unpacked/creditnexus`

## Runtime Requirements

### For Development Mode
```bash
# Run frontend dev server + Electron
npm run electron:dev

# Or separately:
npm run frontend  # Start Vite dev server (port 5173)
# Then start Electron manually
```

**Requirements:**
- Frontend dev server running on `http://localhost:5173`
- Node.js runtime

### For Production (Built App)
**Standalone executable:**
- No additional requirements - self-contained
- Includes Electron runtime (~100MB)
- Includes bundled frontend assets

**If backend is required:**
- Python 3.10+ installed
- Python dependencies installed
- Backend server accessible (default: `http://localhost:8000`)

## File Structure After Build

```
client/dist/
├── assets/              # Compiled JS/CSS
├── index.html          # Frontend entry point
└── desktop/
    ├── win-unpacked/   # Unpacked Windows app
    │   └── CreditNexus.exe
    ├── CreditNexus-0.0.0-win.exe  # Windows installer
    └── ...
```

## Running the Built App

### Windows
```bash
# Option 1: Run unpacked executable
.\client\dist\desktop\win-unpacked\CreditNexus.exe

# Option 2: Run installer (if built with installer)
.\client\dist\desktop\CreditNexus-0.0.0-win.exe
```

### macOS
```bash
open client/dist/desktop/mac/CreditNexus.app
```

### Linux
```bash
./client/dist/desktop/linux-unpacked/creditnexus
```

## Troubleshooting

### Build Errors

1. **TypeScript errors**: 
   - Check `client/tsconfig.app.json` configuration
   - May need to disable `noUnusedLocals` temporarily for testing

2. **Missing dependencies**:
   ```bash
   npm install
   cd client && npm install
   ```

3. **Electron not found**:
   ```bash
   npm install --save-dev electron electron-builder
   ```

### Runtime Errors

1. **Blank/empty window**:
   - Check DevTools (F12 or automatic) for console errors
   - Verify `client/dist/index.html` exists
   - Check path resolution in `electron/main.js`

2. **Backend connection errors**:
   - Ensure Python backend is running (if needed)
   - Check `SERVER_URL` in `electron/main.js`
   - Verify port 8000 is not in use

3. **Asset loading errors**:
   - Check `client/dist/assets/` directory exists
   - Verify build completed successfully
   - Check browser console for 404 errors

## Quick Start Checklist

- [ ] Node.js 18+ installed
- [ ] `npm install` completed (root directory)
- [ ] `cd client && npm install` completed
- [ ] `npm run client:build` succeeded
- [ ] `npm run electron:build -- --dir` succeeded
- [ ] Executable exists at `client/dist/desktop/win-unpacked/CreditNexus.exe`

## Environment Variables (Optional)

Create `.env` file for configuration:

```env
# Backend (if needed)
DATABASE_URL=postgresql://...
API_URL=http://localhost:8000

# Electron
NODE_ENV=production
```

## Notes

- The Electron app is **self-contained** and doesn't require Node.js to run after building
- Development mode requires both Node.js and a running Vite dev server
- The app can work standalone (frontend only) or with a Python backend
- DevTools are enabled by default in production for debugging
