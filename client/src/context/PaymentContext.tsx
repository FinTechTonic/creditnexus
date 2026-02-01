import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { PaymentRequiredModal } from '@/components/payments/PaymentRequiredModal';
import type { PaymentRequiredPayload } from '@/components/payments/PaymentRequiredModal';
import { fetchWithAuth } from './AuthContext';

interface PaymentContextType {
  showPaymentModal: (payload: PaymentRequiredPayload, endpoint?: string, retryBody?: any) => void;
  hidePaymentModal: () => void;
  fetchWithPaymentHandling: (url: string, options?: RequestInit) => Promise<Response>;
}

const PaymentContext = createContext<PaymentContextType | undefined>(undefined);

export function PaymentProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [paymentPayload, setPaymentPayload] = useState<PaymentRequiredPayload | null>(null);
  const [endpoint, setEndpoint] = useState<string | undefined>(undefined);
  const [retryBody, setRetryBody] = useState<any>(undefined);
  const [retryFunction, setRetryFunction] = useState<(() => Promise<void>) | null>(null);

  const showPaymentModal = useCallback((
    payload: PaymentRequiredPayload,
    endpointParam?: string,
    retryBodyParam?: any
  ) => {
    setPaymentPayload({
      ...payload,
      endpoint: endpointParam,
      retry_body: retryBodyParam,
    });
    setEndpoint(endpointParam);
    setRetryBody(retryBodyParam);
    setIsOpen(true);
  }, []);

  const hidePaymentModal = useCallback(() => {
    setIsOpen(false);
    setPaymentPayload(null);
    setEndpoint(undefined);
    setRetryBody(undefined);
    setRetryFunction(null);
  }, []);

  const handleRetry = useCallback(async () => {
    if (retryFunction) {
      await retryFunction();
    } else if (endpoint) {
      // Retry the original request
      await fetchWithAuth(endpoint, {
        method: 'GET',
        ...(retryBody && { body: JSON.stringify(retryBody) }),
      });
    }
    hidePaymentModal();
  }, [endpoint, retryBody, retryFunction, hidePaymentModal]);

  const fetchWithPaymentHandling = useCallback(async (
    url: string,
    options?: RequestInit
  ): Promise<Response> => {
    const response = await fetchWithAuth(url, options);

    if (response.status === 402) {
      try {
        const payload = await response.json();
        const body = options?.body ? JSON.parse(options.body as string) : undefined;
        
        // Store retry function
        setRetryFunction(() => async () => {
          await fetchWithAuth(url, options);
        });
        
        showPaymentModal(
          {
            ...payload,
            payment_type: payload.payment_type || extractPaymentTypeFromUrl(url),
          },
          url,
          body
        );
      } catch (e) {
        console.error('Failed to parse 402 response:', e);
        showPaymentModal({
          message: 'Payment required to continue.',
          endpoint: url,
          payment_type: extractPaymentTypeFromUrl(url),
        });
      }
    }

    return response;
  }, [showPaymentModal]);

  return (
    <PaymentContext.Provider
      value={{
        showPaymentModal,
        hidePaymentModal,
        fetchWithPaymentHandling,
      }}
    >
      {children}
      <PaymentRequiredModal
        open={isOpen}
        payload={paymentPayload}
        onClose={hidePaymentModal}
        onRetry={handleRetry}
        onPaymentComplete={hidePaymentModal}
      />
    </PaymentContext.Provider>
  );
}

export function usePayment() {
  const context = useContext(PaymentContext);
  if (!context) {
    throw new Error('usePayment must be used within PaymentProvider');
  }
  return context;
}

function extractPaymentTypeFromUrl(url: string): string {
  if (url.includes('/banking/accounts')) return 'plaid_accounts_get';
  if (url.includes('/banking/balances')) return 'plaid_balances_get';
  if (url.includes('/banking/transactions')) return 'plaid_transactions_get';
  if (url.includes('/subscriptions/org-admin/upgrade')) return 'org_admin_upgrade';
  if (url.includes('/subscriptions/upgrade')) return 'subscription_upgrade';
  if (url.includes('/notarize')) return 'notarization_fee';
  if (url.includes('/purchase-tranche')) return 'tranche_purchase';
  if (url.includes('/settle')) return 'trade_settlement';
  if (url.includes('/disburse')) return 'loan_disbursement';
  if (url.includes('/penalty-payment')) return 'penalty_payment';
  if (url.includes('/stock-prediction')) return 'billable_feature';
  if (url.includes('/profile/extract')) return 'billable_feature';
  if (url.includes('/digitizer-chatbot/launch-workflow')) return 'billable_feature';
  if (url.includes('/business-intelligence/research-person')) return 'billable_feature';
  if (url.includes('/green-finance/assess')) return 'billable_feature';
  if (url.includes('/api/funding/request')) return 'credit_top_up'; // Server 402 includes payment_type from body
  if (url.includes('/api/credits/top-up')) return 'credit_top_up';
  if (url.includes('/api/polymarket/fund')) return 'polymarket_funding';
  return 'payment';
}
