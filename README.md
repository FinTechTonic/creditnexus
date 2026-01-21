# CreditNexus

**"Price & Create Structured Financial Products"**

[![Documentation](https://img.shields.io/badge/📖-Read%20The%20Docs-blue?style=flat-square)](https://tonic-ai.mintlify.app)
[![Company Site](https://img.shields.io/badge/Company%20Site-Visit-green?style=flat-square)](https://josephrp.github.io/creditnexus)
[![YouTube Demo](https://img.shields.io/badge/YouTube-Demo-red?style=flat-square&logo=youtube)](https://www.youtube.com/watch?v=jg25So46Wks)

[![Enforced](https://img.shields.io/badge/Enforced-Sanctions-red?style=flat-square)](https://tonic-ai.mintlify.app/compliance/sanctions)
[![Enforced](https://img.shields.io/badge/Enforced-BASEL%20II-blue?style=flat-square)](https://tonic-ai.mintlify.app/compliance/basel)
[![Enforced](https://img.shields.io/badge/Enforced-Credit%20Risk-orange?style=flat-square)](https://tonic-ai.mintlify.app/compliance/credit-risk)
[![Enforced](https://img.shields.io/badge/Enforced-ESG-green?style=flat-square)](https://tonic-ai.mintlify.app/compliance/esg)
[![Enforced](https://img.shields.io/badge/Enforced-SDG-green?style=flat-square)](https://tonic-ai.mintlify.app/compliance/sdg)

[![A Priori](https://img.shields.io/badge/A%20Priori-Policy%20Enforcement-purple?style=flat-square)](https://tonic-ai.mintlify.app/features/policy-engine)
[![FDC3](https://img.shields.io/badge/FDC3-OpenFin-blue?style=flat-square)](https://tonic-ai.mintlify.app/compliance/fdc3-compliance)
[![DORA](https://img.shields.io/badge/DORA-Compliant-green?style=flat-square)](https://tonic-ai.mintlify.app/compliance/dora-disclosure)
[![FINOS CDM](https://img.shields.io/badge/FINOS-CDM-blue?style=flat-square)](https://tonic-ai.mintlify.app/compliance/cdm-compliance)
[![GDPR](https://img.shields.io/badge/GDPR-Compliant-green?style=flat-square)](https://tonic-ai.mintlify.app/compliance/gdpr-compliance)
[![AI:Local](https://img.shields.io/badge/AI-Local%20Ready-orange?style=flat-square)](https://tonic-ai.mintlify.app/getting-started/configuration#llm-provider-configuration)


[![Security](https://img.shields.io/badge/Security-Passed-brightgreen?style=flat-square)](https://github.com/josephrp/creditnexus/actions/workflows/security.yml)
[![SSL](https://img.shields.io/badge/SSL-Enabled-brightgreen?style=flat-square)](https://tonic-ai.mintlify.app/compliance/security)
[![Encryption](https://img.shields.io/badge/Encryption-At--Rest-brightgreen?style=flat-square)](https://tonic-ai.mintlify.app/compliance/security)
[![Payments](https://img.shields.io/badge/Payments-X402-blue?style=flat-square)](https://tonic-ai.mintlify.app/features/payments)
[![Green Finance](https://img.shields.io/badge/Green-Finance-green?style=flat-square)](https://tonic-ai.mintlify.app/features/green-finance)
[![Join us on Discord](https://img.shields.io/discord/1109943800132010065?label=Discord&logo=discord&style=flat-square)](https://discord.gg/qdfnvSPcqP) 

CreditNexus is a next-generation financial operating system that bridges the gap between **Sustainabiity-Linked Loans (Legal Contracts)** and **Physical Reality (Satellite Data)**. It uses AI agents to extract covenants from PDF agreements and orchestrates "Ground Truth" verification using geospatial deep learning.

> 📚 **[Full Documentation](https://tonic-ai.mintlify.app)** | 🏢 **[Company Site](https://josephrp.github.io/creditnexus)** | 🎥 **[Demo Video](https://www.youtube.com/watch?v=jg25So46Wks)**

## 🌐 Connect With Us

- **Twitter/X**: [@josephpollack](https://x.com/josephpollack)
- **GitHub**: [@fintechtonic](https://github.com/fintechtonic)
- **HuggingFace**: [@tonic](https://hf.co/tonic)
- **Discord**: [Join our community](https://discord.gg/7YS4Cz2Deq) - [![Discord Online](https://img.shields.io/discord/INVITE_ID?label=Discord&logo=discord&logoColor=white&style=flat-square)](https://discord.gg/7YS4Cz2Deq)


---

## 📊 Platform Scale & Capabilities

CreditNexus is built with enterprise-scale architecture and comprehensive feature coverage:

### Component Statistics

- **215+ Prompt Templates** - AI prompts across 16 files covering LMA-compliant clause generation, industry-specific templates, and multi-scenario support
- **11 Specialized Agents** - AI agents for document analysis, satellite verification, classification, research, and workflow automation
- **121 Policy Rules** - Regulatory compliance rules across 21 files covering MiCA, Basel III, FATF, ESG, and green finance
- **94 Tool Modules** - Service modules, utilities, and LangChain integration chains for comprehensive functionality
- **76 Data Models** - Pydantic models ensuring type safety and FINOS CDM compliance across all data structures
- **54 Database Tables** - SQLAlchemy 2.0 models covering users, documents, workflows, deals, payments, and analytics
- **147 API Endpoints** - RESTful endpoints providing comprehensive programmatic access to all platform features
- **100% CDM Compliant** - Full FINOS Common Domain Model compliance ensuring interoperability with financial systems

### Platform Architecture Highlights

**AI & Automation:**
- 215+ prompt templates for consistent AI behavior
- 11 specialized agents for complex workflows
- Multi-provider LLM support (OpenAI, vLLM, HuggingFace)
- 20 LangChain integration chains

**Compliance & Policy:**
- 121 policy rules across 8 categories
- Real-time policy enforcement engine
- CDM-compliant event generation
- Three-tier decision system (ALLOW/BLOCK/FLAG)

**Data & Integration:**
- 76 Pydantic models for type safety
- 54 database tables with SQLAlchemy 2.0
- 147 API endpoints for programmatic access
- Full CDM standardization

> 📖 **Learn More**: See [Platform Statistics Documentation](https://tonic-ai.mintlify.app/architecture/platform-statistics) for detailed component breakdown and capabilities assessment.

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

<details>
<summary><b>0.5. External Service Configuration (Click to expand)</b></summary>

<br>

<details>
<summary><b>DigiSigner Webhook Setup (for Digital Signatures)</b></summary>

CreditNexus integrates with DigiSigner for digital signature workflows. To enable webhook notifications:

1. **Get your DigiSigner API key** from your DigiSigner account settings
2. **Configure webhook callbacks** in DigiSigner:
   - Log in to your DigiSigner account
   - Navigate to **Account Settings → API Settings**
   - Set both callback URLs to: `https://your-domain.com/api/signatures/webhook`
     - "Signature Request Completed" Callback URL
     - "Document Signed" Callback URL

**For Local Development:**

To test webhooks locally, use a tunnel service to expose your local server:

**Option 1: Using localtunnel (Recommended for quick testing)**

```bash
# Install and run localtunnel
npx localtunnel --port 8000
# Output: your url is: https://icy-chairs-warn.loca.lt
```

Then configure the webhook URL in DigiSigner:
- Set both callback URLs to: `https://icy-chairs-warn.loca.lt/api/signatures/webhook`
  - "Signature Request Completed" Callback URL
  - "Document Signed" Callback URL

**Option 2: Using ngrok**

```bash
# Install ngrok (if not already installed)
# Windows: choco install ngrok
# macOS: brew install ngrok
# Linux: Download from https://ngrok.com/download

# Start tunnel
ngrok http 8000
# Use the HTTPS URL shown (e.g., https://abc123.ngrok.io)
```

Then configure the webhook URL in DigiSigner:
- Set both callback URLs to: `https://your-ngrok-url.ngrok.io/api/signatures/webhook`

**Important Notes:**
- Ensure your local server is running on port 8000 before starting the tunnel
- The tunnel URL changes each time you restart localtunnel (ngrok free tier also changes)
- Update DigiSigner webhook URLs whenever the tunnel URL changes
- For production, use a stable HTTPS domain instead of tunnels

**Environment Variables:**

Copy `.env.example` to `.env` and configure:
```env
DIGISIGNER_API_KEY=your_api_key_here
DIGISIGNER_BASE_URL=https://api.digisigner.com/v1
DIGISIGNER_WEBHOOK_SECRET=your_webhook_secret_here  # Optional but recommended
```

> 📖 **Full Setup Guide**: See [DigiSigner Setup Guide](https://tonic-ai.mintlify.app/guides/digisigner-setup) for detailed configuration, troubleshooting, and security considerations.

</details>

<details>
<summary><b>Twilio Setup (for Loan Recovery)</b></summary>

CreditNexus integrates with Twilio for SMS and voice communication in loan recovery workflows. To enable:

1. **Create a Twilio account** at https://www.twilio.com/
2. **Get your credentials** from the Twilio Console:
   - Account SID
   - Auth Token
   - Phone Number (with SMS/Voice capabilities)

**Environment Variables:**

Copy `.env.example` to `.env` and add:
```env
TWILIO_ENABLED=true
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890  # E.164 format
TWILIO_SMS_ENABLED=true
TWILIO_VOICE_ENABLED=true
TWILIO_WEBHOOK_URL=https://your-domain.com/api/twilio/webhook/status
```

**Webhook Configuration:**
Configure webhook URLs in Twilio Console:
- SMS Status: `https://your-domain.com/api/twilio/webhook/sms`
- Voice Status: `https://your-domain.com/api/twilio/webhook/voice`
- Status Callback: `https://your-domain.com/api/twilio/webhook/status`

> 📖 **Full Setup Guide**: See [Loan Recovery Feature Documentation](https://tonic-ai.mintlify.app/features/recovery) for complete details and [Twilio Setup Guide](https://tonic-ai.mintlify.app/guides/twilio-setup) for configuration.

</details>

<details>
<summary><b>SentinelHub Setup (for Satellite Imagery)</b></summary>

CreditNexus uses SentinelHub for satellite imagery access. To enable:

1. **Create a SentinelHub account** at https://www.sentinel-hub.com/
2. **Generate OAuth credentials** in your account settings
3. **Copy `.env.example` to `.env` and add:**
```env
SENTINELHUB_KEY=your_client_id_here
SENTINELHUB_SECRET=your_client_secret_here
```

> 📖 **Configuration Guide**: See [Documentation - Configuration](https://tonic-ai.mintlify.app/getting-started/configuration#sentinelhub-configuration) for detailed setup.

</details>

<details>
<summary><b>MetaMask/Blockchain Setup (for Securitization)</b></summary>

CreditNexus uses Base network for blockchain operations. To configure:

1. **Add Base network to MetaMask** (see detailed guide below)
2. **Configure environment variables:**
```env
X402_NETWORK_RPC_URL=https://mainnet.base.org  # or https://sepolia.base.org for testnet
USDC_TOKEN_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913  # Base Mainnet USDC
```

> 📖 **Full Setup Guide**: See [MetaMask Setup Guide](https://tonic-ai.mintlify.app/guides/metamask-setup) for complete network configuration, contract addresses, and troubleshooting.

</details>

<details>
<summary><b>Companies House API (for UK Regulatory Filings)</b></summary>

For automated UK charge filings (MR01), configure:

1. **Register for free API access** at https://developer.company-information.service.gov.uk/
2. **Copy `.env.example` to `.env` and add:**
```env
COMPANIES_HOUSE_API_KEY=your_api_key_here
```

> 📖 **Environment Configuration**: See [Configuration Guide](https://tonic-ai.mintlify.app/getting-started/configuration) for all available environment variables.

</details>

<details>
<summary><b>Alpaca (Trading & Stock-Prediction Market Data)</b></summary>

Alpaca provides live/paper trading and historical bars for stock prediction and backtesting.

1. **Create an account** at https://alpaca.markets/ and get API keys (paper and/or live).
2. **Copy `.env.example` to `.env` and add:**
```env
ALPACA_API_KEY=your_key
ALPACA_API_SECRET=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets   # or https://api.alpaca.markets for live
ALPACA_DATA_ENABLED=true   # Use Alpaca for historical bars when set (else yahooquery)
```
3. **Stock prediction**: Enable `STOCK_PREDICTION_ENABLED=true` to use daily/hourly/15min predictions and backtests. With `ALPACA_DATA_ENABLED=true`, OHLCV and trading quotes prefer Alpaca.

> 📖 **Details**: See [dev/environment.md](dev/environment.md) for Alpaca and related cache TTLs.

</details>

<details>
<summary><b>Polymarket (Prediction Markets / SFP)</b></summary>

Polymarket-style prediction markets for Structured Financial Products (SFPs).

1. **Enable the feature** and set CLOB/Gamma/Data URLs if using Polymarket’s public APIs.
2. **Copy `.env.example` to `.env` and add (as needed):**
```env
POLYMARKET_ENABLED=true
POLYMARKET_API_URL=https://clob.polymarket.com
POLYMARKET_API_KEY=optional_clob_key
POLYMARKET_NETWORK=polygon
POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com
POLYMARKET_DATA_API_URL=https://data-api.polymarket.com
POLYMARKET_SURVEILLANCE_ENABLED=false
POLYMARKET_PUBLISH_EXTERNAL=false
```
3. **Cross-chain (optional):** For outcome tokens on L2s, set `CROSS_CHAIN_ENABLED=true`, `POLYMARKET_BRIDGE_API_URL`, `OUTCOME_TOKEN_CHAIN_ID`, `SFP_OUTCOME_TOKEN_CONTRACT`.

> 📖 **Details**: See [dev/environment.md](dev/environment.md) for all Polymarket and cross-chain options.

</details>

<details>
<summary><b>Data Cache & New Services (Polygon, Alpha Vantage, Serper, Tavily, Cache TTLs)</b></summary>

Unified caching for market data, tools, and external APIs. TTLs are configurable via environment variables.

- **Cache TTLs (seconds):** `CACHE_TTL_OHLCV_1D`, `CACHE_TTL_OHLCV_1H`, `CACHE_TTL_OHLCV_15M`, `CACHE_TTL_SNAPSHOT`, `CACHE_TTL_FUNDAMENTAL`, `CACHE_TTL_NEWS`, `CACHE_TTL_WEB_SEARCH`, `CACHE_TTL_TRADING_QUOTE`, `CACHE_TTL_BACKTEST`. Used by `app.core.data_cache` for OHLCV, snapshots, fundamentals, news, web search, Alpaca quotes, and backtest results.
- **LangAlpha / Quantitative:** `POLYGON_API_KEY` (Polygon.io), `ALPHA_VANTAGE_API_KEY`, `TAVILY_API_KEY`, `TICKERTICK_API_KEY` (optional), `SERPER_API_KEY` (web search).
- **Web search:** `SERPER_API_KEY`, `WEB_SEARCH_RATE_LIMIT`, `WEB_SEARCH_ANALYTICS_DIR`.

> 📖 **Full list**: See [dev/environment.md](dev/environment.md) for defaults and descriptions.

</details>

<details>
<summary><b>0.6. Smart Contract Deployment (Optional - for Securitization Features)</b></summary>

CreditNexus includes smart contracts for securitization workflows. To enable blockchain features:

#### Prerequisites

1. **Node.js & npm** - For compiling and deploying contracts
2. **Hardhat** - Build system (installed automatically)
3. **Base Network RPC Access** (or local Hardhat) - For contract deployment

#### Quick Setup

**1. Install Contract Dependencies:**

```bash
cd contracts
npm install
```

**2. Compile Contracts:**

```bash
cd contracts
npm run compile
```

This generates contract ABIs and bytecode in `contracts/artifacts/`.

**3. Deploy Contracts**

**Local development (no private key):**

- **One-off in-memory:** `npm run deploy:local` — uses built-in Hardhat accounts; no `.env` keys. Chain is ephemeral.
- **Persistent node:** run `npm run node` in one terminal, then `npm run deploy:localhost` in another. Point the app at `http://127.0.0.1:8545` and add the printed contract addresses to `.env`.

See [`contracts/README.md`](contracts/README.md) for full local deployment steps.

**Base Sepolia (Testnet) or Base Mainnet (requires `PRIVATE_KEY`):**

Set `PRIVATE_KEY` or `BLOCKCHAIN_DEPLOYER_PRIVATE_KEY` in the **project root** `.env` (or `contracts/.env`). Optional: `BASE_SEPOLIA_RPC_URL`, `BASE_RPC_URL`, `BASESCAN_API_KEY`.

```bash
cd contracts

# Testnet
npm run deploy:base-sepolia

# Mainnet
npm run deploy:base
```

**4. Update Environment Variables:**

After deployment, add the contract addresses to your **project root** `.env` (copy from `.env.example` first if needed):

```env
SECURITIZATION_NOTARIZATION_CONTRACT=0x...
SECURITIZATION_TOKEN_CONTRACT=0x...
SECURITIZATION_PAYMENT_ROUTER_CONTRACT=0x...
X402_NETWORK_RPC_URL=https://mainnet.base.org   # or https://sepolia.base.org for testnet, or http://127.0.0.1:8545 for local
```

#### Auto-Deployment (Development)

If you don't manually deploy contracts, CreditNexus can auto-deploy them on first use:

1. Copy `.env.example` to `.env` and set `BLOCKCHAIN_AUTO_DEPLOY=true`
2. Ensure `X402_NETWORK_RPC_URL` is configured
3. Contracts will be automatically deployed when first accessed

**Note:** Auto-deployment requires:
- Valid RPC connection (Base, Base Sepolia, or local Hardhat at `http://127.0.0.1:8545`; for local, run `npm run node` in `contracts/` first)
- Deployer account with sufficient ETH for gas (for local without a key, use manual `npm run deploy:localhost` instead; see `contracts/README.md`)
- Compiled contracts (run `npm run compile` first)

#### Manual Deployment (Production)

For production, manually deploy contracts and set addresses:

1. Deploy contracts using Hardhat (see steps above)
2. Copy `.env.example` to `.env` and set contract addresses:
   ```env
   SECURITIZATION_NOTARIZATION_CONTRACT=0x...
   SECURITIZATION_TOKEN_CONTRACT=0x...
   SECURITIZATION_PAYMENT_ROUTER_CONTRACT=0x...
   BLOCKCHAIN_AUTO_DEPLOY=false  # Disable auto-deployment in production
   ```

#### Contract Verification

To verify contracts on BaseScan:

```bash
cd contracts
npx hardhat verify --network base <CONTRACT_ADDRESS> [CONSTRUCTOR_ARGS]
```

**Example:**
```bash
# Verify SecuritizationToken
npx hardhat verify --network base 0x... 

# Verify SecuritizationPaymentRouter (requires token address as constructor arg)
npx hardhat verify --network base 0x... 0x[TOKEN_ADDRESS]
```

> 📖 **Smart Contract Documentation**: See [`contracts/README.md`](contracts/README.md) for detailed contract specifications and [Securitization Feature Documentation](https://tonic-ai.mintlify.app/features/securitization) for integration details.

</details>

</details>

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

- **[📚 Full Documentation](https://tonic-ai.mintlify.app)** - Comprehensive technical documentation, API reference, guides, and architecture details
- **[🏢 Company Site](https://josephrp.github.io/creditnexus)** - Learn about our team, market positioning, and business model
- **[🎥 Demo Video](https://www.youtube.com/watch?v=jg25So46Wks)** - Watch CreditNexus in action
- **[⚖️ License](LICENSE.md)** - GPL-2 + Rail.md dual license
- **[🤝 Contributing](docs/CONTRIBUTING.md)** - Guidelines for contributing to the project
- **[🔧 Environment Configuration](https://tonic-ai.mintlify.app/getting-started/configuration)** - Complete list of environment variables and configuration options
- **[✍️ DigiSigner Webhook Setup](https://tonic-ai.mintlify.app/guides/digisigner-setup)** - Guide for configuring DigiSigner webhooks for digital signatures
- **[📜 Smart Contracts](contracts/README.md)** - Solidity contract documentation and specifications
- **[🏗️ Securitization Feature](https://tonic-ai.mintlify.app/features/securitization)** - Complete securitization workflow documentation

---

<details>
<summary><b>🧩 Core Modules (Click to expand)</b></summary>

<br>

<details>
<summary><b>1. The Verification Demo (Live Orchestration)</b></summary>

> **Access via: "Verification Demo" in Sidebar**
The primary demonstration of the "Live Wire" workflow.
- **Input**: Upload a PDF Credit Agreement.
- **Process**:
    1.  **Legal Extraction**: Uses LLMs to find "Borrower", "Collateral Address", and "Sustainability Performance Targets (SPTs)".
    2.  **Geocoding**: Converts the address to Lat/Lon coordinates.
    3.  **Satellite Verification**: Fetches Sentinel-2 imagery and runs a TorchGeo ResNet-50 classifier.
    4.  **NDVI Calculation**: Computes the Normalized Difference Vegetation Index to verify crop health.
- **Output**: Determines if the borrower is in **COMPLIANCE** or **BREACH** based on the satellite evidence.

</details>

<details>
<summary><b>2. Ground Truth Dashboard</b></summary>

> **Access via: "Ground Truth" in Sidebar**
The "Production View" for monitoring the entire portfolio of spatially-verified assets.

- **Map View**: See all collateral assets on a global map.
- **Status Indicators**: Green (Compliant), Red (Breach), Yellow (Warning).
- **Asset Creation**: Manually onboard new loans for verification.

</details>

<details>
<summary><b>3. Risk War Room</b></summary>

> **Access via: "Risk War Room" in Sidebar**
A semantic search engine for risk officers, integrated with FDC3.

- **Capabilities**: Ask questions like "Find all vineyards in California with NDVI < 0.6".
- **FDC3**: Listens for context broadcasts from other apps (e.g., when the dashboard detects a breach, the War Room automatically focuses on that asset).

</details>

<details>
<summary><b>4. GreenLens</b></summary>

> **Access via: "GreenLens" in Sidebar**
Visualizes the financial impact (Margin Ratchets) of ESG performance.

- **Dynamic Pricing**: Shows how the loan's interest rate changes based on real-time ESG metrics (e.g., +25bps penalty for missed target).

</details>

<details>
<summary><b>5. Document Parser</b></summary>

> **Access via: "Document Parser" in Top Nav**
The foundational tool for extracting structured data from unstructured PDF legal documents.

> 📖 **Learn More**: See [Documentation - Features](https://tonic-ai.mintlify.app/features) for detailed feature descriptions and [Documentation - Guides](https://tonic-ai.mintlify.app/guides) for step-by-step workflows.

</details>

<details>
<summary><b>6. Loan Recovery System</b></summary>

> **Access via: "Loan Recovery" in Sidebar**
Automated loan default detection and recovery workflow with Twilio integration.

- **Default Detection**: Automatic detection of payment defaults and covenant breaches
- **Recovery Actions**: SMS and voice communication via Twilio
- **Borrower Contact Management**: Centralized contact information management
- **CDM Events**: All recovery actions generate CDM-compliant events

> 📖 **Learn More**: See [Loan Recovery Feature Documentation](https://tonic-ai.mintlify.app/features/recovery) for complete details and [Twilio Setup Guide](https://tonic-ai.mintlify.app/guides/twilio-setup) for configuration.

</details>

<details>
<summary><b>7. Payment Systems (x402 Protocol)</b></summary>

> **Access via: Securitization and Trade workflows**
Blockchain-based payment processing using x402 protocol and USDC stablecoin.

- **x402 Protocol**: Standardized payment request/response flow
- **USDC Payments**: Stablecoin payments on Base network
- **MetaMask Integration**: Wallet-based payment authorization
- **Payment Events**: CDM-compliant payment event generation

> 📖 **Learn More**: See [MetaMask Setup Guide](https://tonic-ai.mintlify.app/guides/metamask-setup) for network setup.

</details>

<details>
<summary><b>8. Notarization (Blockchain-Based)</b></summary>

> **Access via: Securitization Workflow**
Blockchain-based document notarization using smart contracts.

- **Smart Contract Notarization**: SecuritizationNotarization contract on Base network
- **MetaMask Signing**: Wallet-based signature verification
- **Immutable Records**: All notarizations stored on-chain
- **Multi-Party Signing**: Support for multiple signers

> 📖 **Learn More**: See [Securitization Feature Documentation](https://tonic-ai.mintlify.app/features/securitization) for implementation details.

</details>

<details>
<summary><b>9. Digital Signing (DigiSigner Integration)</b></summary>

> **Access via: Document workflows**
Digital signature workflows with DigiSigner integration and webhook notifications.

- **DigiSigner Integration**: Professional e-signature service
- **Webhook Notifications**: Real-time signature status updates
- **Multi-Document Signing**: Batch document signing workflows
- **Legal Validity**: Legally binding digital signatures

> 📖 **Learn More**: See [DigiSigner Setup Guide](https://tonic-ai.mintlify.app/guides/digisigner-setup) for setup guide.

</details>

<details>
<summary><b>10. Dealflow Management</b></summary>

> **Access via: "Deals" in Sidebar**
Comprehensive deal tracking and collaboration platform.

- **Deal Dashboard**: Portfolio overview with filtering and search
- **Deal Timeline**: Visual timeline of deal events and milestones
- **Deal Notes**: Collaborative note-taking and comments
- **Deal Detail View**: Comprehensive deal information and documents

> 📖 **Learn More**: See [Documentation - Features](https://tonic-ai.mintlify.app/features/dealflow-management) for detailed workflows.

</details>

<details>
<summary><b>11. One-Click Audit Reports</b></summary>

> **Access via: "Auditor" in Sidebar**
Automated audit report generation with CDM event exploration.

- **Report Generation**: Automated report generation from audit logs
- **CDM Event Explorer**: Browse and filter CDM events
- **Policy Decisions Explorer**: Review policy evaluation decisions
- **Export Functionality**: Export reports in multiple formats (PDF, CSV, JSON)

> 📖 **Learn More**: See [Documentation - Features](https://tonic-ai.mintlify.app/features/audit-reports) for report generation guide.

</details>

<details>
<summary><b>12. Securitization Workflow</b></summary>

> **Access via: "Securitization" in Sidebar**
Complete securitization workflow from pool creation to token minting.

- **Pool Creation**: Create securitization pools with asset selection
- **Notarization**: Blockchain-based pool notarization
- **Tranche Minting**: ERC-721 tranche token creation
- **Payment Distribution**: Automated payment waterfall processing

> 📖 **Learn More**: See [Securitization Feature Documentation](https://tonic-ai.mintlify.app/features/securitization) for complete workflow.

</details>

<details>
<summary><b>13. AI Agent Workflows</b></summary>

> **Access via: "Agent Dashboard" in Sidebar or Document Digitizer Chatbot**
Three powerful AI agent workflows for quantitative analysis, research, and business intelligence.

<details>
<summary><b>LangAlpha: Quantitative Analysis</b></summary>

Multi-agent system for quantitative financial analysis:
- **Company Analysis**: Financial health, market position, investment potential
- **Market Analysis**: Trends, sectors, economic indicators
- **Loan Application Analysis**: Credit risk, financial ratios, cash flow projections
- **Multi-Agent Orchestration**: Coordinator, planner, supervisor, researcher, market, coder, reporter, analyst
- **Real-Time Progress**: Server-Sent Events (SSE) for streaming updates

**Configuration Required:**
- `POLYGON_API_KEY`: Polygon.io API key for market data
- `ALPHA_VANTAGE_API_KEY`: Alpha Vantage API key for fundamentals
- `SERPER_API_KEY`: Serper API key for web search (optional)

</details>

<details>
<summary><b>DeepResearch: Iterative Web Research</b></summary>

Comprehensive web research with knowledge accumulation:
- **Multi-Stage Research**: Search → Read → Answer → Reflect → Iterate
- **Knowledge Accumulation**: Builds comprehensive knowledge bases
- **Source Citations**: Full citation tracking and source references
- **CDM Event Integration**: Research queries generate CDM-compliant events

**Configuration Required:**
- `SERPER_API_KEY`: Serper API key for Google search (optional, uses WebSearchService fallback)

</details>

<details>
<summary><b>PeopleHub: Business Intelligence</b></summary>

Business intelligence and psychometric analysis:
- **Psychometric Analysis**: Big Five personality traits, risk tolerance, decision-making style
- **LinkedIn Integration**: Automated profile fetching and analysis
- **Web Research**: Comprehensive web research with content scraping
- **Credit Assessment**: Automated creditworthiness evaluation

**Configuration Required:**
- No additional API keys (uses existing WebSearchService and LLM configuration)

</details>

**Agent Dashboard Features:**
- Unified view of all agent results
- Search and filter by agent type, status, or date
- Detailed result views with export (Markdown, PDF, JSON)
- Statistics and usage analytics

> 📖 **Learn More**: See [Agent Workflows Documentation](https://tonic-ai.mintlify.app/features/agent-workflows) for complete details and [Configuration Guide](https://tonic-ai.mintlify.app/getting-started/configuration#agent-workflows-configuration) for setup.

</details>

</details>

---

<details>
<summary><b>🔗 System Interoperability (FDC3) (Click to expand)</b></summary>

<br>

CreditNexus is **fully compliant with FDC3 2.0** standards, enabling seamless desktop interoperability with other financial applications. The platform components are designed to work as a "Chain of Command" using the **FDC3 Standard** for seamless data flow:

  1.**Extract**: Use the **Document Parser** to turn a PDF into data. Click "Broadcast to Desktop" to send the loan data out.
  2.**Trade**: The **Trade Blotter** automatically receives this signal and pre-fills an LMA trade ticket.
  3.**Analyze**: **GreenLens** picks up the same signal to show the ESG Margin Ratchet and pricing impact.
  4.**Verify**: The **Verification Demo** runs the "Ground Truth" protocol. When a breach is detected, it broadcasts an updated context.
  5.**Surveil**: The **Risk War Room** listens for these alerts and automatically highlights assets in breach for immediate investigation.

### FDC3 2.0 Compliance Features

- ✅ **App Directory API**: Served at `/api/fdc3/apps` for OpenFin Workspace discovery
- ✅ **Context Types**: All custom contexts use `finos.creditnexus.*` namespace (FDC3 2.0 compliant)
- ✅ **Intent Handling**: Full support for intent listeners and raisers
- ✅ **App Channels**: Custom channels for workflow, extraction, and portfolio events
- ✅ **Error Handling**: Robust validation and retry logic for reliable broadcasting
- ✅ **Native OpenFin Integration**: Uses built-in FDC3 2.0 API (no deprecated services)

**Context Types Supported:**
- `finos.creditnexus.loan` - Loan data context
- `finos.creditnexus.agreement` - Credit agreement context
- `finos.creditnexus.document` - Document extraction context
- `finos.creditnexus.portfolio` - Portfolio context
- `finos.creditnexus.workflow` - Workflow link sharing context
- `finos.creditnexus.approvalResult` - Approval workflow results
- `finos.creditnexus.esgData` - ESG analytics data
- `finos.cdm.landUse` - Land use classification
- `finos.cdm.greenFinanceAssessment` - Green finance assessment

> 📖 **Learn More**: See [Documentation - Architecture](https://tonic-ai.mintlify.app/architecture/overview) for detailed system design and [Documentation - FDC3 Compliance](https://tonic-ai.mintlify.app/compliance/fdc3-compliance) for interoperability standards.

</details>

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
4. **.env file** - Copy from `.env.example` in the project root and configure

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

<details>
<summary><b>Manual Startup (Advanced) (Click to expand)</b></summary>

<br>

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
# Launch via RVM (no CLI needed!)
.\scripts\launch_openfin.sh
# Or simply open the manifest URL in your browser:
# http://localhost:8000/openfin/app.json
```

**Windows (Git Bash/MINGW64):**
```bash
# Launch via RVM
./scripts/launch_openfin.sh
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

### After the Script Runs

Once `launch_openfin.sh` completes successfully, here's what happens:

1. **OpenFin Runtime Launch**:
   - If this is your first time, OpenFin Runtime will download automatically (this may take a few minutes)
   - The OpenFin Runtime window will appear
   - You'll see the CreditNexus platform loading

2. **Application Window Opens**:
   - A new window (1400×900 pixels) will open with the CreditNexus application
   - The application loads from `http://localhost:8000`
   - You should see the CreditNexus login/interface

3. **FDC3 Integration Active**:
   - FDC3 2.0 API is available via `window.fdc3`
   - App Directory is accessible at `http://localhost:8000/api/fdc3/apps`
   - Context broadcasting and intent handling are ready

4. **What You Can Do Next**:
   - **Login/Register**: Create an account or login to access features
   - **Test FDC3**: Open multiple windows and test context broadcasting between them
   - **Use Document Parser**: Upload a credit agreement PDF and click "Broadcast to Desktop" to test FDC3 context sharing
   - **Open Trade Blotter**: It will automatically receive FDC3 contexts from Document Parser
   - **Test GreenLens**: It listens for FDC3 contexts to show ESG analytics
   - **Verify Integration**: Check that other FDC3-compliant apps can discover CreditNexus via the App Directory

5. **First Launch Notes**:
   - OpenFin Runtime download: On first launch, OpenFin may take 1-2 minutes to download and install
   - Security prompts: You may see security prompts - allow OpenFin to run
   - Port access: Ensure ports 8000 and 5173 are not blocked by firewall

6. **Verifying Everything Works**:
   ```bash
   # Check FDC3 App Directory is accessible
   curl http://localhost:8000/api/fdc3/apps
   
   # Should return JSON with CreditNexus app definition
   ```

7. **If OpenFin Doesn't Launch**:
   - Check the script output for error messages
   - Verify backend is running: `curl http://localhost:8000/api/health`
   - Verify manifest is accessible: `curl http://localhost:8000/openfin/app.json`
   - Try opening the manifest URL directly in your browser: `http://localhost:8000/openfin/app.json`

### Configuration

The configuration is in `openfin/app.json`:

- **Platform**: creditnexus-platform
- **Default Window**: 1400×900 pixels
- **Entry Point**: http://localhost:8000
- **Security Realm**: creditnexus
- **FDC3 Interop**: 2.0

**Configuration Files:**
- **App Manifest**: `openfin/app.json` - Platform configuration, window layout, FDC3 settings
- **FDC3 Intents**: `openfin/fdc3-intents.json` - Intent declarations and context types (served at `/api/fdc3/apps`)
- **Provider Config**: `openfin/provider.json` - Service provider setup (uses native FDC3 2.0 API)

**FDC3 App Directory:**
The FDC3 App Directory is automatically served by the backend at `http://localhost:8000/api/fdc3/apps`. This allows OpenFin Workspace and other FDC3-compliant platforms to discover and integrate with CreditNexus.

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
# Verify OpenFin RVM is installed (recommended)
# RVM is automatically installed by OpenFin Runtime

# Alternative: Install OpenFin CLI (optional)
npm install -g @openfin/cli

# Or use the launcher script which handles RVM detection
.\scripts\launch_openfin.sh
```

**FDC3 App Directory Not Accessible:**
```powershell
# Verify the endpoint is accessible
curl http://localhost:8000/api/fdc3/apps

# Check backend logs for errors
# Ensure openfin/fdc3-intents.json exists
```

**Cannot Connect to Services:**
- Ensure firewall allows localhost traffic
- Check that ports 8000 and 5173 are available
- Verify `.env` file has correct DATABASE_URL (copy from `.env.example` if needed)

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
- **App Directory API**: Automatic discovery endpoint at `/api/fdc3/apps` for OpenFin Workspace
- **Context Type Validation**: Robust validation and error handling for all FDC3 contexts
- **Namespace Compliance**: All custom contexts use `finos.*` namespace per FDC3 2.0 standards
- **Desktop Integration**: Seamless integration with other OpenFin applications
- **Platform Management**: Multi-window platform with workspace support
- **Security**: Configurable security realms and CORS policies
- **Native API**: Uses OpenFin's built-in FDC3 2.0 API (no deprecated services)

### More Information

- [OpenFin Documentation](https://developers.openfin.co/)
- [FDC3 Specification](https://fdc3.finos.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vite Documentation](https://vitejs.dev/)

</details>

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
- **Blockchain**: Web3.py for smart contract interaction (Base network)
- **Smart Contracts**: Solidity contracts for securitization (Hardhat build system)

### Development Tools

- **Dependencies**: Managed via `pyproject.toml` and `uv.lock`
- **Testing**: `uv run pytest`
- **Code Quality**: ruff, black, mypy (configured in `pyproject.toml`)

> 📖 **Learn More**: See [Documentation - Technical](https://tonic-ai.mintlify.app/architecture) for technology details and [Documentation - Configuration](https://tonic-ai.mintlify.app/getting-started/configuration) for environment setup.

---

<details>
<summary><b>🚀 Demonstration & Quick Start Guide (Click to expand)</b></summary>

<br>

This guide explains how to use CreditNexus for demonstration purposes, from first login to executing a complex satellite-verified trade.

<details>
<summary><b>1. Accessing the Platform (Login)</b></summary>

CreditNexus automatically initializes a default administrative user on first startup for easy exploration.

- **URL**: `http://localhost:5173`
- **Default Email**: `demo@creditnexus.app`
- **Default Password**: `DemoPassword123!`
- **Role**: `admin` (Full system access)

</details>

<details>
<summary><b>2. Initializing Demo Data (The Demo Tab)</b></summary>

To populate the application with a realistic portfolio of deals, documents, and events without manual entry, use the built-in seeding engine.

1.  Navigate to the **"Demo"** tab in the top navigation or sidebar.
2.  Select the datasets you wish to seed:
    - **Users**: Creates a suite of role-based demo users (Auditor, Banker, etc.).
    - **Templates**: Seeds LMA-compliant document templates.
    - **Policies**: Loads regulatory and ESG policy rules (Basel III, MiCA, etc.).
    - **Generate Deals**: Synthetically creates 12+ complex deals with full AI-generated legal histories.
3.  Click **"Run Seeding Process"**.
4.  Watch the real-time logs as the **DemoDataService** orchestrates the creation of a complete financial environment.

</details>

<details>
<summary><b>3. Role-Based Demonstration Flows</b></summary>

Logout and log back in as different users to see how CreditNexus adapts to various financial personas:

- **The Banker (`banker@creditnexus.app` / `Banker123!`)**:
  - Focuses on the **Trade Blotter** and **Deals Dashboard**.
  - Can initiate new credit agreements and track workflow approvals.
- **The Law Officer (`lawofficer@creditnexus.app` / `LawOfficer123!`)**:
  - Reviews document extractions in the **Document Parser**.
  - Approves or flags specific legal clauses and covenants.
- **The Auditor (`auditor@creditnexus.app` / `Auditor123!`)**:
  - Uses the **One-Click Audit Report** and the **CDM Event Explorer**.
  - Has a read-only oversight of all policy decisions and state transitions.

</details>

<details>
<summary><b>4. Verification Demo (Satellite Ground Truth)</b></summary>

This is the "Live Wire" workflow connecting legal covenants to physical reality.

1.  Navigate to **"Verification Demo"**.
2.  Drag & Drop the sample **Credit Agreement PDF** (or use a generated demo deal).
3.  The **Legal Agent** extracts covenants (e.g., "NDVI > 0.75" for a sustainable farm).
4.  Click **"Securitize & Verify"**.
5.  **Ground Truth Protocol**:
    - If no SentinelHub API key is provided, the system uses its **Synthetic Satellite Engine** to generate plausible multispectral data based on the asset's geocoded coordinates.
    - The **NDVI Service** calculates vegetation health.
    - The **TorchGeo Classifier** verifies the land use (e.g., "Vineyard").
6.  **Result**: The system determines **COMPLIANCE** or **BREACH** and automatically broadcasts the update via **FDC3** to the Risk War Room.

</details>

<details>
<summary><b>5. The CDM Event Ledger</b></summary>

Every action taken in the steps above—from a banker creating a deal to a satellite detecting a breach—generates a **FINOS Common Domain Model (CDM)** event.

- Navigate to **"Auditor > Event Explorer"** to see the immutable ledger.
- Each event is stored as a standard JSON structure, ensuring that legal data is interoperable with any other CDM-compliant banking system.

</details>

> 📖 **Pro Tip**: Use the **FDC3 Desktop Integration** by opening the app in **OpenFin**. This allows the Document Parser, Trade Blotter, and GreenLens to stay synchronized in real-time as you click through a deal.

</details>

---

## ⚠️ Important Disclosures

### DORA Compliance Disclosure

**Digital Operational Resilience Act (DORA) - European Union Regulation**

This application is provided as a **non-production demonstration**. However, transactions executed through this system may be **live and executory**, with real digital signatures and legal implications for all signees based on system configuration. Users are responsible for understanding the legal and regulatory implications of their use of this system.

> 📖 **Learn More**: See [Documentation - DORA Disclosure](https://tonic-ai.mintlify.app/compliance/dora-disclosure) for complete compliance information.

### Compliance Standards

- **FDC3 2.0**: Full desktop interoperability compliance - [Documentation](https://tonic-ai.mintlify.app/compliance/fdc3-compliance)
- **OpenFin**: Native integration support - [Documentation](https://tonic-ai.mintlify.app/compliance/openfin-compliance)
- **FINOS CDM**: Complete Common Domain Model compliance - [Documentation](https://tonic-ai.mintlify.app/compliance/cdm-compliance)
- **DORA**: European cybersecurity regulation awareness - [Documentation](https://tonic-ai.mintlify.app/compliance/dora-disclosure)
- **Policy Engine**: Real-time compliance enforcement - [Documentation](https://tonic-ai.mintlify.app/compliance/policy-compliance)

---

## 👥 Our Team

Our team brings over **20 years of combined experience** in the financial industry:

- **Joseph Pollack** - Chief Information Officer (Strategic technology leadership)
- **Biniyam Ajew** - Senior Developer (Full-stack development and system architecture)

> 📖 **Learn More**: See [Company Site - Team](https://josephrp.github.io/creditnexus) for detailed team information.

---

*Built by the CreditNexus Team - "Trust, but Verify (from Space)."*
