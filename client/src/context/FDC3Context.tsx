import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { Context, Listener, DesktopAgent, Channel, IntentResolution, IntentHandler as FDC3IntentHandler } from '@finos/fdc3';

export interface ESGKPITarget {
  kpi_type: string;
  target_value: number;
  current_value?: number;
  unit: string;
  margin_adjustment_bps: number;
}

export interface Party {
  id: string;
  name: string;
  role: string;
  lei?: string;
  legal_name?: string; // Alternative name field
  address?: string; // Address field for CdmDataPreview
}

export interface Facility {
  facility_name: string;
  commitment_amount: { amount: number; currency: string };
  interest_terms: {
    rate_option: { benchmark: string; spread_bps: number };
    payment_frequency: { period: string; period_multiplier: number };
  };
  maturity_date: string;
  spread_bps?: number; // Direct access for convenience
  facility_identification?: { facility_name: string }; // For CdmDataPreview
  facility_type?: string; // For CdmDataPreview
}

export interface CreditAgreementData {
  agreement_date?: string;
  parties?: Party[];
  facilities?: Facility[];
  governing_law?: string;
  sustainability_linked?: boolean;
  esg_kpi_targets?: ESGKPITarget[];
  deal_id?: string;
  loan_identification_number?: string;
  extraction_status?: string;
  document_text?: string;
  is_accounting_document?: boolean;
}

export interface CreditNexusLoanContext extends Context {
  type: 'finos.creditnexus.loan';
  id?: {
    LIN?: string;
    DealID?: string;
  };
  loan: CreditAgreementData;
}

export interface AgreementContext extends Context {
  type: 'finos.creditnexus.agreement';
  id: {
    agreementId: string;
    version?: number;
  };
  name?: string;
  borrower?: string;
  agreementDate?: string;
  totalCommitment?: {
    amount: number;
    currency: string;
  };
  workflowStatus?: 'draft' | 'under_review' | 'approved' | 'published';
  facilities?: Facility[];
  parties?: Party[];
}

export interface DocumentContext extends Context {
  type: 'finos.creditnexus.document';
  id?: {
    documentId: string;
  };
  name?: string;
  content: string;
  mimeType?: string;
}

export interface PortfolioContext extends Context {
  type: 'finos.creditnexus.portfolio';
  id?: {
    portfolioId: string;
  };
  name?: string;
  agreementIds?: string[];
  totalCommitment?: {
    amount: number;
    currency: string;
  };
  agreementCount?: number;
}

export interface ApprovalResultContext extends Context {
  type: 'finos.creditnexus.approvalResult';
  agreementId: string;
  approved: boolean;
  approver?: string;
  timestamp?: string;
  comments?: string;
  newStatus?: 'draft' | 'under_review' | 'approved' | 'published' | 'rejected';
}

export interface GeneratedDocumentContext extends Context {
  type: 'finos.creditnexus.generatedDocument';
  id?: {
    documentId: string;
    templateId?: number;
  };
  template?: {
    id: number;
    code: string;
    name: string;
    category: string;
  };
  sourceCdmData?: CreditAgreementData;
  generatedAt?: string;
  filePath?: string;
  status?: string;
}

export interface ESGDataContext extends Context {
  type: 'finos.creditnexus.esgData';
  agreementId?: string;
  environmentalScore?: number;
  socialScore?: number;
  governanceScore?: number;
  overallScore?: number;
  greenLoanIndicators?: string[];
  sustainabilityLinkedTerms?: boolean;
}

export interface LandUseContext extends Context {
  type: 'finos.cdm.landUse';
  id: { internalID: string };
  classification: string;
  complianceStatus: 'COMPLIANT' | 'WARNING' | 'BREACH';
  lastInferenceConfidence: number;
  cloudCover: number;
}

export interface GreenFinanceAssessmentContext extends Context {
  type: 'finos.cdm.greenFinanceAssessment';
  id: { transactionId: string };
  location: {
    lat: number;
    lon: number;
    type: 'urban' | 'suburban' | 'rural';
  };
  environmentalMetrics: {
    airQualityIndex: number;
    pm25?: number;
    pm10?: number;
    no2?: number;
  };
  sustainabilityScore: number;
  sdgAlignment?: {
    sdg_11?: number;
    sdg_13?: number;
    sdg_15?: number;
    overall_alignment: number;
  };
  assessedAt: string;
}

export interface WorkflowLinkContext extends Context {
  type: 'finos.creditnexus.workflow';
  id: {
    workflowId: string;
  };
  workflowType: string; // verification, notarization, document_review, etc.
  linkPayload: string; // Encrypted payload
  metadata?: {
    title?: string;
    description?: string;
    dealId?: number;
    documentId?: number;
    senderInfo?: {
      user_id?: number;
      email?: string;
      name?: string;
    };
    receiverInfo?: {
      user_id?: number;
      email?: string;
      name?: string;
    };
    expiresAt?: string;
    filesIncluded?: number;
  };
}

/** Standard FDC3 instrument (inbound from other apps). */
export interface Fdc3InstrumentContext extends Context {
  type: 'fdc3.instrument';
  id?: { ticker?: string; RIC?: string; ISIN?: string; CUSIP?: string; BBG?: string };
  name?: string;
}

/** Instrument/symbol for trading; CDM- and fdc3.instrument-aligned. */
export interface InstrumentContext extends Context {
  type: 'finos.creditnexus.instrument';
  id?: { ticker?: string; symbol?: string };
  name?: string;
  exchange?: string;
  signal?: 'bullish' | 'bearish' | 'neutral';
}

/** Stock prediction (Chronos/technical): symbol, timeframe, forecast, signal. */
export interface StockPredictionContext extends Context {
  type: 'finos.creditnexus.stockPrediction';
  symbol: string;
  timeframe?: 'daily' | 'hourly' | '15min';
  strategy?: string;
  forecast?: number[];
  signal?: 'bullish' | 'bearish' | 'neutral';
  prediction_id?: number;
  cached?: boolean;
}

/** Polymarket-style SFP / prediction market. */
export interface PredictionMarketContext extends Context {
  type: 'finos.creditnexus.predictionMarket';
  market_id: string;
  question?: string;
  outcome_type?: string;
  deal_id?: number;
  sfp_id?: string | null;
  resolved_at?: string | null;
  resolution_outcome?: string | null;
}

/** Deal Signature Tracking Context */
export interface DealSignatureContext extends Context {
  type: 'finos.creditnexus.dealSignature';
  id: {
    dealId: string;
  };
  signatureStatus: string;
  requiredSignatures: number;
  completedSignatures: number;
  signatureProgress: number;
}

/** Deal Documentation Tracking Context */
export interface DealDocumentationContext extends Context {
  type: 'finos.creditnexus.dealDocumentation';
  id: {
    dealId: string;
  };
  documentationStatus: string;
  requiredDocuments: number;
  completedDocuments: number;
  documentationProgress: number;
}

/** Deal Compliance Context */
export interface DealComplianceContext extends Context {
  type: 'finos.creditnexus.dealCompliance';
  id: {
    dealId: string;
  };
  complianceStatus: string;
  signatureStatus: string;
  documentationStatus: string;
}

/** LangAlpha/DeepResearch/PeopleHub result; symbols and recommendations for cross-linking. */
export interface AgentResultContext extends Context {
  type: 'finos.creditnexus.agentResult';
  analysis_id: string;
  agent_type: 'langalpha' | 'deep_research' | 'peoplehub';
  query?: string;
  summary?: string;
  symbols?: string[];
  recommendations?: string[];
  deal_id?: number | null;
}

export type CreditNexusContext =
  | CreditNexusLoanContext
  | AgreementContext
  | DocumentContext
  | PortfolioContext
  | DealSignatureContext
  | DealDocumentationContext
  | DealComplianceContext
  | ApprovalResultContext
  | ESGDataContext
  | LandUseContext
  | GreenFinanceAssessmentContext
  | WorkflowLinkContext
  | GeneratedDocumentContext
  | Fdc3InstrumentContext
  | InstrumentContext
  | StockPredictionContext
  | PredictionMarketContext
  | AgentResultContext;

export type IntentName =
  | 'ViewLoanAgreement'
  | 'ApproveLoanAgreement'
  | 'ViewESGAnalytics'
  | 'ExtractCreditAgreement'
  | 'ViewPortfolio'
  | 'GenerateLMATemplate'
  | 'ShareWorkflowLink'
  | 'ProcessWorkflowLink'
  | 'ViewInstrument'
  | 'ViewStockPrediction'
  | 'ViewPredictionMarket'
  | 'ViewAgentResult';

export type IntentHandler = FDC3IntentHandler;

interface AppChannels {
  workflow: Channel | null;
  extraction: Channel | null;
  portfolio: Channel | null;
  trading: Channel | null;
  predictionMarket: Channel | null;
}

interface FDC3ContextValue {
  isAvailable: boolean;
  context: CreditNexusContext | null;
  broadcast: (ctx: CreditNexusContext) => Promise<void>;
  clearContext: () => void;
  raiseIntent: (intent: IntentName, ctx: Context) => Promise<IntentResolution | null>;
  addIntentListener: (intent: IntentName, handler: IntentHandler) => Promise<Listener | null>;
  broadcastOnChannel: (channelName: keyof AppChannels, ctx: Context) => Promise<void>;
  appChannels: AppChannels;
  onIntentReceived: (callback: (intent: IntentName, context: Context) => void) => void;
  pendingIntent: { intent: IntentName; context: Context } | null;
  clearPendingIntent: () => void;
  broadcastWorkflowLink: (workflowLink: WorkflowLinkContext) => Promise<void>;
  listenForWorkflowLinks: (callback: (context: WorkflowLinkContext) => void) => Promise<Listener | null>;
}

const FDC3Context = createContext<FDC3ContextValue | null>(null);

export function FDC3Provider({ children }: { children: ReactNode }) {
  const [isAvailable, setIsAvailable] = useState(false);
  const [context, setContext] = useState<CreditNexusContext | null>(null);
  const [appChannels, setAppChannels] = useState<AppChannels>({
    workflow: null,
    extraction: null,
    portfolio: null,
    trading: null,
    predictionMarket: null,
  });
  const [pendingIntent, setPendingIntent] = useState<{ intent: IntentName; context: Context } | null>(null);
  const [intentCallback, setIntentCallback] = useState<((intent: IntentName, context: Context) => void) | null>(null);

  useEffect(() => {
    const available = typeof window !== 'undefined' && !!window.fdc3;
    setIsAvailable(available);

    if (available && window.fdc3) {
      const fdc3 = window.fdc3 as DesktopAgent;
      const subscriptions: Listener[] = [];

      const initializeChannels = async () => {
        try {
          const workflowChannel = await fdc3.getOrCreateChannel('creditnexus.workflow');
          const extractionChannel = await fdc3.getOrCreateChannel('creditnexus.extraction');
          const portfolioChannel = await fdc3.getOrCreateChannel('creditnexus.portfolio');
          const tradingChannel = await fdc3.getOrCreateChannel('creditnexus.trading');
          const predictionMarketChannel = await fdc3.getOrCreateChannel('creditnexus.predictionMarket');

          setAppChannels({
            workflow: workflowChannel,
            extraction: extractionChannel,
            portfolio: portfolioChannel,
            trading: tradingChannel,
            predictionMarket: predictionMarketChannel,
          });

          console.log('[FDC3] App channels initialized');
        } catch (error) {
          console.warn('[FDC3] Failed to initialize app channels:', error);
        }
      };

      const setupContextListeners = async () => {
        try {
          const loanListener = await fdc3.addContextListener('finos.creditnexus.loan', (ctx: Context) => {
            setContext(ctx as CreditNexusLoanContext);
          });
          subscriptions.push(loanListener);

          const agreementListener = await fdc3.addContextListener('finos.creditnexus.agreement', (ctx: Context) => {
            setContext(ctx as AgreementContext);
          });
          subscriptions.push(agreementListener);

          const documentListener = await fdc3.addContextListener('finos.creditnexus.document', (ctx: Context) => {
            setContext(ctx as DocumentContext);
          });
          subscriptions.push(documentListener);

          const portfolioListener = await fdc3.addContextListener('finos.creditnexus.portfolio', (ctx: Context) => {
            setContext(ctx as PortfolioContext);
          });
          subscriptions.push(portfolioListener);

          const workflowLinkListener = await fdc3.addContextListener('finos.creditnexus.workflow', (ctx: Context) => {
            setContext(ctx as WorkflowLinkContext);
          });
          subscriptions.push(workflowLinkListener);

          const fdc3InstrumentListener = await fdc3.addContextListener('fdc3.instrument', (ctx: Context) => {
            setContext(ctx as Fdc3InstrumentContext);
          });
          subscriptions.push(fdc3InstrumentListener);

          const instrumentListener = await fdc3.addContextListener('finos.creditnexus.instrument', (ctx: Context) => {
            setContext(ctx as InstrumentContext);
          });
          subscriptions.push(instrumentListener);

          const stockPredictionListener = await fdc3.addContextListener('finos.creditnexus.stockPrediction', (ctx: Context) => {
            setContext(ctx as StockPredictionContext);
          });
          subscriptions.push(stockPredictionListener);

          const predictionMarketListener = await fdc3.addContextListener('finos.creditnexus.predictionMarket', (ctx: Context) => {
            setContext(ctx as PredictionMarketContext);
          });
          subscriptions.push(predictionMarketListener);

          const agentResultListener = await fdc3.addContextListener('finos.creditnexus.agentResult', (ctx: Context) => {
            setContext(ctx as AgentResultContext);
          });
          subscriptions.push(agentResultListener);

          console.log('[FDC3] Context listeners registered');
        } catch (error) {
          console.warn('[FDC3] Failed to set up context listeners:', error);
        }
      };

      initializeChannels();
      setupContextListeners();

      return () => {
        subscriptions.forEach(listener => listener.unsubscribe());
      };
    } else {
      console.log('[FDC3 Mock] FDC3 not available, using mock mode for inter-app communication');
    }
  }, []);

  const broadcast = useCallback(async (loanContext: CreditNexusContext) => {
    // Validate context before broadcasting
    if (!loanContext || !loanContext.type) {
      const error = new Error('Context must have a type property');
      console.error('[FDC3] Invalid context:', error, loanContext);
      throw error;
    }

    // Validate context type matches known types
    const validTypes = [
      'finos.creditnexus.loan',
      'finos.creditnexus.agreement',
      'finos.creditnexus.document',
      'finos.creditnexus.portfolio',
      'finos.creditnexus.approvalResult',
      'finos.creditnexus.esgData',
      'finos.creditnexus.workflow',
      'finos.creditnexus.generatedDocument',
      'finos.creditnexus.instrument',
      'finos.creditnexus.stockPrediction',
      'finos.creditnexus.predictionMarket',
      'finos.creditnexus.agentResult',
      'finos.cdm.landUse',
      'finos.cdm.greenFinanceAssessment',
      'fdc3.instrument',
    ];
    
    if (!validTypes.includes(loanContext.type)) {
      console.warn(`[FDC3] Unknown context type: ${loanContext.type}. Broadcasting anyway.`);
    }

    setContext(loanContext);

    if (isAvailable && window.fdc3) {
      // Retry logic for failed broadcasts
      let retries = 2;
      let lastError: Error | null = null;
      
      while (retries >= 0) {
        try {
          await window.fdc3.broadcast(loanContext as Context);
          console.log('[FDC3] Broadcast successful:', loanContext.type, loanContext);
          return; // Success, exit retry loop
        } catch (error) {
          lastError = error instanceof Error ? error : new Error(String(error));
          console.error(`[FDC3] Broadcast failed (${2 - retries + 1}/3):`, lastError);
          
          if (retries > 0) {
            // Wait before retry (exponential backoff: 100ms, 200ms)
            await new Promise(resolve => setTimeout(resolve, (3 - retries) * 100));
          }
          retries--;
        }
      }
      
      // All retries failed
      console.error('[FDC3] Broadcast failed after all retries:', lastError);
      throw lastError || new Error('Broadcast failed after retries');
    } else {
      console.log('[FDC3 Mock] Broadcasting context:', loanContext.type, loanContext);
    }
  }, [isAvailable]);

  const clearContext = useCallback(() => {
    setContext(null);
  }, []);

  const raiseIntent = useCallback(async (intent: IntentName, ctx: Context): Promise<IntentResolution | null> => {
    if (isAvailable && window.fdc3) {
      try {
        const resolution = await window.fdc3.raiseIntent(intent, ctx);
        console.log('[FDC3] Intent raised:', intent, resolution);
        return resolution;
      } catch (error) {
        console.error('[FDC3] Failed to raise intent:', error);
        return null;
      }
    } else {
      console.log('[FDC3 Mock] Raising intent:', intent, ctx);
      return null;
    }
  }, [isAvailable]);

  const addIntentListener = useCallback(async (intent: IntentName, handler: IntentHandler): Promise<Listener | null> => {
    if (isAvailable && window.fdc3) {
      try {
        const listener = await window.fdc3.addIntentListener(intent, handler);
        console.log('[FDC3] Intent listener added:', intent);
        return listener;
      } catch (error) {
        console.error('[FDC3] Failed to add intent listener:', error);
        return null;
      }
    } else {
      console.log('[FDC3 Mock] Adding intent listener:', intent);
      return null;
    }
  }, [isAvailable]);

  const broadcastOnChannel = useCallback(async (channelName: keyof AppChannels, ctx: Context): Promise<void> => {
    const channel = appChannels[channelName];
    if (channel) {
      try {
        await channel.broadcast(ctx);
        console.log(`[FDC3] Broadcast on ${channelName} channel:`, ctx);
      } catch (error) {
        console.error(`[FDC3] Failed to broadcast on ${channelName} channel:`, error);
      }
    } else if (isAvailable) {
      console.warn(`[FDC3] Channel ${channelName} not available`);
    } else {
      console.log(`[FDC3 Mock] Broadcasting on ${channelName} channel:`, ctx);
    }
  }, [appChannels, isAvailable]);

  const onIntentReceived = useCallback((callback: (intent: IntentName, context: Context) => void) => {
    setIntentCallback(() => callback);
  }, []);

  const clearPendingIntent = useCallback(() => {
    setPendingIntent(null);
  }, []);

  const broadcastWorkflowLink = useCallback(async (workflowLink: WorkflowLinkContext) => {
    if (isAvailable && window.fdc3) {
      try {
        await window.fdc3.broadcast(workflowLink as Context);
        console.log('[FDC3] Workflow link broadcast successful:', workflowLink);
      } catch (error) {
        console.error('[FDC3] Workflow link broadcast failed:', error);
      }
    } else {
      console.log('[FDC3 Mock] Broadcasting workflow link:', workflowLink);
    }
  }, [isAvailable]);

  const listenForWorkflowLinks = useCallback(async (
    callback: (context: WorkflowLinkContext) => void
  ): Promise<Listener | null> => {
    if (isAvailable && window.fdc3) {
      try {
        const listener = await window.fdc3.addContextListener('finos.creditnexus.workflow', (ctx: Context) => {
          callback(ctx as WorkflowLinkContext);
        });
        console.log('[FDC3] Workflow link listener added');
        return listener;
      } catch (error) {
        console.error('[FDC3] Failed to add workflow link listener:', error);
        return null;
      }
    } else {
      console.log('[FDC3 Mock] Adding workflow link listener');
      return null;
    }
  }, [isAvailable]);

  useEffect(() => {
    if (!isAvailable || !window.fdc3) return;

    const fdc3 = window.fdc3 as DesktopAgent;
    const listeners: Listener[] = [];

    const setupIntentListeners = async () => {
      const intents: IntentName[] = [
        'ViewLoanAgreement',
        'ApproveLoanAgreement',
        'ViewESGAnalytics',
        'ExtractCreditAgreement',
        'ViewPortfolio',
        'GenerateLMATemplate',
        'ShareWorkflowLink',
        'ProcessWorkflowLink',
        'ViewInstrument',
        'ViewStockPrediction',
        'ViewPredictionMarket',
        'ViewAgentResult',
      ];

      for (const intent of intents) {
        try {
          const listener = await fdc3.addIntentListener(intent, (ctx: Context) => {
            console.log(`[FDC3] Received intent: ${intent}`, ctx);
            setPendingIntent({ intent, context: ctx });
            if (intentCallback) {
              intentCallback(intent, ctx);
            }
          });
          listeners.push(listener);
        } catch (error) {
          console.warn(`[FDC3] Failed to add listener for ${intent}:`, error);
        }
      }

      console.log('[FDC3] Intent listeners registered for all supported intents');
    };

    setupIntentListeners();

    return () => {
      listeners.forEach(listener => listener.unsubscribe());
    };
  }, [isAvailable, intentCallback]);

  return (
    <FDC3Context.Provider
      value={{
        isAvailable,
        context,
        broadcast,
        clearContext,
        raiseIntent,
        addIntentListener,
        broadcastOnChannel,
        appChannels,
        onIntentReceived,
        pendingIntent,
        clearPendingIntent,
        broadcastWorkflowLink,
        listenForWorkflowLinks,
      }}
    >
      {children}
    </FDC3Context.Provider>
  );
}

export function useFDC3() {
  const ctx = useContext(FDC3Context);
  if (!ctx) {
    throw new Error('useFDC3 must be used within an FDC3Provider');
  }
  return ctx;
}

export function createAgreementContext(
  agreementId: string,
  data: Partial<AgreementContext>
): AgreementContext {
  return {
    type: 'finos.creditnexus.agreement',
    id: { agreementId, version: data.id?.version },
    name: data.name,
    borrower: data.borrower,
    agreementDate: data.agreementDate,
    totalCommitment: data.totalCommitment,
    workflowStatus: data.workflowStatus,
    facilities: data.facilities,
    parties: data.parties,
  };
}

export function createDocumentContext(
  content: string,
  documentId?: string,
  name?: string
): DocumentContext {
  return {
    type: 'finos.creditnexus.document',
    id: documentId ? { documentId } : undefined,
    name,
    content,
    mimeType: 'text/plain',
  };
}

export function createPortfolioContext(
  portfolioId: string,
  data: Partial<PortfolioContext>
): PortfolioContext {
  return {
    type: 'finos.creditnexus.portfolio',
    id: { portfolioId },
    name: data.name,
    agreementIds: data.agreementIds,
    totalCommitment: data.totalCommitment,
    agreementCount: data.agreementCount,
  };
}

export function createApprovalResultContext(
  agreementId: string,
  approved: boolean,
  data?: Partial<ApprovalResultContext>
): ApprovalResultContext {
  return {
    type: 'finos.creditnexus.approvalResult',
    agreementId,
    approved,
    approver: data?.approver,
    timestamp: data?.timestamp || new Date().toISOString(),
    comments: data?.comments,
    newStatus: data?.newStatus,
  };
}

export function createESGDataContext(
  data: Partial<ESGDataContext>
): ESGDataContext {
  return {
    type: 'finos.creditnexus.esgData',
    agreementId: data.agreementId,
    environmentalScore: data.environmentalScore,
    socialScore: data.socialScore,
    governanceScore: data.governanceScore,
    overallScore: data.overallScore,
    greenLoanIndicators: data.greenLoanIndicators,
    sustainabilityLinkedTerms: data.sustainabilityLinkedTerms,
  };
}

export function createWorkflowLinkContext(
  workflowId: string,
  workflowType: string,
  linkPayload: string,
  metadata?: WorkflowLinkContext['metadata']
): WorkflowLinkContext {
  return {
    type: 'finos.creditnexus.workflow',
    id: {
      workflowId,
    },
    workflowType,
    linkPayload,
    metadata,
  };
}

export function createInstrumentContext(symbol: string, data?: Partial<InstrumentContext>): InstrumentContext {
  return {
    type: 'finos.creditnexus.instrument',
    id: { ticker: symbol, symbol },
    name: data?.name ?? symbol,
    exchange: data?.exchange,
    signal: data?.signal,
  };
}

export function createStockPredictionContext(
  symbol: string,
  data: Partial<StockPredictionContext>
): StockPredictionContext {
  return {
    type: 'finos.creditnexus.stockPrediction',
    symbol,
    timeframe: data.timeframe,
    strategy: data.strategy,
    forecast: data.forecast,
    signal: data.signal,
    prediction_id: data.prediction_id,
    cached: data.cached,
  };
}

export function createPredictionMarketContext(
  marketId: string,
  data: Partial<PredictionMarketContext>
): PredictionMarketContext {
  return {
    type: 'finos.creditnexus.predictionMarket',
    market_id: marketId,
    question: data.question,
    outcome_type: data.outcome_type,
    deal_id: data.deal_id,
    sfp_id: data.sfp_id ?? null,
    resolved_at: data.resolved_at ?? null,
    resolution_outcome: data.resolution_outcome ?? null,
  };
}

export function createDealSignatureContext(
  dealId: number,
  status: {
    signature_status: string;
    required_signatures: Array<any>;
    completed_signatures: Array<any>;
    signature_progress: number;
  }
): DealSignatureContext {
  return {
    type: 'finos.creditnexus.dealSignature',
    id: { dealId: String(dealId) },
    signatureStatus: status.signature_status,
    requiredSignatures: status.required_signatures?.length || 0,
    completedSignatures: status.completed_signatures?.length || 0,
    signatureProgress: status.signature_progress || 0
  };
}

export function createDealDocumentationContext(
  dealId: number,
  status: {
    documentation_status: string;
    required_documents: Array<any>;
    completed_documents: Array<any>;
    documentation_progress: number;
  }
): DealDocumentationContext {
  return {
    type: 'finos.creditnexus.dealDocumentation',
    id: { dealId: String(dealId) },
    documentationStatus: status.documentation_status,
    requiredDocuments: status.required_documents?.length || 0,
    completedDocuments: status.completed_documents?.length || 0,
    documentationProgress: status.documentation_progress || 0
  };
}

export function createDealComplianceContext(
  dealId: number,
  summary: {
    compliance_status: string;
    signature_status: {
      signature_status: string;
    };
    documentation_status: {
      documentation_status: string;
    };
  }
): DealComplianceContext {
  return {
    type: 'finos.creditnexus.dealCompliance',
    id: { dealId: String(dealId) },
    complianceStatus: summary.compliance_status,
    signatureStatus: summary.signature_status?.signature_status || 'unknown',
    documentationStatus: summary.documentation_status?.documentation_status || 'unknown'
  };
}

export function createAgentResultContext(
  analysisId: string,
  agentType: AgentResultContext['agent_type'],
  data: Partial<AgentResultContext>
): AgentResultContext {
  return {
    type: 'finos.creditnexus.agentResult',
    analysis_id: analysisId,
    agent_type: agentType,
    query: data.query,
    summary: data.summary,
    symbols: data.symbols,
    recommendations: data.recommendations,
    deal_id: data.deal_id ?? null,
  };
}
