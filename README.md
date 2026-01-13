# Algorithmic Nature-Finance Platform (CreditNexus)

**"Where Legal Text Meets Ground Truth"**

CreditNexus is a next-generation financial operating system that bridges the gap between **Sustainabiity-Linked Loans (Legal Contracts)** and **Physical Reality (Satellite Data)**. It uses AI agents to extract covenants from PDF agreements and orchestrates "Ground Truth" verification using geospatial deep learning.

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
uv run alembic upgrade heads
```

**Note:** Use `heads` instead of `head` because this project has multiple migration branches. If you encounter "Multiple head revisions" errors, `alembic upgrade heads` will apply all migration heads.

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

---

## 🔗 System Interoperability (FDC3)

The platform components are designed to work as a "Chain of Command" using the **FDC3 Standard** for seamless data flow:

  1.**Extract**: Use the **Document Parser** to turn a PDF into data. Click "Broadcast to Desktop" to send the loan data out.
  2.**Trade**: The **Trade Blotter** automatically receives this signal and pre-fills an LMA trade ticket.
  3.**Analyze**: **GreenLens** picks up the same signal to show the ESG Margin Ratchet and pricing impact.
  4.**Verify**: The **Verification Demo** runs the "Ground Truth" protocol. When a breach is detected, it broadcasts an updated context.
  5.**Surveil**: The **Risk War Room** listens for these alerts and automatically highlights assets in breach for immediate investigation.

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

### Optional Features: Twilio SMS Integration

CreditNexus supports Twilio SMS integration for loan recovery notifications. To enable this feature:

1. **Create a `.env` file** in the project root (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

2. **Configure Twilio credentials** in `.env`:
   ```env
   TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
   TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
   TWILIO_PHONE_NUMBER=+12345678900
   ```

3. **Install Twilio Python SDK**:
   ```bash
   uv add twilio
   ```

**Development Note**: If Twilio credentials are not configured, the backend will start with a warning and Twilio webhook validation will be disabled. This allows for local development without requiring Twilio setup.

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

---

*Built by the CreditNexus Team - "Trust, but Verify (from Space)."*
