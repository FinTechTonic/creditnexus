import { useState, useCallback } from 'react';
import type { PaymentRequiredPayload } from '@/components/payments/PaymentRequiredModal';

interface UsePaymentRequiredReturn {
  showPaymentModal: (payload: PaymentRequiredPayload, endpoint?: string, retryBody?: any) => void;
  hidePaymentModal: () => void;
  paymentPayload: PaymentRequiredPayload | null;
  isOpen: boolean;
  endpoint: string | undefined;
  retryBody: any;
}

/**
 * Hook for managing payment required modals globally.
 * 
 * When an API call returns 402, use this hook to show the PaymentRequiredModal
 * with the appropriate payment options (MetaMask, RevenueCat, Plaid).
 */
export function usePaymentRequired(): UsePaymentRequiredReturn {
  const [isOpen, setIsOpen] = useState(false);
  const [paymentPayload, setPaymentPayload] = useState<PaymentRequiredPayload | null>(null);
  const [endpoint, setEndpoint] = useState<string | undefined>(undefined);
  const [retryBody, setRetryBody] = useState<any>(undefined);

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
  }, []);

  return {
    showPaymentModal,
    hidePaymentModal,
    paymentPayload,
    isOpen,
    endpoint,
    retryBody,
  };
}

/**
 * Helper function to check if a response is a 402 Payment Required.
 * Extracts payment payload and returns it in a standardized format.
 */
export function extractPaymentPayload(response: Response, endpoint?: string): PaymentRequiredPayload | null {
  if (response.status !== 402) {
    return null;
  }

  // Response will be parsed by the caller
  return {
    endpoint,
  };
}

/**
 * Wrapper for fetchWithAuth that automatically handles 402 responses.
 * 
 * Usage:
 *   const { fetchWithPaymentHandling } = usePaymentRequired();
 *   const response = await fetchWithPaymentHandling('/api/banking/accounts');
 */
export function createFetchWithPaymentHandling(
  showPaymentModal: (payload: PaymentRequiredPayload, endpoint?: string, retryBody?: any) => void,
  baseFetch: (url: string, options?: RequestInit) => Promise<Response>
) {
  return async (url: string, options?: RequestInit): Promise<Response> => {
    const response = await baseFetch(url, options);

    if (response.status === 402) {
      try {
        const payload = await response.json();
        showPaymentModal(
          payload,
          url,
          options?.body ? JSON.parse(options.body as string) : undefined
        );
      } catch (e) {
        console.error('Failed to parse 402 response:', e);
        showPaymentModal({
          message: 'Payment required to continue.',
          endpoint: url,
        });
      }
    }

    return response;
  };
}
