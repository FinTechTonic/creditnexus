# CreditNexus

A FINOS-Compliant Financial AI Agent for extracting structured credit agreement data from unstructured legal documents.

## Overview

CreditNexus uses OpenAI's GPT-4o model with LangChain to extract structured, machine-readable data from credit agreements. The extracted data conforms to the FINOS Common Domain Model (CDM), ensuring interoperability with other financial systems.

## Architecture

### Backend
- **Framework**: FastAPI with Python 3.11
- **AI Engine**: LangChain + OpenAI GPT-4o
- **Port**: 8000 (development), 5000 (production)
- **Key Features**:
  - `/api/extract` - Extracts structured data from credit agreement text
  - `/api/health` - Health check endpoint
  - Automatic strategy selection (simple vs map-reduce) based on document length
  - Reflexion retry pattern for validation error correction
  - Static file serving for production deployment

### Frontend
- **Framework**: React + Vite + TypeScript
- **Port**: 5000
- **UI Components**: Custom components with Tailwind CSS
- **Key Features**:
  - Document upload interface
  - Real-time extraction with loading states
  - Review interface for extracted data
  - Approve/reject workflow

### Data Models
All data models follow the FINOS Common Domain Model (CDM) specification:
- `CreditAgreement` - Root object containing all extracted data
- `Party` - Legal entities (Borrower, Lender, Administrative Agent, etc.)
- `LoanFacility` - Individual loan facilities with terms
- `InterestRatePayout` - Interest rate structure and payment frequency
- `Money` - Monetary amounts with currency (using Decimal for precision)
- `FloatingRateOption` - Benchmark rates and spreads (in basis points)

## Development

### Environment Variables
- `OPENAI_API_KEY` (required) - OpenAI API key for GPT-4o access

### Running Locally
Both workflows start automatically:
- **Frontend**: `cd client && npm run dev` (port 5000)
- **Backend**: `uvicorn server:app --host 127.0.0.1 --port 8000 --reload`

### API Proxy
In development, the Vite frontend proxies `/api` requests to `http://localhost:8000`.

## Deployment

The application is configured for Replit's autoscale deployment:

1. **Build**: Installs dependencies and builds the frontend
2. **Run**: Starts uvicorn server on port 5000, serving both API and static files
3. **Static Files**: Built frontend is served from `client/dist/`

The backend automatically detects the presence of built static files and serves them in production, falling back to API-only mode if they're not found.

## Key Technical Details

### Extraction Process
1. User uploads a credit agreement document (text)
2. Frontend sends text to `/api/extract` endpoint
3. Backend analyzes document length:
   - **< 50k characters**: Uses simple extraction with structured output
   - **≥ 50k characters**: Uses map-reduce strategy for long documents
4. LLM extracts structured data conforming to CDM schema
5. If validation fails, the error is fed back to the LLM for correction (up to 3 attempts)
6. Frontend displays extracted data for review

### Validation Rules
- Agreement date cannot be in the future
- Facility maturity dates must be after agreement date
- All facilities must use the same currency
- At least one party must have role "Borrower"
- Interest rate spreads are normalized to basis points (3.5% → 350.0)
- All monetary amounts use Decimal for precision

## Project Structure
```
├── app/
│   ├── api/              # FastAPI routes and API layer
│   ├── chains/           # LangChain extraction logic
│   ├── core/             # Configuration and settings
│   ├── db/               # Database models and session management
│   └── models/           # Pydantic models (CDM implementation)
├── client/               # React frontend
│   ├── src/
│   │   ├── components/   # UI components
│   │   └── App.tsx       # Main application
│   └── dist/             # Built static files (production)
├── openfin/              # OpenFin deployment configuration
│   ├── app.json          # Application manifest
│   ├── fdc3-intents.json # FDC3 intent declarations
│   └── provider.json     # Service provider config
└── server.py             # FastAPI application entry point
```

## Enterprise Features

### Document Management
- **Document Library**: Browse, search, and manage saved documents
- **Version History**: Track all versions of a document with full audit trail
- **Workflow Management**: Draft → Under Review → Approved → Published state machine
- **Audit Logging**: Full audit trail for all user actions with timestamps and metadata

### Export Capabilities
Export extracted data in multiple formats:
- **JSON**: Complete structured data in FINOS CDM format
- **CSV**: Flattened tabular format for spreadsheet analysis
- **Excel**: Multi-sheet workbook with Summary, Facilities, and Parties sheets

API Endpoint: `GET /api/documents/{id}/export?format=json|csv|excel`

### User Authentication
- Replit OAuth2 PKCE flow for secure authentication
- Role-based access control (Viewer, Analyst, Reviewer, Admin)
- Session management with secure cookies

## OpenFin Deployment

CreditNexus is fully compatible with OpenFin platform deployment and supports FDC3 2.0 interoperability.

### Configuration Files
Located in the `openfin/` directory:
- **`app.json`**: Main OpenFin application manifest with platform settings
- **`fdc3-intents.json`**: FDC3 app directory entry with intent declarations
- **`provider.json`**: Service provider configuration for channels and intents
- **`README.md`**: Detailed deployment instructions

### Supported FDC3 Intents

| Intent | Description |
|--------|-------------|
| `ViewLoanAgreement` | View credit agreement details |
| `ApproveLoanAgreement` | Approve or reject agreements |
| `ViewESGAnalytics` | View ESG scores and metrics |
| `ExtractCreditAgreement` | Extract data from documents |
| `ViewPortfolio` | View portfolio overview |

### Custom Context Types
- `finos.creditnexus.agreement` - Credit agreement context
- `finos.creditnexus.document` - Document for extraction
- `finos.creditnexus.portfolio` - Portfolio context
- `finos.creditnexus.approvalResult` - Approval workflow result
- `finos.creditnexus.esgData` - ESG analytics data

### App Channels
- `creditnexus.workflow` - Workflow state updates
- `creditnexus.extraction` - Document extraction events

## Recent Changes (December 2024)
- Created FastAPI backend with extraction endpoints
- Configured Vite frontend with API proxy and allowedHosts
- Updated frontend to use relative API paths
- Added static file serving for production deployment
- Configured autoscale deployment with build pipeline
- Set up development workflows for frontend and backend
- Redesigned UI with professional enterprise-grade styling:
  - Modern header with branding
  - Feature cards highlighting capabilities
  - Drag-and-drop file upload area
  - Text paste input for documents
  - Responsive layout with glassmorphism effects
  - Improved review interface with summary and JSON views
- Added enterprise features:
  - Database schema with Users, Documents, DocumentVersions, Workflows, AuditLog tables
  - User authentication with Replit OAuth2
  - Document history with version tracking
  - Dashboard analytics with portfolio overview
  - Approval workflow with state machine
  - Audit trail with comprehensive logging
  - Export capabilities (JSON, CSV, Excel formats)
