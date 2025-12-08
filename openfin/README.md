# OpenFin Deployment Configuration

This directory contains the OpenFin deployment configuration for CreditNexus.

## Files

### `app.json` - Application Manifest
The main OpenFin application manifest that defines:
- Platform configuration with UUID and branding
- Window layout and dimensions
- Runtime version and FDC3 service integration
- Shortcut and support information

### `fdc3-intents.json` - FDC3 Intent Declarations
FDC3 2.0 compliant app directory entry containing:
- Application metadata (appId, version, categories)
- Intent listeners and raisers with defined result types
- Custom context type schemas in `customConfig.contextTypes`
- User and app channel configurations

### `provider.json` - Service Provider Configuration
OpenFin service provider setup for:
- App directory hosting
- Channel management
- FDC3 intent routing

## Configuration Variables

All configuration files use `${APP_URL}` as a placeholder for your deployment URL. Before deployment, replace this with your actual application URL.

Example:
```bash
# Replace placeholders with your actual URL
sed -i 's|\${APP_URL}|https://your-app.replit.app|g' openfin/*.json
```

## Supported FDC3 Intents

### Listens For (Incoming)

| Intent | Description | Input Context | Result Type |
|--------|-------------|---------------|-------------|
| `ViewLoanAgreement` | View details of a credit agreement | `finos.creditnexus.agreement`, `fdc3.instrument` | `finos.creditnexus.agreement` |
| `ApproveLoanAgreement` | Approve or reject a loan agreement | `finos.creditnexus.agreement` | `finos.creditnexus.approvalResult` |
| `ViewESGAnalytics` | View ESG scores and metrics | `finos.creditnexus.portfolio`, `finos.creditnexus.agreement` | `finos.creditnexus.esgData` |
| `ExtractCreditAgreement` | Extract data from a document | `finos.creditnexus.document` | `finos.creditnexus.agreement` |
| `ViewPortfolio` | View portfolio overview | `fdc3.portfolio`, `finos.creditnexus.portfolio` | `finos.creditnexus.portfolio` |

### Raises (Outgoing)

| Intent | Description | Context Types |
|--------|-------------|---------------|
| `ViewChart` | Request chart visualization | `fdc3.timeRange` |
| `ViewInstrument` | View instrument details | `fdc3.instrument` |

## Custom Context Types

All context type schemas are defined in `customConfig.contextTypes` within the app directory entry.

### `finos.creditnexus.agreement`
Credit agreement context containing:
- `type` (const) - "finos.creditnexus.agreement"
- `id.agreementId` (required) - Unique identifier
- `id.version` - Version number
- `name` - Display name
- `borrower` - Borrowing party name
- `agreementDate` - Date of agreement (ISO date format)
- `totalCommitment` - Object with `amount` and `currency`
- `workflowStatus` - One of: draft, under_review, approved, published
- `facilities` - Array of loan facilities
- `parties` - Array of agreement parties

### `finos.creditnexus.document`
Document context for extraction:
- `type` (const) - "finos.creditnexus.document"
- `content` (required) - Raw text content
- `id.documentId` - Document identifier
- `name` - Document name
- `mimeType` - Document MIME type

### `finos.creditnexus.portfolio`
Portfolio context:
- `type` (const) - "finos.creditnexus.portfolio"
- `id.portfolioId` - Portfolio identifier
- `name` - Portfolio name
- `agreementIds` - Array of agreement IDs
- `totalCommitment` - Object with `amount` and `currency`
- `agreementCount` - Number of agreements

### `finos.creditnexus.approvalResult`
Approval workflow result:
- `type` (const) - "finos.creditnexus.approvalResult"
- `agreementId` (required) - Agreement being approved
- `approved` (required) - Boolean approval status
- `approver` - User who approved
- `timestamp` - Approval time (ISO datetime)
- `comments` - Optional comments
- `newStatus` - New workflow status

### `finos.creditnexus.esgData`
ESG analytics data:
- `type` (const) - "finos.creditnexus.esgData"
- `agreementId` - Related agreement
- `environmentalScore` - E score (0-100)
- `socialScore` - S score (0-100)
- `governanceScore` - G score (0-100)
- `overallScore` - Combined score (0-100)
- `greenLoanIndicators` - Array of green loan markers
- `sustainabilityLinkedTerms` - Whether sustainability terms apply

## App Channels

### `creditnexus.workflow`
Workflow state updates and approval requests/responses.
- Broadcasts: `finos.creditnexus.agreement`, `finos.creditnexus.approvalResult`
- Listens for: `finos.creditnexus.approvalResult`

### `creditnexus.extraction`
Document extraction progress and completion events.
- Broadcasts: `finos.creditnexus.agreement`
- Listens for: `finos.creditnexus.document`

## Deployment

### Prerequisites
1. OpenFin Runtime installed or available via Workspace
2. Application deployed and accessible via HTTPS
3. Manifest files hosted on a web-accessible server

### Local Development
1. Replace `${APP_URL}` in all JSON files with your development URL
2. Host the manifest files on a web server (or use the application's static file serving)
3. Launch OpenFin with the app.json manifest:
   ```bash
   npx openfin-cli launch --manifest https://your-app.replit.app/openfin/app.json
   ```

### Production Deployment
1. Replace `${APP_URL}` with your production domain
2. Ensure manifests are served with correct MIME types (application/json)
3. Register the app in your OpenFin App Directory using `fdc3-intents.json`

### Serving Manifests from CreditNexus

The CreditNexus backend can serve these manifest files directly. Ensure the openfin directory is included in your static file serving configuration.

## Integration with OpenFin Workspace

To add CreditNexus to OpenFin Workspace:

1. Add the app directory entry from `fdc3-intents.json` to your workspace app directory
2. The app will appear in the Workspace dock and home screen
3. Users can raise intents to CreditNexus from other FDC3-compliant apps

## FDC3 Compliance

This configuration follows:
- FDC3 2.0 App Directory specification
- FINOS CDM for financial data structures
- OpenFin platform best practices

All context types use the `finos.creditnexus.*` namespace to avoid conflicts with standard FDC3 context types.
