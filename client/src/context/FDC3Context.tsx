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
}

export interface Facility {
  facility_name: string;
  commitment_amount: { amount: number; currency: string };
  interest_terms: {
    rate_option: { benchmark: string; spread_bps: number };
    payment_frequency: { period: string; period_multiplier: number };
  };
  maturity_date: string;
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
}

export interface CreditNexusLoanContext extends Context {
  type: 'fdc3.creditnexus.loan';
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

export type CreditNexusContext =
  | CreditNexusLoanContext
  | AgreementContext
  | DocumentContext
  | PortfolioContext
  | ApprovalResultContext
  | ESGDataContext
  | LandUseContext;

export type IntentName =
  | 'ViewLoanAgreement'
  | 'ApproveLoanAgreement'
  | 'ViewESGAnalytics'
  | 'ExtractCreditAgreement'
  | 'ViewPortfolio';

export type IntentHandler = FDC3IntentHandler;

interface AppChannels {
  workflow: Channel | null;
  extraction: Channel | null;
  portfolio: Channel | null;
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
}

const FDC3Context = createContext<FDC3ContextValue | null>(null);

export function FDC3Provider({ children }: { children: ReactNode }) {
  const [isAvailable, setIsAvailable] = useState(false);
  const [context, setContext] = useState<CreditNexusContext | null>(null);
  const [appChannels, setAppChannels] = useState<AppChannels>({
    workflow: null,
    extraction: null,
    portfolio: null,
  });
  const [pendingIntent, setPendingIntent] = useState<{ intent: IntentName; context: Context } | null>(null);
  const [intentCallback, setIntentCallback] = useState<((intent: IntentName, context: Context) => void) | null>(null);

  useEffect(() => {
    const available = typeof window !== 'undefined' && !!window.fdc3;
    setIsAvailable(available);

    if (available && window.fdc3) {
      const fdc3 = window.fdc3 as DesktopAgent;
      let subscriptions: Listener[] = [];

      const initializeChannels = async () => {
        try {
          const workflowChannel = await fdc3.getOrCreateChannel('creditnexus.workflow');
          const extractionChannel = await fdc3.getOrCreateChannel('creditnexus.extraction');
          const portfolioChannel = await fdc3.getOrCreateChannel('creditnexus.portfolio');

          setAppChannels({
            workflow: workflowChannel,
            extraction: extractionChannel,
            portfolio: portfolioChannel,
          });

          console.log('[FDC3] App channels initialized');
        } catch (error) {
          console.warn('[FDC3] Failed to initialize app channels:', error);
        }
      };

      const setupContextListeners = async () => {
        try {
          const loanListener = await fdc3.addContextListener('fdc3.creditnexus.loan', (ctx: Context) => {
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
    setContext(loanContext);

    if (isAvailable && window.fdc3) {
      try {
        await window.fdc3.broadcast(loanContext as Context);
        console.log('[FDC3] Broadcast successful:', loanContext);
      } catch (error) {
        console.error('[FDC3] Broadcast failed:', error);
      }
    } else {
      console.log('[FDC3 Mock] Broadcasting context:', loanContext);
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
