# Running CreditNexus in OpenFin

This guide explains how to run the CreditNexus application with the OpenFin runtime.

## Prerequisites

1. **OpenFin Runtime** - Install the OpenFin Runtime:
   ```powershell
   # Using OpenFin CLI
   npm install -g @openfin/cli
   ```
   
   Or download from: https://openfin.co/

2. **Node.js & npm** - For running the frontend
3. **Python 3.10+** - For running the backend
4. **.env file** - Already configured in the project root

## Quick Start

### On Windows (PowerShell):

```powershell
# Make sure you're in the project root
cd c:\Users\odolb\projects\creditNexus1

# Run the automated startup script
.\run_openfin.ps1
```

Or using npm:
```powershell
npm run dev
```

### On Mac/Linux:

```bash
cd /path/to/creditNexus1
bash run_openfin.sh
```

Or using npm:
```bash
npm run dev:unix
```

## Manual Startup (Advanced)

If you prefer to run services separately, open multiple terminals:

### Terminal 1 - Backend Server:
```powershell
cd c:\Users\odolb\projects\creditNexus1
python scripts/run_dev.py
# Server runs at: http://127.0.0.1:8000
```

### Terminal 2 - Frontend Dev Server:
```powershell
cd c:\Users\odolb\projects\creditNexus1\client
npm run dev
# Frontend runs at: http://localhost:5173
```

### Terminal 3 - Launch OpenFin:
```powershell
npm run openfin:launch
# Or
openfin launch --config openfin/app.json
```

## What Happens

1. **Backend Server** starts on `http://127.0.0.1:8000`
   - FastAPI application
   - Hot reload enabled
   - Serves API endpoints and static files

2. **Frontend Dev Server** starts on `http://localhost:5173`
   - Vite development server
   - Hot module replacement (HMR) enabled
   - React application with TypeScript

3. **OpenFin Runtime** launches the application
   - Configured in `openfin/app.json`
   - Platform UUID: `creditnexus-platform`
   - Loads frontend from `http://localhost:8000` (redirected from Vite)
   - Includes FDC3 interoperability

## OpenFin Configuration

The configuration is in `openfin/app.json`:

- **Platform**: creditnexus-platform
- **Default Window**: 1400×900 pixels
- **Entry Point**: http://localhost:8000
- **Security Realm**: creditnexus
- **FDC3 Interop**: 2.0

## Troubleshooting

### Backend Won't Start
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Install Python dependencies
pip install -r requirements.txt
```

### Frontend Won't Start
```powershell
# Install Node dependencies
cd client
npm install
```

### OpenFin Won't Launch
```powershell
# Verify OpenFin CLI is installed
openfin --version

# Install if needed
npm install -g @openfin/cli
```

### Cannot Connect to Services
- Ensure firewall allows localhost traffic
- Check that ports 8000 and 5173 are available
- Verify .env file has correct DATABASE_URL

## Stopping Services

### From the startup script:
Press `Ctrl+C` in each service window

### Manual cleanup:
```powershell
# Close OpenFin applications
# Stop frontend terminal with Ctrl+C
# Stop backend terminal with Ctrl+C
```

## Production Build

To build the frontend for production:

```powershell
cd client
npm run build
# Output goes to: client/dist
```

Then configure `openfin/app.json` to point to the production build location.

## Environment Variables

The application requires the following in `.env`:

```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=...
SENTINELHUB_KEY=...
SENTINELHUB_SECRET=...
```

All variables are already configured in your .env file.

## Development Tips

- **Hot Reload**: Both backend and frontend support hot reload during development
- **FDC3 Messages**: Use FDC3 2.0 for inter-window communication
- **Redux DevTools**: Available in Chrome DevTools for the React app
- **API Debugging**: Backend API available at http://127.0.0.1:8000/docs (OpenAPI)

## More Information

- [OpenFin Documentation](https://developers.openfin.co/)
- [FDC3 Specification](https://fdc3.finos.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vite Documentation](https://vitejs.dev/)
