# Verification Auto-Hydration & LangAlpha Integration Plan
## Remove Demo Tab, Enable Agreement-Based Auto-Hydration, and Integrate LangAlpha

**Status**: Enhancement Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 4-6 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This plan removes the "Verification Demo" tab and transforms verification into an auto-hydrating system that:
1. **Seeds from Agreement Data**: Accepts any credit agreement and automatically extracts deal information
2. **Auto-Hydration**: Automatically finds data, runs checks, and performs verification
3. **Multi-Deal Type Support**: Supports equities, commodities, unlisted assets, securitized Polymarket deals, etc.
4. **LangAlpha Integration**: LangAlpha bot available by default in verification interface
5. **Unified Verification Dashboard**: Single verification interface for all deal types

---

## Current State Analysis

### Existing Verification System

**Components**:
- `client/src/components/VerificationDashboard.tsx` - Main verification UI
- `app/services/verification_service.py` - Verification service
- `app/agents/verifier.py` - Satellite verification agent
- `client/src/components/DesktopAppLayout.tsx` - Contains "Verification Demo" tab (line 108-113)

**Current Flow**:
1. User uploads PDF credit agreement
2. Legal extraction finds borrower, collateral address, SPTs
3. Geocoding converts address to coordinates
4. Satellite verification fetches imagery and runs NDVI
5. Compliance/Breach determination

**Limitations**:
- Demo-only workflow (separate tab)
- Deal-type specific (only loan assets)
- Manual workflow initiation
- No automatic data discovery
- LangAlpha not integrated

---

## Project 1: Remove Verification Demo Tab

### Activity 1.1: Remove Demo Tab from Sidebar

**File**: `client/src/components/DesktopAppLayout.tsx` (UPDATE)

#### Task 1.1.1: Remove Verification Demo Entry
**Lines**: ~108-113

**Subtasks**:
1. **Line 108-113**: Remove verification-demo entry from sidebarApps array
   ```typescript
   // REMOVE THIS:
   {
     id: 'verification-demo',
     name: 'Verification Demo',
     icon: <Sparkles className="h-5 w-5 text-indigo-400" />,
     description: 'Live Verification Workflow',
     requiredPermission: PERMISSION_SATELLITE_VIEW,
   },
   ```

2. **Line ~1046**: Remove verification-demo route handler
   ```typescript
   // REMOVE:
   {activeApp === 'verification-demo' && <VerificationDashboard />}
   ```

### Activity 1.2: Update Navigation References

**File**: `client/src/components/MainNavigation.tsx` (UPDATE if needed)

**File**: `client/src/router/Routes.tsx` (UPDATE if needed)

**Subtasks**:
1. Remove any routes pointing to `/verification-demo`
2. Update any navigation links to point to unified verification dashboard

---

## Project 2: Agreement-Based Auto-Hydration System

### Activity 2.1: Enhanced Agreement Parser

**File**: `app/services/agreement_parser_service.py` (NEW)

#### Task 2.1.1: Multi-Deal Type Agreement Parser
**Lines**: 1-400

**Subtasks**:
1. **Line 1-100**: Service class with deal type detection
   ```python
   from typing import Dict, Any, Optional, List
   from enum import Enum
   from sqlalchemy.orm import Session
   from app.core.llm_client import get_chat_model
   from app.models.cdm import CreditAgreement
   
   class DealType(str, Enum):
       """Supported deal types for verification."""
       LOAN_ASSET = "loan_asset"  # Traditional loan with collateral
       EQUITY = "equity"  # Equity investment
       COMMODITY = "commodity"  # Commodity contract
       UNLISTED = "unlisted"  # Unlisted/private asset
       SECURITIZED = "securitized"  # Securitized product
       POLYMARKET = "polymarket"  # Polymarket prediction market
       STRUCTURED_PRODUCT = "structured_product"  # Structured financial product
       FIXED_INCOME = "fixed_income"  # Fixed income security
       REAL_ESTATE = "real_estate"  # Real estate investment
   
   class AgreementParserService:
       """Service for parsing agreements and detecting deal types."""
       
       def __init__(self, db: Session):
           self.db = db
           self.llm = get_chat_model(temperature=0)
       
       async def parse_agreement(
           self,
           document_text: str,
           document_id: Optional[int] = None
       ) -> Dict[str, Any]:
           """Parse agreement and extract deal information."""
           # Use existing extraction chain
           from app.chains.extraction_chain import extract_data_smart
           
           result = extract_data_smart(text=document_text)
           
           if not result.agreement:
               raise ValueError("Failed to extract agreement data")
           
           # Detect deal type
           deal_type = await self._detect_deal_type(result.agreement, document_text)
           
           # Extract deal-specific information
           deal_info = await self._extract_deal_info(result.agreement, deal_type)
           
           return {
               "agreement": result.agreement,
               "deal_type": deal_type,
               "deal_info": deal_info,
               "cdm_events": result.cdm_events or []
           }
   ```

2. **Line 101-200**: Deal type detection
   ```python
       async def _detect_deal_type(
           self,
           agreement: CreditAgreement,
           document_text: str
       ) -> DealType:
           """Detect deal type from agreement and document text."""
           from langchain_core.messages import SystemMessage, HumanMessage
           from pydantic import BaseModel, Field
           
           class DealTypeDetection(BaseModel):
               """Structured output for deal type detection."""
               deal_type: str = Field(description="Deal type: loan_asset, equity, commodity, unlisted, securitized, polymarket, structured_product, fixed_income, real_estate")
               confidence: float = Field(description="Confidence score 0-1")
               indicators: List[str] = Field(description="Key indicators that led to this classification")
           
           prompt = f"""Analyze the following credit agreement and determine the deal type.

Document Text (excerpt):
{document_text[:2000]}

Agreement Summary:
- Parties: {[p.name for p in (agreement.parties or [])]}
- Facilities: {len(agreement.facilities or [])}
- Total Amount: {agreement.total_facility_amount}

Deal Types:
- loan_asset: Traditional loan with collateral (real estate, equipment, etc.)
- equity: Equity investment or stock purchase
- commodity: Commodity contract (gold, oil, wheat, etc.)
- unlisted: Unlisted/private security or asset
- securitized: Securitized product (ABS, MBS, etc.)
- polymarket: Polymarket prediction market linked to credit event
- structured_product: Structured financial product
- fixed_income: Fixed income security (bonds, notes, etc.)
- real_estate: Real estate investment or mortgage

Determine the most appropriate deal type."""
           
           structured_llm = self.llm.with_structured_output(DealTypeDetection)
           result = await structured_llm.ainvoke([
               SystemMessage(content="You are an expert at classifying financial agreements."),
               HumanMessage(content=prompt)
           ])
           
           return DealType(result.deal_type)
   ```

3. **Line 201-300**: Deal-specific information extraction
   ```python
       async def _extract_deal_info(
           self,
           agreement: CreditAgreement,
           deal_type: DealType
       ) -> Dict[str, Any]:
           """Extract deal-specific information based on type."""
           deal_info = {
               "deal_type": deal_type.value,
               "parties": [p.name for p in (agreement.parties or [])],
               "amount": float(agreement.total_facility_amount) if agreement.total_facility_amount else None
           }
           
           if deal_type == DealType.LOAN_ASSET:
               # Extract collateral information
               deal_info["collateral"] = self._extract_collateral(agreement)
               deal_info["spt_threshold"] = self._extract_spt_threshold(agreement)
           
           elif deal_type == DealType.EQUITY:
               # Extract equity information
               deal_info["ticker"] = self._extract_ticker(agreement)
               deal_info["shares"] = self._extract_shares(agreement)
               deal_info["price"] = self._extract_price(agreement)
           
           elif deal_type == DealType.COMMODITY:
               # Extract commodity information
               deal_info["commodity_type"] = self._extract_commodity_type(agreement)
               deal_info["quantity"] = self._extract_quantity(agreement)
               deal_info["delivery_date"] = self._extract_delivery_date(agreement)
           
           elif deal_type == DealType.POLYMARKET:
               # Extract Polymarket information
               deal_info["market_id"] = self._extract_market_id(agreement)
               deal_info["resolution_condition"] = self._extract_resolution_condition(agreement)
           
           elif deal_type == DealType.SECURITIZED:
               # Extract securitization information
               deal_info["pool_id"] = self._extract_pool_id(agreement)
               deal_info["tranches"] = self._extract_tranches(agreement)
           
           # ... more deal types
           
           return deal_info
   ```

### Activity 2.2: Auto-Hydration Service

**File**: `app/services/verification_auto_hydration_service.py` (NEW)

#### Task 2.2.1: Auto-Hydration Orchestrator
**Lines**: 1-500

**Subtasks**:
1. **Line 1-150**: Service class
   ```python
   class VerificationAutoHydrationService:
       """
       Service for automatically hydrating verification data.
       
       Automatically:
       1. Finds relevant data sources
       2. Runs verification checks
       3. Performs compliance analysis
       4. Generates verification reports
       """
       
       def __init__(self, db: Session):
           self.db = db
           self.agreement_parser = AgreementParserService(db)
           self.verification_service = VerificationService(db)
           self.langalpha_service = QuantitativeAnalysisService(db)
       
       async def auto_hydrate_from_agreement(
           self,
           document_id: int,
           user_id: int,
           deal_id: Optional[int] = None
       ) -> Dict[str, Any]:
           """Auto-hydrate verification from agreement document."""
           # Load document
           document = self.db.query(Document).filter(Document.id == document_id).first()
           if not document:
               raise ValueError(f"Document {document_id} not found")
           
           # Parse agreement
           agreement_data = await self.agreement_parser.parse_agreement(
               document_text=document.extracted_text or "",
               document_id=document_id
           )
           
           deal_type = DealType(agreement_data["deal_type"])
           deal_info = agreement_data["deal_info"]
           
           # Auto-discover data sources
           data_sources = await self._discover_data_sources(deal_type, deal_info)
           
           # Run verification checks
           verification_results = await self._run_verification_checks(
               deal_type=deal_type,
               deal_info=deal_info,
               data_sources=data_sources
           )
           
           # Perform compliance analysis
           compliance_analysis = await self._perform_compliance_analysis(
               agreement_data["agreement"],
               verification_results
           )
           
           # Generate verification report
           report = await self._generate_verification_report(
               agreement_data=agreement_data,
               verification_results=verification_results,
               compliance_analysis=compliance_analysis
           )
           
           return {
               "verification_id": report["verification_id"],
               "deal_type": deal_type.value,
               "deal_info": deal_info,
               "data_sources": data_sources,
               "verification_results": verification_results,
               "compliance_analysis": compliance_analysis,
               "report": report
           }
   ```

2. **Line 151-250**: Data source discovery
   ```python
       async def _discover_data_sources(
           self,
           deal_type: DealType,
           deal_info: Dict[str, Any]
       ) -> Dict[str, Any]:
           """Discover relevant data sources for verification."""
           sources = {}
           
           if deal_type == DealType.LOAN_ASSET:
               # Discover satellite imagery sources
               if "collateral" in deal_info and "address" in deal_info["collateral"]:
                   sources["satellite"] = {
                       "provider": "sentinelhub",
                       "location": deal_info["collateral"]["address"],
                       "layers": ["NDVI", "land_use", "urban_activity"]
                   }
               
               # Discover OSM data
               sources["osm"] = {
                   "provider": "openstreetmap",
                   "location": deal_info["collateral"]["address"]
               }
           
           elif deal_type == DealType.EQUITY:
               # Discover market data sources
               if "ticker" in deal_info:
                   sources["market_data"] = {
                       "provider": "polygon",
                       "ticker": deal_info["ticker"],
                       "data_types": ["price", "volume", "fundamentals"]
                   }
               
               # Discover news sources
               sources["news"] = {
                   "provider": "serper",
                   "query": f"{deal_info.get('company_name', deal_info.get('ticker'))} financial news"
               }
           
           elif deal_type == DealType.COMMODITY:
               # Discover commodity data sources
               if "commodity_type" in deal_info:
                   sources["commodity_data"] = {
                       "provider": "yahoo_finance",
                       "symbol": self._get_commodity_symbol(deal_info["commodity_type"]),
                       "data_types": ["price", "futures"]
                   }
           
           elif deal_type == DealType.POLYMARKET:
               # Discover Polymarket data
               if "market_id" in deal_info:
                   sources["polymarket"] = {
                       "provider": "polymarket",
                       "market_id": deal_info["market_id"],
                       "data_types": ["market_data", "resolution_status"]
                   }
           
           # Always include LangAlpha for quantitative analysis
           sources["quantitative_analysis"] = {
               "provider": "langalpha",
               "enabled": True,
               "analysis_types": ["company", "market", "risk"]
           }
           
           return sources
   ```

3. **Line 251-350**: Verification checks
   ```python
       async def _run_verification_checks(
           self,
           deal_type: DealType,
           deal_info: Dict[str, Any],
           data_sources: Dict[str, Any]
       ) -> Dict[str, Any]:
           """Run verification checks based on deal type."""
           results = {}
           
           if deal_type == DealType.LOAN_ASSET:
               # Run satellite verification
               if "satellite" in data_sources:
                   from app.agents.verifier import VerifierAgent
                   verifier = VerifierAgent(self.db)
                   satellite_result = await verifier.verify_asset(
                       address=data_sources["satellite"]["location"],
                       spt_threshold=deal_info.get("spt_threshold")
                   )
                   results["satellite"] = satellite_result
           
           elif deal_type == DealType.EQUITY:
               # Run market data verification
               if "market_data" in data_sources:
                   ticker = data_sources["market_data"]["ticker"]
                   market_data = await self._fetch_market_data(ticker)
                   results["market_data"] = {
                       "current_price": market_data.get("price"),
                       "volume": market_data.get("volume"),
                       "market_cap": market_data.get("market_cap"),
                       "verified_at": datetime.utcnow().isoformat()
                   }
           
           elif deal_type == DealType.COMMODITY:
               # Run commodity price verification
               if "commodity_data" in data_sources:
                   commodity_data = await self._fetch_commodity_data(
                       data_sources["commodity_data"]["symbol"]
                   )
                   results["commodity"] = {
                       "current_price": commodity_data.get("price"),
                       "futures_price": commodity_data.get("futures_price"),
                       "verified_at": datetime.utcnow().isoformat()
                   }
           
           elif deal_type == DealType.POLYMARKET:
               # Run Polymarket verification
               if "polymarket" in data_sources:
                   from app.services.polymarket_service import PolymarketService
                   polymarket_service = PolymarketService(self.db)
                   market_data = await polymarket_service.get_market_data(
                       market_id=data_sources["polymarket"]["market_id"]
                   )
                   results["polymarket"] = market_data
           
           # Always run LangAlpha quantitative analysis
           if "quantitative_analysis" in data_sources:
               langalpha_result = await self._run_langalpha_analysis(deal_type, deal_info)
               results["quantitative_analysis"] = langalpha_result
           
           return results
   ```

4. **Line 351-450**: Compliance analysis
   ```python
       async def _perform_compliance_analysis(
           self,
           agreement: CreditAgreement,
           verification_results: Dict[str, Any]
       ) -> Dict[str, Any]:
           """Perform compliance analysis based on verification results."""
           from app.services.policy_service import PolicyService
           
           policy_service = PolicyService(self.db)
           
           # Evaluate policy compliance
           policy_result = policy_service.evaluate_facility_creation(
               credit_agreement=agreement,
               document_id=None
           )
           
           # Check verification compliance
           compliance_status = "COMPLIANT"
           compliance_issues = []
           
           if "satellite" in verification_results:
               satellite = verification_results["satellite"]
               if satellite.get("status") == "BREACH":
                   compliance_status = "BREACH"
                   compliance_issues.append({
                       "type": "satellite_verification",
                       "message": satellite.get("message"),
                       "severity": "high"
                   })
           
           if "quantitative_analysis" in verification_results:
               qa = verification_results["quantitative_analysis"]
               risk_score = qa.get("risk_score", 0)
               if risk_score > 0.7:
                   compliance_status = "WARNING"
                   compliance_issues.append({
                       "type": "high_risk",
                       "message": f"High risk score: {risk_score}",
                       "severity": "medium"
                   })
           
           return {
               "status": compliance_status,
               "policy_result": policy_result,
               "issues": compliance_issues,
               "verified_at": datetime.utcnow().isoformat()
           }
   ```

---

## Project 3: LangAlpha Integration in Verification Interface

### Activity 3.1: LangAlpha Bot Component

**File**: `client/src/components/verification/LangAlphaBot.tsx` (NEW)

#### Task 3.1.1: LangAlpha Chatbot Component
**Lines**: 1-300

**Subtasks**:
1. **Line 1-100**: Component setup
   ```typescript
   import { useState, useEffect, useCallback } from 'react';
   import { MessageSquare, Loader2, Bot } from 'lucide-react';
   import { fetchWithAuth } from '@/context/AuthContext';
   import { Button } from '@/components/ui/button';
   import { Card } from '@/components/ui/card';
   
   interface LangAlphaMessage {
     id: string;
     role: 'user' | 'assistant';
     content: string;
     timestamp: Date;
     analysis_id?: string;
     status?: 'pending' | 'running' | 'completed' | 'failed';
   }
   
   interface LangAlphaBotProps {
     dealId?: number;
     documentId?: number;
     dealType?: string;
     dealInfo?: Record<string, unknown>;
   }
   
   export function LangAlphaBot({
     dealId,
     documentId,
     dealType,
     dealInfo
   }: LangAlphaBotProps) {
     const [messages, setMessages] = useState<LangAlphaMessage[]>([
       {
         id: '1',
         role: 'assistant',
         content: `I'm LangAlpha, your quantitative analysis assistant. I can help you analyze ${dealType || 'this deal'} using market data, financial metrics, and risk analysis. What would you like to analyze?`,
         timestamp: new Date()
       }
     ]);
     const [input, setInput] = useState('');
     const [isLoading, setIsLoading] = useState(false);
     const [activeAnalysis, setActiveAnalysis] = useState<string | null>(null);
   ```

2. **Line 101-200**: Message handling with LangAlpha integration
   ```typescript
     const handleSendMessage = useCallback(async () => {
       if (!input.trim() || isLoading) return;
       
       const userMessage = input.trim();
       setInput('');
       
       // Add user message
       const newUserMessage: LangAlphaMessage = {
         id: `msg-${Date.now()}`,
         role: 'user',
         content: userMessage,
         timestamp: new Date()
       };
       setMessages(prev => [...prev, newUserMessage]);
       setIsLoading(true);
       
       try {
         // Determine analysis type from message
         const analysisType = detectAnalysisType(userMessage, dealType, dealInfo);
         
         // Launch LangAlpha analysis
         const response = await fetchWithAuth('/api/quantitative-analysis/query', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({
             query: userMessage,
             analysis_type: analysisType,
             deal_id: dealId,
             document_id: documentId,
             deal_type: dealType,
             deal_info: dealInfo
           })
         });
         
         if (response.ok) {
           const data = await response.json();
           const analysisId = data.analysis_id;
           
           // Add assistant message with analysis ID
           const assistantMessage: LangAlphaMessage = {
             id: `msg-${Date.now()}-assistant`,
             role: 'assistant',
             content: data.message || 'Analysis started. I will provide results shortly.',
             timestamp: new Date(),
             analysis_id: analysisId,
             status: 'running'
           };
           setMessages(prev => [...prev, assistantMessage]);
           setActiveAnalysis(analysisId);
           
           // Poll for results
           pollAnalysisResults(analysisId);
         }
       } catch (error) {
         console.error('LangAlpha error:', error);
       } finally {
         setIsLoading(false);
       }
     }, [input, isLoading, dealId, documentId, dealType, dealInfo]);
     
     const pollAnalysisResults = async (analysisId: string) => {
       const maxAttempts = 60; // 5 minutes max
       let attempts = 0;
       
       const poll = setInterval(async () => {
         attempts++;
         
         try {
           const response = await fetchWithAuth(`/api/quantitative-analysis/results/${analysisId}`);
           if (response.ok) {
             const data = await response.json();
             
             if (data.status === 'completed') {
               clearInterval(poll);
               
               // Update message with results
               setMessages(prev => prev.map(msg => 
                 msg.analysis_id === analysisId
                   ? {
                       ...msg,
                       content: formatAnalysisResults(data.result),
                       status: 'completed'
                     }
                   : msg
               ));
               setActiveAnalysis(null);
             } else if (data.status === 'failed') {
               clearInterval(poll);
               setMessages(prev => prev.map(msg => 
                 msg.analysis_id === analysisId
                   ? { ...msg, status: 'failed', content: 'Analysis failed' }
                   : msg
               ));
               setActiveAnalysis(null);
             }
           }
         } catch (error) {
           console.error('Poll error:', error);
         }
         
         if (attempts >= maxAttempts) {
           clearInterval(poll);
         }
       }, 5000); // Poll every 5 seconds
     };
   ```

### Activity 3.2: Update Verification Dashboard

**File**: `client/src/components/VerificationDashboard.tsx` (UPDATE)

#### Task 3.2.1: Integrate LangAlpha Bot
**Lines**: ~500-600 (in tabs section)

**Subtasks**:
1. **Line ~500**: Add LangAlpha tab
   ```typescript
   import { LangAlphaBot } from './verification/LangAlphaBot';
   
   // In TabsList, add:
   <TabsTrigger value="langalpha">
     <Bot className="w-4 h-4 mr-2" />
     LangAlpha
   </TabsTrigger>
   
   // In TabsContent, add:
   <TabsContent value="langalpha" className="flex-1 m-0 h-full p-4">
     <LangAlphaBot
       dealId={dealId}
       documentId={documentId}
       dealType={currentDealType}
       dealInfo={currentDealInfo}
     />
   </TabsContent>
   ```

2. **Line ~100**: Add state for deal type and info
   ```typescript
   const [currentDealType, setCurrentDealType] = useState<string | null>(null);
   const [currentDealInfo, setCurrentDealInfo] = useState<Record<string, unknown> | null>(null);
   ```

---

## Project 4: Unified Verification Dashboard

### Activity 4.1: Agreement Upload & Auto-Hydration

**File**: `client/src/components/VerificationDashboard.tsx` (UPDATE)

#### Task 4.1.1: Agreement Upload Flow
**Lines**: ~200-300

**Subtasks**:
1. **Line 200-250**: Add agreement upload section
   ```typescript
   const handleAgreementUpload = async (file: File) => {
     setLoading(true);
     
     try {
       // Upload document
       const formData = new FormData();
       formData.append('file', file);
       
       const uploadResponse = await fetchWithAuth('/api/documents/upload', {
         method: 'POST',
         body: formData
       });
       
       if (!uploadResponse.ok) {
         throw new Error('Upload failed');
       }
       
       const uploadData = await uploadResponse.json();
       const documentId = uploadData.document_id;
       
       // Trigger auto-hydration
       const hydrationResponse = await fetchWithAuth('/api/verification/auto-hydrate', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({
           document_id: documentId,
           deal_id: dealId
         })
       });
       
       if (hydrationResponse.ok) {
         const hydrationData = await hydrationResponse.json();
         
         // Update state with deal type and info
         setCurrentDealType(hydrationData.deal_type);
         setCurrentDealInfo(hydrationData.deal_info);
         
         // Show verification results
         setVerificationResults(hydrationData.verification_results);
         setComplianceAnalysis(hydrationData.compliance_analysis);
         
         addLog('Auto-hydration completed successfully', 'SUCCESS');
       }
     } catch (error) {
       addLog(`Auto-hydration failed: ${error}`, 'ERROR');
     } finally {
       setLoading(false);
     }
   };
   ```

---

## Project 5: API Endpoints

### Activity 5.1: Auto-Hydration Endpoint

**File**: `app/api/routes.py` (UPDATE)

#### Task 5.1.1: Add Auto-Hydration Endpoint
**Lines**: ~12000-12100

**Subtasks**:
1. **Line 12000-12100**: Auto-hydration endpoint
   ```python
   @router.post("/verification/auto-hydrate")
   async def auto_hydrate_verification(
       request: AutoHydrateRequest,
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       """Auto-hydrate verification from agreement document."""
       from app.services.verification_auto_hydration_service import VerificationAutoHydrationService
       
       service = VerificationAutoHydrationService(db)
       
       result = await service.auto_hydrate_from_agreement(
           document_id=request.document_id,
           user_id=current_user.id,
           deal_id=request.deal_id
       )
       
       return result
   ```

### Activity 5.2: LangAlpha Query Endpoint

**File**: `app/api/routes.py` (UPDATE)

#### Task 5.2.1: Add LangAlpha Query Endpoint
**Lines**: ~12100-12200

**Subtasks**:
1. **Line 12100-12200**: LangAlpha query endpoint
   ```python
   @router.post("/quantitative-analysis/query")
   async def langalpha_query(
       request: LangAlphaQueryRequest,
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       """Launch LangAlpha analysis from query."""
       from app.services.quantitative_analysis_service import QuantitativeAnalysisService
       
       service = QuantitativeAnalysisService(db)
       
       # Determine analysis type
       analysis_type = request.analysis_type or "comprehensive"
       
       # Launch analysis
       if request.deal_type == "equity" and "ticker" in (request.deal_info or {}):
           result = await service.analyze_company(
               company_name=request.deal_info.get("company_name"),
               ticker=request.deal_info.get("ticker"),
               analysis_type=analysis_type,
               deal_id=request.deal_id,
               user_id=current_user.id
           )
       else:
           # Generic query analysis
           result = await service.analyze_query(
               query=request.query,
               deal_id=request.deal_id,
               user_id=current_user.id
           )
       
       return {
           "status": "success",
           "analysis_id": result.get("analysis_id"),
           "message": "Analysis started. Results will be available shortly."
       }
   ```

---

## Implementation Checklist

### Phase 1: Remove Demo Tab (Week 1)
- [ ] Remove verification-demo from DesktopAppLayout sidebar
- [ ] Remove verification-demo route handler
- [ ] Update navigation references
- [ ] Test that verification is accessible via unified dashboard

### Phase 2: Agreement Parser (Week 2)
- [ ] Create AgreementParserService
- [ ] Implement deal type detection
- [ ] Implement deal-specific information extraction
- [ ] Add support for all deal types

### Phase 3: Auto-Hydration (Week 3-4)
- [ ] Create VerificationAutoHydrationService
- [ ] Implement data source discovery
- [ ] Implement verification checks
- [ ] Implement compliance analysis
- [ ] Add auto-hydration endpoint

### Phase 4: LangAlpha Integration (Week 5)
- [ ] Create LangAlphaBot component
- [ ] Integrate into VerificationDashboard
- [ ] Add LangAlpha query endpoint
- [ ] Test LangAlpha workflow

### Phase 5: Testing & Refinement (Week 6)
- [ ] Test with various deal types
- [ ] Test auto-hydration flow
- [ ] Test LangAlpha integration
- [ ] Performance optimization
- [ ] Documentation updates

---

## Success Criteria

1. ✅ Verification Demo tab removed from sidebar
2. ✅ Verification accepts any agreement data
3. ✅ Auto-hydration discovers data sources automatically
4. ✅ Verification checks run automatically
5. ✅ Supports all deal types (equities, commodities, unlisted, Polymarket, etc.)
6. ✅ LangAlpha bot available by default in verification interface
7. ✅ Unified verification dashboard for all deal types

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
