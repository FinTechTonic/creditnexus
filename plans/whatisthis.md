Reviewing the README and project structure to understand the app's purpose and implementation.


[3 tools called]


Exploring the codebase to understand the implementation:


[5 tools called]


Reviewing the extraction chain implementation:


[4 tools called]


Checking authentication and FDC3 integration:


[2 tools called]


## **What CreditNexus Does**

CreditNexus is a next-generation financial AI platform that bridges legal contracts and physical reality. It automates the extraction of structured data from credit agreement documents (PDFs/text/images/audio) and verifies sustainability-linked loan covenants using satellite imagery and deep learning. The platform provides a complete workflow from document ingestion to portfolio management, with desktop interoperability via FDC3 standards.

### **Core Purpose:**
- Extract structured financial data from unstructured credit agreement text, images, and audio
- Convert extracted data into FINOS CDM format
- Generate LMA templates from CDM data
- Verify sustainability-linked loans using satellite imagery (NDVI)
- Manage documents through a review/approval workflow
- Enforce regulatory compliance via policy-as-code engine
- Process loan applications and manage deal lifecycles
- Provide portfolio analytics, credit risk assessment, and ESG tracking
- Enable desktop interoperability via FDC3

---

## **How It Works - Deep Technical Breakdown**

### **1. AI-Powered Extraction Engine**

#### **Simple Extraction Strategy** (for documents < 50k characters)

**Location:** `app/chains/extraction_chain.py`

**Process:**
1. Document input: User uploads PDF or pastes text
2. Text extraction: PDFs are parsed using PyMuPDF (`fitz`) to extract raw text
3. LLM processing:
   - Uses OpenAI GPT-4o with `temperature=0` for deterministic output
   - LangChain binds the Pydantic `ExtractionResult` model as a structured output
   - The LLM is prompted to extract:
     - Parties (Borrower, Lenders, Administrative Agent) with LEIs
     - Loan facilities (Term Loans, Revolving Credit) with commitment amounts
     - Interest rates (benchmark + spread in basis points)
     - Dates (agreement date, maturity dates)
     - Governing law
     - ESG provisions (if sustainability-linked)
4. Reflexion retry pattern:
   - If validation fails, the Pydantic error is fed back to the LLM
   - The LLM corrects issues (e.g., date format, currency consistency)
   - Up to 3 retry attempts with error feedback
5. Validation:
   - Pydantic validates all fields against the CDM schema
   - Business logic validators check:
     - Agreement date not in future
     - Maturity dates after agreement date
     - All facilities use same currency
     - At least one Borrower party exists
     - Spreads normalized to basis points (3.5% → 350.0)

#### **Map-Reduce Strategy** (for documents > 50k characters)

**Location:** `app/chains/map_reduce_chain.py` + `app/utils/document_splitter.py`

**Process:**
1. Document splitting:
   - Uses `CreditAgreementSplitter` to split by Articles (Article I, Article II, etc.)
   - Regex pattern matches: `ARTICLE\s+([IVX]+|\d+)`
   - Each Article becomes a chunk (max 8000 chars, min 500 chars)
   - If an Article is too long, it's split by paragraphs
2. MAP phase:
   - Each chunk is processed independently
   - Uses `PartialCreditAgreement` model (all fields optional)
   - Extracts whatever data exists in that section
   - Processes chunks sequentially (can be parallelized)
3. REDUCE phase:
   - All partial extractions are merged by a reducer LLM
   - Deduplicates parties (by name matching)
   - Combines facilities
   - Selects authoritative dates (prefers preamble/Article I)
   - Produces a complete `CreditAgreement` object
   - Final validation ensures consistency

#### **Multimodal Extraction Strategy**

**Location:** `app/chains/audio_transcription_chain.py`, `app/chains/image_extraction_chain.py`, `app/chains/multimodal_fusion_chain.py`

CreditNexus supports extraction from multiple input sources:

1. **Audio Transcription**
   - Uses nvidia/canary-1b-v2 model for speech-to-text
   - Supports multiple languages (source_lang, target_lang)
   - Formats: WAV, MP3, M4A, OGG, FLAC, WEBM
   - Optional CDM extraction from transcription
   - Endpoint: `POST /api/audio/transcribe`

2. **Image OCR**
   - Uses Multimodal-OCR3 for text extraction from images
   - Supports multiple image uploads (multi-page documents)
   - Formats: PNG, JPEG, WEBP, GIF, BMP, TIFF
   - Combines OCR text from all images
   - Optional CDM extraction from OCR text
   - Endpoint: `POST /api/image/extract`

3. **Multimodal Fusion**
   - Combines data from multiple sources (audio, image, document, text)
   - Two fusion strategies:
     - **Deterministic**: Source priority-based conflict resolution
     - **LLM-based**: AI-powered intelligent merging
   - Tracks field sources for auditability
   - Resolves conflicts with confidence scores
   - Endpoint: `POST /api/multimodal/fuse`

#### **Template-Aware Extraction**

**Location:** `app/chains/template_aware_extraction.py`

- Optimizes extraction based on document template category
- Provides category-specific guidance to LLM
- Supports: Facility Agreement, Term Sheet, Sustainable Finance, Regulatory, etc.
- Improves extraction accuracy for specialized document types

### **2. Data Models & Validation**

**Location:** `app/models/cdm.py`

**FINOS CDM Structure:**
```python
CreditAgreement
├── agreement_date: date (ISO 8601)
├── parties: List[Party]
│   ├── id, name, role, lei (20-char), jurisdiction
├── facilities: List[LoanFacility]
│   ├── facility_name, commitment_amount (Money: amount Decimal, currency)
│   ├── interest_terms: InterestRatePayout
│   │   ├── rate_option: FloatingRateOption (benchmark, spread_bps)
│   │   └── payment_frequency: Frequency (period, period_multiplier)
│   └── maturity_date: date
├── governing_law: str
├── sustainability_provisions (optional)
│   ├── sustainability_linked: bool
│   └── esg_kpi_targets: List[ESGKPITarget]
│       ├── kpi_type, target_value, current_value, unit, margin_adjustment_bps
├── KYC/AML Fields (optional): kyc_verification_date, sanctions_screening_date, aml_certification_date, source_of_funds, ongoing_obligations
├── Regulatory Compliance Fields (optional): fatf_compliance_statement, cdd_obligations, risk_weighting, regulatory_capital_requirements
├── Security & Intercreditor Fields (optional): collateral_details, security_interests, priority_arrangements, voting_mechanisms
├── Secondary Trading Fields (optional): transfer_provisions, assignment_restrictions, margin_calculation_methodology
├── Crypto & Digital Assets Fields (optional): crypto_asset_details, digital_asset_types, blockchain_network, wallet_addresses
├── Consumer Credit Fields (optional): apr_disclosure, cooling_off_period, withdrawal_rights
├── Restructuring Fields (optional): restructuring_terms, forbearance_period
├── Bridge Loan Fields (optional): bridge_period, takeout_facility_reference
├── Mezzanine Finance Fields (optional): equity_kicker, warrant_terms
├── Project Finance Fields (optional): project_name, sponsor_details, revenue_streams
├── Trade Finance Fields (optional): lc_number, beneficiary_details, shipping_documents
├── Asset-Based Lending Fields (optional): collateral_valuation, borrowing_base
├── Letter of Credit Fields (optional): lc_type, expiry_date, presentation_period
├── Guarantee Fields (optional): guarantor_details, guarantee_amount, guarantee_type
├── Subordination Fields (optional): senior_debt_amount, subordination_ratio
└── Amendment Fields (optional): amendment_number, effective_date, amended_sections
```

**Validation Rules:**
- Type safety: All fields must match declared types (Pydantic)
- Business logic: Custom `@model_validator` decorators enforce:
  - Dates not in future
  - Maturity > agreement date
  - Currency consistency across facilities
  - At least one Borrower party
- Data normalization:
  - Percentages → basis points (automatic conversion)
  - Dates → ISO 8601 format
  - Monetary amounts → Decimal for precision

### **3. Database & Persistence**

**Location:** `app/db/models.py`

**Database Schema (PostgreSQL with SQLAlchemy ORM):**

1. **Users Table:**
   - OAuth integration (Replit) + JWT authentication
   - Roles: viewer, analyst, reviewer, admin
   - Password hashing with bcrypt
   - Account lockout after failed login attempts

2. **Documents Table:**
   - Stores document metadata (title, borrower, total commitment, etc.)
   - Links to versions and workflow

3. **DocumentVersions Table:**
   - Full version history (extracted_data as JSONB)
   - Tracks original_text, source_filename, extraction_method
   - Each document can have multiple versions

4. **Workflows Table:**
   - State machine: `DRAFT → UNDER_REVIEW → APPROVED → PUBLISHED → ARCHIVED`
   - Tracks assignments, due dates, priorities
   - Records approval/rejection with timestamps

5. **AuditLogs Table:**
   - Complete audit trail of all actions
   - Records: user, action type, target, IP address, user agent, metadata
   - Used for compliance and security

6. **StagedExtractions Table:**
   - Legacy support for pre-approval staging

7. **LMATemplates Table:**
   - Stores LMA template files and metadata
   - Categories: Facility Agreement, Term Sheet, Sustainable Finance, Regulatory, etc.

8. **TemplateFieldMappings Table:**
   - Maps CDM fields to template placeholders
   - Mapping types: direct, computed, ai_generated

9. **GeneratedDocuments Table:**
   - Tracks documents generated from templates
   - Stores CDM data and field values used

10. **Policies Table:**
    - Stores policy rules and metadata
    - Status: DRAFT, PENDING_APPROVAL, ACTIVE, ARCHIVED

11. **PolicyVersions Table:**
    - Version history for policies
    - Stores rules_yaml for each version

12. **PolicyApprovals Table:**
    - Policy approval workflow tracking

13. **PolicyDecisions Table:**
    - Stores policy evaluation results (ALLOW/BLOCK/FLAG)
    - Includes CDM events and evaluation trace

14. **Applications Table:**
    - Loan application submissions (INDIVIDUAL/BUSINESS)
    - Status: DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED

15. **Deals Table:**
    - Deal lifecycle management
    - Status: DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, ACTIVE, CLOSED
    - Deal-based folder structure for documents

16. **DealNotes Table:**
    - Notes and comments on deals

17. **LoanAssets Table:**
    - Loan asset information for verification
    - Stores address, coordinates, NDVI scores, risk status

18. **GreenFinanceAssessments Table:**
    - Green finance compliance assessments

19. **CreditRiskAssessments Table:**
    - Credit risk evaluation results (PD, LGD, EAD, RWA, capital requirement)

20. **Inquiries Table:**
    - User inquiries and support tickets

21. **Meetings Table:**
    - Meeting scheduling and management

22. **RolePermissions Table:**
    - Granular permission system

23. **ClauseCache Table:**
    - Cache for AI-generated clauses to reduce LLM costs

### **4. API Layer**

**Location:** `app/api/routes.py` (2,270 lines)

**Key Endpoints:**

1. **Extraction:**
   - `POST /api/extract` - Extract from text
   - `POST /api/upload` - Upload PDF/TXT and extract

2. **Documents:**
   - `GET /api/documents` - List with search/pagination
   - `POST /api/documents` - Create new document
   - `GET /api/documents/{id}` - Get with all versions
   - `POST /api/documents/{id}/versions` - Create new version
   - `DELETE /api/documents/{id}` - Delete (with permission check)

3. **Workflow:**
   - `POST /api/documents/{id}/workflow/submit` - Submit for review
   - `POST /api/documents/{id}/workflow/approve` - Approve (reviewer/admin only)
   - `POST /api/documents/{id}/workflow/reject` - Reject with reason
   - `POST /api/documents/{id}/workflow/publish` - Publish approved document

4. **Analytics:**
   - `GET /api/analytics/portfolio` - Portfolio overview
   - `GET /api/analytics/dashboard` - Dashboard metrics with activity feed
   - `GET /api/analytics/charts` - Time-series data for visualizations

5. **Export:**
   - `GET /api/documents/{id}/export?format=json|csv|excel`
   - Flattens nested data for CSV/Excel
   - Creates multi-sheet Excel files (Summary, Facilities, Parties)

6. **Audit:**
   - `GET /api/audit-logs` - List with filtering
   - `GET /api/documents/{id}/audit-logs` - Document-specific logs

7. **Multimodal Extraction:**
   - `POST /api/audio/transcribe` - Transcribe audio and extract CDM
   - `POST /api/image/extract` - Extract text from images and extract CDM
   - `POST /api/multimodal/fuse` - Fuse data from multiple sources

8. **LMA Template Generation:**
   - `GET /api/templates` - List available templates
   - `POST /api/templates/{id}/generate` - Generate document from template
   - `GET /api/templates/{id}/mappings` - Get field mappings

9. **Policy Engine:**
   - `GET /api/policies` - List policies
   - `POST /api/policies` - Create new policy
   - `POST /api/policies/{id}/test` - Test policy with transaction
   - `POST /api/policies/{id}/approve` - Approve policy version

10. **Deal Management:**
    - `GET /api/deals` - List deals
    - `POST /api/deals` - Create new deal
    - `GET /api/deals/{id}` - Get deal details
    - `POST /api/deals/{id}/notes` - Add note to deal

11. **Applications:**
    - `GET /api/applications` - List applications
    - `POST /api/applications` - Create application
    - `POST /api/applications/{id}/create-deal` - Create deal from approved application

12. **Credit Risk & Green Finance:**
    - `POST /api/credit-risk/assess` - Assess credit risk
    - `POST /green-finance/assess` - Assess green finance compliance

13. **Profile Extraction:**
    - `POST /api/profile/extract` - Extract profile from documents

14. **Decision Support:**
    - `POST /api/chatbot/chat` - Chat with decision support chatbot

### **5. Frontend Architecture**

**Location:** `client/src/`

**Tech Stack:**
- React + TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- FDC3 SDK for desktop interoperability

**Main Components:**

1. **App.tsx / DesktopAppLayout** - Main application shell:
   - Multi-app navigation (Dashboard, Docu-Digitizer, Library, Trade Blotter, GreenLens, Document Generator, Policy Editor, Verification Demo, Ground Truth, Risk War Room)
   - FDC3 intent handling
   - Authentication state management
   - Sidebar with collapsible tools
   - Theme switching (light/dark)

2. **DocuDigitizer** (`apps/docu-digitizer/DocumentParser.tsx`):
   - File upload (PDF/TXT) via drag-and-drop
   - Text paste interface
   - **Multimodal input tabs** (audio, image, document, text)
   - Extraction progress display
   - Review interface for extracted data
   - Save to library functionality
   - FDC3 broadcast on save

3. **Dashboard** (`components/Dashboard.tsx`):
   - Portfolio metrics (total commitments, ESG scores)
   - Workflow distribution charts (pie/bar charts)
   - Activity feed from audit logs
   - Recent documents list
   - Real-time updates via FDC3 channels

4. **DocumentHistory** (`components/DocumentHistory.tsx`):
   - List all documents with search
   - Version history viewer
   - Workflow state indicators (color-coded badges)
   - Export functionality (JSON/CSV/Excel)
   - Filter by status, borrower, date range

5. **ReviewInterface** (`components/ReviewInterface.tsx`):
   - Displays extracted data in structured format
   - Edit capabilities (inline editing)
   - Approve/Reject actions
   - Workflow transition buttons
   - Validation warnings display

6. **DocumentGenerator** (`apps/document-generator/DocumentGenerator.tsx`):
   - Template selection grid
   - CDM data input (from library or manual)
   - Field mapping preview
   - AI-powered field population
   - Document preview and export
   - Chatbot assistance for template guidance

7. **PolicyEditor** (`apps/policy-editor/PolicyEditor.tsx`):
   - Visual rule builder
   - YAML editor and preview
   - Policy testing with transaction builder
   - Policy validation
   - Approval workflow
   - Version history

8. **VerificationDashboard** (`components/VerificationDashboard.tsx`):
   - Upload credit agreement PDF
   - Display extracted SPT and address
   - Run verification workflow
   - Show satellite imagery (if available)
   - Display NDVI score and compliance status
   - Map view of asset location

9. **GroundTruthDashboard** (`components/GroundTruthDashboard.tsx`):
   - Portfolio map view (Leaflet/React-Leaflet)
   - Status indicators (Green=Compliant, Red=Breach, Yellow=Warning)
   - Asset creation form
   - Filter by compliance status
   - Click asset to view details

10. **RiskWarRoom** (`components/RiskWarRoom.tsx`):
    - Semantic search interface
    - Vector search using pgvector
    - FDC3 context listener for automatic focus
    - Query examples: "Find all vineyards in California with NDVI < 0.6"
    - Results display with compliance status

11. **GreenLens** (`apps/green-lens/GreenLens.tsx`):
    - Visualizes ESG margin ratchets
    - Shows how interest rate changes based on ESG performance
    - Dynamic pricing calculator
    - FDC3 context listener for loan data

12. **TradeBlotter** (`apps/trade-blotter/TradeBlotter.tsx`):
    - LMA trade ticket interface
    - Pre-fills from FDC3 context
    - Generates FINOS CDM trade execution events
    - Broadcasts trade data to other apps

13. **ApplicationDashboard** (`components/ApplicationDashboard.tsx`):
    - Individual and business application forms
    - Application status tracking
    - Application-to-deal conversion

14. **DealDashboard** (`components/DealDashboard.tsx`):
    - Deal list and search
    - Deal detail view with timeline
    - Deal notes and collaboration
    - Document organization by deal

15. **AdminSignupDashboard** (`components/AdminSignupDashboard.tsx`):
    - Signup approval workflow
    - User management
    - Role assignment

16. **Additional Components:**
    - **CdmFieldEditor**: Edit CDM fields inline
    - **ClauseEditor**: Edit document clauses
    - **TemplateLibrary**: Browse LMA templates
    - **ProfileEnrichment**: User profile management
    - **MetaMaskConnect**: Blockchain wallet integration
    - **PermissionGate**: Role-based access control UI
    - **Inbox**: User notifications and messages
    - **CalendarView**: Meeting scheduling
    - **DemoDataDashboard**: Demo data management

### **6. FDC3 Desktop Interoperability**

**Location:** `client/src/context/FDC3Context.tsx` + `openfin/` + `finsemble/`

**FDC3 Integration:**
- FDC3 2.0 compliant for financial desktop connectivity
- Supports OpenFin and Finsemble platforms

**Intents Supported:**
- `ViewLoanAgreement` - Open agreement details
- `ApproveLoanAgreement` - Approval workflow
- `ViewESGAnalytics` - ESG dashboard
- `ExtractCreditAgreement` - Trigger extraction from external app
- `ViewPortfolio` - Portfolio overview

**App Channels:**
- `creditnexus.workflow` - Workflow state updates
- `creditnexus.extraction` - Extraction events
- `creditnexus.portfolio` - Portfolio updates

**Custom Context Types:**
- `finos.creditnexus.agreement` - Credit agreement context
- `finos.creditnexus.document` - Document for extraction
- `finos.creditnexus.portfolio` - Portfolio context
- `finos.creditnexus.approvalResult` - Approval results
- `finos.creditnexus.esgData` - ESG analytics

### **7. Authentication & Security**

**Location:** `app/auth/jwt_auth.py`

**Security Features:**
- JWT access tokens (30 min expiry) + refresh tokens (7 days)
- Password requirements: 12+ chars, uppercase, lowercase, number, special char
- Account lockout after 5 failed attempts (30 min lockout)
- bcrypt password hashing
- Token blacklisting for logout
- Role-based access control (RBAC)
- Audit logging of all actions

**Role-Based Access Control (RBAC):**
- **viewer**: Read-only access
- **analyst**: Can create documents, submit for review
- **reviewer**: Can approve/reject, publish documents
- **admin**: Full access, user management
- **auditor**: Full oversight, read-only access to all
- **banker**: Write permissions for deals, documents
- **law_officer**: Write/edit for legal documents
- **accountant**: Write/edit for financial data
- **applicant**: Apply and track applications

**Signup Approval Workflow:**
- New user signups require approval
- Signup status: pending → approved/rejected
- Admin/reviewer can approve/reject signups
- Rejection reasons tracked

**Authentication Flow:**
1. User logs in with email/password or OAuth (Replit)
2. Server validates credentials, checks lockout status
3. Returns JWT access token + refresh token
4. Frontend stores tokens, includes in API requests
5. Server validates JWT on protected endpoints
6. Refresh token used to get new access token when expired

### **8. Workflow State Machine**

**States:**
```
DRAFT → UNDER_REVIEW → APPROVED → PUBLISHED
         ↓ (reject)
       DRAFT
```

**Transitions:**
- **Submit:** Draft → Under Review (analyst/reviewer/admin)
- **Approve:** Under Review → Approved (reviewer/admin)
- **Reject:** Under Review → Draft (reviewer/admin, with reason)
- **Publish:** Approved → Published (reviewer/admin)
- **Archive:** Any state → Archived (reviewer/admin)

**Workflow Features:**
- Assignment to specific reviewers
- Priority levels (low, normal, high, urgent)
- Due dates for reviews
- Rejection reasons tracked
- Full audit trail of all transitions

### **9. Analytics & Reporting**

**Portfolio Analytics:**
- Total commitments by currency
- ESG breakdown (sustainability-linked vs. non-sustainability)
- Workflow distribution (how many in each state)
- Maturity timeline
- Recent activity feed

**Dashboard Metrics:**
- Documents created this week vs. last week (trend)
- Pending reviews count
- Approved this week
- Total commitment USD
- Sustainability percentage

**Chart Data:**
- Document creation trends over time
- Commitment trends
- Activity by type (create, update, approve, etc.)
- Workflow pipeline visualization

### **10. Export Functionality**

**Formats:**
- **JSON:** Full nested structure
- **CSV:** Flattened single-row format
- **Excel:** Multi-sheet workbook
  - Summary sheet: All document-level data
  - Facilities sheet: One row per facility
  - Parties sheet: One row per party

**Export Process:**
1. Retrieves document version from database
2. Flattens nested structure for tabular formats
3. Creates pandas DataFrames
4. Generates file (CSV/Excel/JSON)
5. Streams to client as download
6. Logs export action in audit trail

---

## **Architecture Summary**

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React + TypeScript)                          │
│  - Multi-app interface (Dashboard, Docu-Digitizer, etc.) │
│  - FDC3 integration for desktop interoperability        │
│  - Real-time updates via FDC3 channels                  │
└─────────────────────────────────────────────────────────┘
                          ↕ HTTP/REST
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend (Python)                              │
│  - REST API endpoints                                    │
│  - Authentication (JWT + OAuth)                         │
│  - Request validation & routing                         │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│  Cognitive Layer (LangChain + OpenAI)                  │
│  - GPT-4o for semantic extraction                        │
│  - Structured output binding (Pydantic)                 │
│  - Reflexion retry pattern                               │
│  - Map-reduce for long documents                        │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│  Validation Layer (Pydantic)                           │
│  - FINOS CDM schema enforcement                          │
│  - Business logic validators                             │
│  - Type safety & data normalization                     │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│  Data Layer (PostgreSQL + SQLAlchemy)                   │
│  - Document storage with versioning                     │
│  - Workflow state machine                               │
│  - Audit logging                                        │
│  - User management                                      │
└─────────────────────────────────────────────────────────┘
```

---

## **Additional Features**

### **LMA Template Generation**
- Generates LMA (Loan Market Association) templates from CDM data
- Automatic field mapping from CDM to template placeholders
- AI-powered field population for missing data
- Template-aware extraction and generation
- Support for multiple template categories

### **Policy Engine & Compliance**
- Real-time policy evaluation using policy-as-code rules
- Enforces financial regulations (MiCA, Basel III, FATF)
- Policy editor with approval workflow
- Policy testing and validation
- CDM-compliant policy evaluation events
- Decision types: ALLOW, BLOCK, FLAG

### **Deal Management & Applications**
- Application processing (individual and business)
- Deal lifecycle management (DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED → ACTIVE → CLOSED)
- Deal-based folder structure for document organization
- Deal notes and collaboration
- Application-to-deal conversion workflow

### **Credit Risk & Green Finance**
- Credit risk assessment with PD, LGD, EAD, RWA, capital requirements
- Green finance assessments with SDG alignment
- Urban sustainability evaluation
- Emissions compliance monitoring
- Enhanced satellite verification with OSM and air quality

### **Decision Support & Profile Extraction**
- AI-powered decision support chatbot with RAG (ChromaDB)
- Template and CDM schema guidance
- Field filling assistance
- Profile extraction from documents
- Profile-based document pre-filling

## **Key Technologies**

- **Backend:** FastAPI, SQLAlchemy 2.0, PostgreSQL, Pydantic 2.0, LangChain, OpenAI GPT-4o, PyMuPDF, TorchGeo, Sentinel Hub, geopy
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, FDC3 SDK, React-Leaflet, Axios
- **AI/ML:** OpenAI GPT-4o, LangChain (structured outputs, map-reduce), nvidia/canary-1b-v2 (audio), Multimodal-OCR3 (images), TorchGeo ResNet-50 (land classification), OpenAI Embeddings (vector search)
- **Security:** JWT, bcrypt, OAuth2 PKCE, role-based access control, audit logging
- **Desktop:** FDC3 2.0, OpenFin, Finsemble
- **Data Format:** FINOS Common Domain Model (CDM), ISO 8601 dates
- **Database:** PostgreSQL with JSONB, pgvector for semantic search

This application automates credit agreement processing with AI extraction, structured validation, workflow management, satellite-based verification, policy enforcement, deal management, and desktop interoperability for financial institutions.