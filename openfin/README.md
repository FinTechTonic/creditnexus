# OpenFin Deployment Configuration

This directory contains the OpenFin deployment configuration for CreditNexus.

## Files

### `app.json` - Application Manifest
The main OpenFin application manifest that defines:
- Platform configuration with UUID and branding
- Window layout and dimensions
- Runtime version (uses "stable" for automatic latest stable runtime)
- Built-in FDC3 2.0 API integration via `fdc3InteropApi`
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

## Runtime Requirements

### Minimum Runtime Version
- **FDC3 2.0 Support**: Requires OpenFin Runtime 29.108.73 or later
- **FDC3 1.2 Support**: Requires OpenFin Runtime 21.93.65 or later

The manifest uses `"version": "stable"` which automatically downloads the latest stable runtime, ensuring FDC3 2.0 compatibility.

### FDC3 Integration
This configuration uses OpenFin's **built-in FDC3 API** (not the deprecated FDC3 service). The integration is configured via:

```json
{
  "platform": {
    "defaultViewOptions": {
      "fdc3InteropApi": "2.0"
    }
  }
}
```

This approach provides:
- Native FDC3 2.0 support without external services
- Better performance and reliability
- Automatic compatibility with OpenFin Workspace

## Supported FDC3 Intents

### Listens For (Incoming)

| Intent | Description | Input Context | Result Type |
|--------|-------------|---------------|-------------|
| `ViewLoanAgreement` | View details of a credit agreement | `finos.creditnexus.agreement`, `fdc3.instrument` | `finos.creditnexus.agreement` |
| `ApproveLoanAgreement` | Approve or reject a loan agreement | `finos.creditnexus.agreement` | `finos.creditnexus.approvalResult` |
| `ViewESGAnalytics` | View ESG scores and metrics | `finos.creditnexus.portfolio`, `finos.creditnexus.agreement` | `finos.creditnexus.esgData` |
| `ExtractCreditAgreement` | Extract data from a document | `finos.creditnexus.document` | `finos.creditnexus.agreement` |
| `ViewPortfolio` | View portfolio overview | `fdc3.portfolio`, `finos.creditnexus.portfolio` | `finos.creditnexus.portfolio` |
| `GenerateLMATemplate` | Generate LMA document from agreement/loan | `finos.creditnexus.agreement`, `finos.creditnexus.loan` | `finos.creditnexus.generatedDocument` |
| `ShareWorkflowLink` | Share workflow link | `finos.creditnexus.workflow` | `finos.creditnexus.workflow` |
| `ProcessWorkflowLink` | Process received workflow link | `finos.creditnexus.workflow` | `finos.creditnexus.workflow` |
| `ViewInstrument` | Focus on instrument/symbol (Trading, Order Form, Stock Prediction) | `fdc3.instrument`, `finos.creditnexus.instrument` | `fdc3.instrument` |
| `ViewStockPrediction` | Open stock prediction for symbol (Chronos/technical) | `finos.creditnexus.stockPrediction`, `fdc3.instrument` | `finos.creditnexus.stockPrediction` |
| `ViewPredictionMarket` | Focus Polymarket-style SFP market | `finos.creditnexus.predictionMarket` | `finos.creditnexus.predictionMarket` |
| `ViewAgentResult` | Open LangAlpha/DeepResearch/PeopleHub result | `finos.creditnexus.agentResult` | `finos.creditnexus.agentResult` |

### Raises (Outgoing)

| Intent | Description | Context Types |
|--------|-------------|---------------|
| `ViewChart` | Request chart visualization | `fdc3.timeRange` |
| `ViewInstrument` | View instrument details | `fdc3.instrument`, `finos.creditnexus.instrument` |
| `ViewStockPrediction` | View stock prediction | `finos.creditnexus.stockPrediction`, `fdc3.instrument` |
| `ViewPredictionMarket` | View prediction market | `finos.creditnexus.predictionMarket` |
| `ViewAgentResult` | View agent analysis result | `finos.creditnexus.agentResult` |

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

### `finos.creditnexus.instrument`
Instrument/symbol for trading; CDM- and fdc3.instrument-aligned.
- `type` (const) - "finos.creditnexus.instrument"
- `id.ticker`, `id.symbol` - Ticker/symbol
- `name`, `exchange` - Optional
- `signal` - Optional: "bullish", "bearish", "neutral"

### `finos.creditnexus.stockPrediction`
Stock prediction result (Chronos/technical).
- `type` (const) - "finos.creditnexus.stockPrediction"
- `symbol` (required) - Ticker
- `timeframe` - "daily", "hourly", "15min"
- `strategy`, `forecast`, `signal`, `prediction_id`, `cached`

### `finos.creditnexus.predictionMarket`
Polymarket-style SFP / prediction market.
- `type` (const) - "finos.creditnexus.predictionMarket"
- `market_id` (required)
- `question`, `outcome_type`, `deal_id`, `sfp_id`, `resolved_at`, `resolution_outcome`

### `finos.creditnexus.agentResult`
LangAlpha/DeepResearch/PeopleHub analysis result.
- `type` (const) - "finos.creditnexus.agentResult"
- `analysis_id` (required), `agent_type` (required): "langalpha" | "deep_research" | "peoplehub"
- `query`, `summary`, `symbols[]`, `recommendations[]`, `deal_id`

### `finos.creditnexus.loan`, `finos.creditnexus.workflow`, `finos.creditnexus.generatedDocument`
See `openfin/fdc3-intents.json` `customConfig.contextTypes`. `finos.cdm.landUse` and `finos.cdm.greenFinanceAssessment` are used for satellite/green finance.

## App Channels

### `creditnexus.workflow`
Workflow state updates and approval requests/responses.
- Broadcasts: `finos.creditnexus.agreement`, `finos.creditnexus.approvalResult`, `finos.creditnexus.workflow`
- Listens for: `finos.creditnexus.approvalResult`, `finos.creditnexus.workflow`

### `creditnexus.extraction`
Document extraction progress and completion events.
- Broadcasts: `finos.creditnexus.agreement`
- Listens for: `finos.creditnexus.document`

### `creditnexus.portfolio`
Portfolio analytics updates.
- Broadcasts: `finos.creditnexus.portfolio`, `finos.creditnexus.esgData`
- Listens for: `finos.creditnexus.portfolio`

### `creditnexus.trading`
Instrument, stock prediction, order context (Alpaca, Chronos).
- Broadcasts: `fdc3.instrument`, `finos.creditnexus.instrument`, `finos.creditnexus.stockPrediction`
- Listens for: `fdc3.instrument`, `finos.creditnexus.instrument`, `finos.creditnexus.stockPrediction`

### `creditnexus.predictionMarket`
Polymarket-style SFP and prediction market context.
- Broadcasts: `finos.creditnexus.predictionMarket`
- Listens for: `finos.creditnexus.predictionMarket`

## Deployment

### Prerequisites
1. OpenFin Runtime (automatically downloaded when using "stable" version)
2. Application deployed and accessible via HTTPS (required for production)
3. Manifest files hosted on a web-accessible server

### Local Development

1. Start your CreditNexus application locally
2. Replace `${APP_URL}` in all JSON files with your local URL (e.g., `http://localhost:8000`)
3. Launch OpenFin using RVM (Runtime Version Manager) - no CLI needed:
   ```powershell
   # Windows (PowerShell)
   .\scripts\launch_openfin.ps1
   
   # Or simply open the manifest URL in your browser:
   # http://localhost:8000/openfin/app.json
   ```
   
   The OpenFin Runtime will be downloaded automatically by RVM if not already installed.

**Note**: 
- The deprecated `openfin-cli` package has been removed. Launch is now handled via RVM.
- For local development, the app will launch but some FDC3 features may show warnings about insecure connections. This is expected for HTTP URLs.

### Production Deployment

1. Deploy your CreditNexus application to a production URL with HTTPS
2. Replace `${APP_URL}` with your production domain:
   ```bash
   sed -i 's|\${APP_URL}|https://josephrp.github.io/creditnexus|g' openfin/*.json
   ```
3. Ensure manifests are served with correct MIME types (application/json)
4. Register the app in your OpenFin App Directory using `fdc3-intents.json`
5. Launch via RVM (users can open the manifest URL directly, or use a script):
   ```bash
   # Users can simply open the manifest URL in their browser:
   # https://josephrp.github.io/creditnexus/openfin/app.json
   # RVM will handle runtime download and app launch automatically
   ```

### Serving Manifests from CreditNexus

The CreditNexus backend serves the OpenFin manifest files from the `/openfin/` static directory. Ensure your backend is configured to serve static files from this location.

## Integration with OpenFin Workspace

To add CreditNexus to OpenFin Workspace:

1. Add the app directory entry from `fdc3-intents.json` to your workspace app directory
2. The app will appear in the Workspace dock and home screen
3. Users can raise intents to CreditNexus from other FDC3-compliant apps

## Troubleshooting

### "Port Discovery is taking a while"
This usually means the OpenFin runtime is downloading for the first time. Wait for it to complete. Check the RVM log at:
```
%LocalAppData%\openfin\logs\rvm.log
```

### "Not able to fetch the required assets"
- Verify your manifest URL is accessible
- Check that the runtime version exists (using "stable" avoids this issue)
- Ensure no firewall is blocking OpenFin CDN downloads

### FDC3 not working
- Verify runtime version is 29.108.73 or later for FDC3 2.0
- Check that `fdc3InteropApi: "2.0"` is in the platform config
- Ensure your app is properly registered in the FDC3 app directory

## FDC3 Compliance

This configuration follows:
- FDC3 2.0 App Directory specification
- FINOS CDM for financial data structures
- OpenFin platform best practices

All context types use the `finos.creditnexus.*` namespace to avoid conflicts with standard FDC3 context types.
