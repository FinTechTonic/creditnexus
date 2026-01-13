# Algorithmic Nature-Finance Platform (CreditNexus)

**"Where Legal Text Meets Ground Truth"**

[![Documentation](https://img.shields.io/badge/Documentation-Read%20Docs-blue?style=flat-square)](https://docs.creditnexus.com)
[![Company Site](https://img.shields.io/badge/Company%20Site-Visit-green?style=flat-square)](https://creditnexus.com)
[![YouTube Demo](https://img.shields.io/badge/YouTube-Demo-red?style=flat-square&logo=youtube)](YOUTUBE_URL)

CreditNexus is a next-generation financial operating system that bridges the gap between **Sustainabiity-Linked Loans (Legal Contracts)** and **Physical Reality (Satellite Data)**. It uses AI agents to extract covenants from PDF agreements and orchestrates "Ground Truth" verification using geospatial deep learning.

> 📚 **[Full Documentation](https://docs.creditnexus.com)** | 🏢 **[Company Site](https://creditnexus.com)** | 🎥 **[Demo Video](YOUTUBE_URL)**

## 🚀 Quick Start

### Prerequisites

#### Install uv (Python Package Manager)

CreditNexus uses **uv** for fast and reliable Python dependency management.

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or via pip:
```bash
pip install uv
```

#### Setup Python Environment

```bash
# Install dependencies and create virtual environment
uv sync
```

This will:
- Create a `.venv` virtual environment with Python 3.11
- Install all dependencies from `pyproject.toml`
- Generate `uv.lock` for reproducible builds

**Note:** You can run commands directly with `uv run <command>` without activating the virtual environment, or activate it manually:

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 0. Database Setup

#### PostgreSQL

Ensure PostgreSQL is running and accessible. The application uses the `DATABASE_URL` environment variable.

**Windows:**

```bash
# Start PostgreSQL service using the psql client - use your own path
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE creditnexus;"
```

**Linux/macOS:**

```bash
# Start PostgreSQL service
sudo systemctl start postgresql  # Linux
# or
brew services start postgresql@XX  # macOS
```

**Or using Docker:**

```bash
docker run --name creditnexus-postgres -e POSTGRES_PASSWORD=yourpassword -e POSTGRES_DB=creditnexus -p 5432:5432 -d postgres
```

#### Run "Database Migrations"

After PostgreSQL is running, apply the database schema using Alembic:

```bash
# In the root directory
uv run alembic upgrade head
```

This will create all necessary tables (documents, workflows, policy_decisions, users, etc.) based on the migration files in `alembic/versions/`.

### 1. Backend (The Brain)

The backend powers the AI agents, satellite imagery fetching, and FINOS CDM event generation.

```bash
# In the root directory
uv run uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

*Runs on http://localhost:8000*

**Alternative:** If you've activated the virtual environment, you can run:

```bash
   uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend (The Interface)

The React-based dashboard for traders and risk officers.

```bash
# In the client directory
cd client
npm run dev
```

*Runs on http://localhost:5173*

---

## 📖 Documentation & Resources

- **[📚 Full Documentation](https://docs.creditnexus.com)** - Comprehensive technical documentation, API reference, guides, and architecture details
- **[🏢 Company Site](https://creditnexus.com)** - Learn about our team, market positioning, and business model
- **[🎥 Demo Video](YOUTUBE_URL)** - Watch CreditNexus in action
- **[⚖️ License](LICENSE.md)** - GPL-2 + Rail.md dual license
- **[🤝 Contributing](docs/CONTRIBUTING.md)** - Guidelines for contributing to the project

---

## 🧩 Core Modules

### 1. The Verification Demo (Live Orchestration)
> **Access via: "Verification Demo" in Sidebar**
The primary demonstration of the "Live Wire" workflow.
- **Input**: Upload a PDF Credit Agreement.
- **Process**:
    1.  **Legal Extraction**: Uses LLMs to find "Borrower", "Collateral Address", and "Sustainability Performance Targets (SPTs)".
    2.  **Geocoding**: Converts the address to Lat/Lon coordinates.
    3.  **Satellite Verification**: Fetches Sentinel-2 imagery and runs a TorchGeo ResNet-50 classifier.
    4.  **NDVI Calculation**: Computes the Normalized Difference Vegetation Index to verify crop health.
- **Output**: Determines if the borrower is in **COMPLIANCE** or **BREACH** based on the satellite evidence.

### 2. Ground Truth Dashboard

> **Access via: "Ground Truth" in Sidebar**
The "Production View" for monitoring the entire portfolio of spatially-verified assets.

- **Map View**: See all collateral assets on a global map.
- **Status Indicators**: Green (Compliant), Red (Breach), Yellow (Warning).
- **Asset Creation**: Manually onboard new loans for verification.

### 3. Risk War Room

> **Access via: "Risk War Room" in Sidebar**
A semantic search engine for risk officers, integrated with FDC3.

- **Capabilities**: Ask questions like "Find all vineyards in California with NDVI < 0.6".
- **FDC3**: Listens for context broadcasts from other apps (e.g., when the dashboard detects a breach, the War Room automatically focuses on that asset).

### 4. GreenLens

> **Access via: "GreenLens" in Sidebar**
Visualizes the financial impact (Margin Ratchets) of ESG performance.

- **Dynamic Pricing**: Shows how the loan's interest rate changes based on real-time ESG metrics (e.g., +25bps penalty for missed target).

### 5. Document Parser

> **Access via: "Document Parser" in Top Nav**
The foundational tool for extracting structured data from unstructured PDF legal documents.

> 📖 **Learn More**: See [Documentation - Features](https://docs.creditnexus.com/features) for detailed feature descriptions and [Documentation - Guides](https://docs.creditnexus.com/guides) for step-by-step workflows.

---

## 🔗 System Interoperability (FDC3)

The platform components are designed to work as a "Chain of Command" using the **FDC3 Standard** for seamless data flow:

  1.**Extract**: Use the **Document Parser** to turn a PDF into data. Click "Broadcast to Desktop" to send the loan data out.
  2.**Trade**: The **Trade Blotter** automatically receives this signal and pre-fills an LMA trade ticket.
  3.**Analyze**: **GreenLens** picks up the same signal to show the ESG Margin Ratchet and pricing impact.
  4.**Verify**: The **Verification Demo** runs the "Ground Truth" protocol. When a breach is detected, it broadcasts an updated context.
  5.**Surveil**: The **Risk War Room** listens for these alerts and automatically highlights assets in breach for immediate investigation.

> 📖 **Learn More**: See [Documentation - Architecture](https://docs.creditnexus.com/architecture/overview) for detailed system design and [Documentation - FDC3 Compliance](https://docs.creditnexus.com/compliance/fdc3-compliance) for interoperability standards.

---

## 🖥️ OpenFin Desktop Integration

CreditNexus supports **OpenFin Runtime** for enterprise desktop deployment with FDC3 2.0 interoperability. This enables seamless integration with other financial applications in a desktop environment.

### Prerequisites

1. **OpenFin Runtime** - Install the OpenFin Runtime:
   ```powershell
   # Using OpenFin CLI
   npm install -g @openfin/cli
   ```
   
   Or download from: https://openfin.co/

2. **Node.js & npm** - For running the frontend
3. **Python 3.10+** - For running the backend
4. **.env file** - Already configured in the project root

### Quick Start

**Windows (PowerShell):**
```powershell
# Make sure you're in the project root
.\scripts\run_openfin.ps1
```

**Mac/Linux:**
```bash
cd /path/to/creditnexus
bash scripts/run_openfin.sh
```

This script automatically:
1. Starts the backend server on `http://127.0.0.1:8000`
2. Starts the frontend dev server on `http://localhost:5173`
3. Launches OpenFin with the configured app manifest

**Quick Launch (if services already running):**
```powershell
.\scripts\launch_openfin.ps1
```

### Manual Startup (Advanced)

If you prefer to run services separately, open multiple terminals:

**Terminal 1 - Backend Server:**
```powershell
python scripts/run_dev.py
# Server runs at: http://127.0.0.1:8000
```

**Terminal 2 - Frontend Dev Server:**
```powershell
cd client
npm run dev
# Frontend runs at: http://localhost:5173
```

**Terminal 3 - Launch OpenFin:**
```powershell
# Launch via RVM (no CLI needed - deprecated dependency removed)
.\scripts\launch_openfin.ps1
# Or simply open the manifest URL in your browser:
# http://localhost:8000/openfin/app.json
```

### What Happens

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

### Configuration

The configuration is in `openfin/app.json`:

- **Platform**: creditnexus-platform
- **Default Window**: 1400×900 pixels
- **Entry Point**: http://localhost:8000
- **Security Realm**: creditnexus
- **FDC3 Interop**: 2.0

**Configuration Files:**
- **App Manifest**: `openfin/app.json` - Platform configuration, window layout, FDC3 settings
- **FDC3 Intents**: `openfin/fdc3-intents.json` - Intent declarations and context types
- **Provider Config**: `openfin/provider.json` - Service provider setup

### Troubleshooting

**Backend Won't Start:**
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Install Python dependencies
uv sync
```

**Frontend Won't Start:**
```powershell
# Install Node dependencies
cd client
npm install
```

**OpenFin Won't Launch:**
```powershell
# Verify OpenFin CLI is installed
openfin --version

# Install if needed
npm install -g @openfin/cli
```

**Cannot Connect to Services:**
- Ensure firewall allows localhost traffic
- Check that ports 8000 and 5173 are available
- Verify .env file has correct DATABASE_URL

### Stopping Services

**From the startup script:**
Press `Ctrl+C` in each service window

**Manual cleanup:**
- Close OpenFin applications
- Stop frontend terminal with Ctrl+C
- Stop backend terminal with Ctrl+C

### Production Build

To build the frontend for production:

```powershell
cd client
npm run build
# Output goes to: client/dist
```

Then configure `openfin/app.json` to point to the production build location.

### Development Tips

- **Hot Reload**: Both backend and frontend support hot reload during development
- **FDC3 Messages**: Use FDC3 2.0 for inter-window communication
- **Redux DevTools**: Available in Chrome DevTools for the React app
- **API Debugging**: Backend API available at http://127.0.0.1:8000/docs (OpenAPI)

### Features

- **FDC3 2.0 Interoperability**: Native support for context broadcasting and intent handling
- **Desktop Integration**: Seamless integration with other OpenFin applications
- **Platform Management**: Multi-window platform with workspace support
- **Security**: Configurable security realms and CORS policies

### More Information

- [OpenFin Documentation](https://developers.openfin.co/)
- [FDC3 Specification](https://fdc3.finos.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vite Documentation](https://vitejs.dev/)

---

## 🏗️ Architecture Stack

### Frontend

- **Framework**: React 18 (Vite)
- **Styling**: Tailwind CSS (Premium "FinTech" Dark Mode)
- **Mapping**: Leaflet / React-Leaflet
- **Interoperability**: FDC3 Context API

### Backend

- **API**: FastAPI (Python)
- **Package Manager**: uv (Python 3.11)
- **AI/LLM**: LangChain + OpenAI GPT-4
- **Geospatial**: TorchGeo (Deep Learning), SentinelHub (Satellite Imagery)
- **Standard**: FINOS Common Domain Model (CDM) for trade events
- **Database**: SQLite (Development) / PostgreSQL (Production ready)

### Development Tools

- **Dependencies**: Managed via `pyproject.toml` and `uv.lock`
- **Testing**: `uv run pytest`
- **Code Quality**: ruff, black, mypy (configured in `pyproject.toml`)

> 📖 **Learn More**: See [Documentation - Technical](https://docs.creditnexus.com/architecture) for technology details and [Documentation - Configuration](https://docs.creditnexus.com/getting-started/configuration) for environment setup.

---

## 🎯 The "Verification Demo" Flow

To demonstrate the full power of the system:

  1.Navigate to **"Verification Demo"**.
  2.Drag & Drop the sample **Credit Agreement PDF**.
  3.Watch the logs as the **Legal Agent** extracts the "Napa Valley Vineyards" entity and the "NDVI > 0.75" covenant.
  4.Click **"Securitize & Verify"**.
  5.Observe the **"Ground Truth Protocol"** in action:
    -   Satellite imagery is requested.
    -   TorchGeo classifies the land (e.g., "Annual Crop").
    -   NDVI is calculated (e.g., 0.65).
    -   **Result**: Breach Detected!
  6.  See the **FDC3 Broadcast** trigger updates in the **Risk War Room** (if open) and generate a **Terms Change** event in the CDM ledger.

> 📖 **Learn More**: See [Documentation - Verification Guide](https://docs.creditnexus.com/guides/verification) for detailed verification workflows.

---

## ⚠️ Important Disclosures

### DORA Compliance Disclosure

**Digital Operational Resilience Act (DORA) - European Union Regulation**

This application is provided as a **non-production demonstration**. However, transactions executed through this system may be **live and executory**, with real digital signatures and legal implications for all signees based on system configuration. Users are responsible for understanding the legal and regulatory implications of their use of this system.

> 📖 **Learn More**: See [Documentation - DORA Disclosure](https://docs.creditnexus.com/compliance/dora-disclosure) for complete compliance information.

### Compliance Standards

- **FDC3 2.0**: Full desktop interoperability compliance - [Documentation](https://docs.creditnexus.com/compliance/fdc3-compliance)
- **OpenFin**: Native integration support - [Documentation](https://docs.creditnexus.com/compliance/openfin-compliance)
- **FINOS CDM**: Complete Common Domain Model compliance - [Documentation](https://docs.creditnexus.com/compliance/cdm-compliance)
- **DORA**: European cybersecurity regulation awareness - [Documentation](https://docs.creditnexus.com/compliance/dora-disclosure)
- **Policy Engine**: Real-time compliance enforcement - [Documentation](https://docs.creditnexus.com/compliance/policy-compliance)

---

## 👥 Our Team

Our team brings over **20 years of combined experience** in the financial industry:

- **Joseph Pollack** - Chief Information Officer (Strategic technology leadership)
- **Biniyam Ajew** - Senior Developer (Full-stack development and system architecture)
- **Boris Li** - Junior Developer (10 years at Citibank and Mastercard in payment systems, banking operations, and financial technology)

> 📖 **Learn More**: See [Company Site - Team](https://creditnexus.com) for detailed team information.

---

*Built by the CreditNexus Team - "Trust, but Verify (from Space)."*
