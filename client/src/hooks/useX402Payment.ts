import { useState, useCallback } from 'react';
import { useWallet } from '@/context/WalletContext';
import { fetchWithAuth } from '@/context/AuthContext';

export interface PaymentRequest {
  amount: string;
  currency: string;
  payment_type: string;
  payer_info?: {
    wallet_address?: string;
    user_id?: number;
    name?: string;
  };
  receiver_info?: {
    wallet_address?: string;
    contract_address?: string;
    name?: string;
  };
  facilitator_url?: string;
  notarization_id?: number;
  deal_id?: number;
  pool_id?: number;
  tranche_id?: number;
}

export interface PaymentResponse {
  status: 'payment_required' | 'paid' | 'failed' | 'processing';
  payment_id?: string;
  amount?: string;
  currency?: string;
  facilitator_url?: string;
  transaction_hash?: string;
  message?: string;
  error?: string;
}

export interface UseX402PaymentReturn {
  processPayment: (
    endpoint: string,
    paymentRequest: PaymentRequest,
    options?: {
      method?: 'POST' | 'PUT' | 'PATCH';
      body?: any;
      skipWalletCheck?: boolean;
    }
  ) => Promise<PaymentResponse>;
  isProcessing: boolean;
  error: string | null;
  lastTransactionHash: string | null;
}

/**
 * Hook for processing x402 payments.
 * 
 * Handles:
 * - Wallet connection check
 * - Payment request/response flow
 * - x402 facilitator integration
 * - Transaction hash tracking
 * - Error handling
 */
export function useX402Payment(): UseX402PaymentReturn {
  const { isConnected, account, connect, signMessage } = useWallet();
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastTransactionHash, setLastTransactionHash] = useState<string | null>(null);

  const processPayment = useCallback(
    async (
      endpoint: string,
      paymentRequest: PaymentRequest,
      options: {
        method?: 'POST' | 'PUT' | 'PATCH';
        body?: any;
        skipWalletCheck?: boolean;
      } = {}
    ): Promise<PaymentResponse> => {
      setIsProcessing(true);
      setError(null);

      try {
        // Check wallet connection
        if (!options.skipWalletCheck) {
          if (!isConnected || !account) {
            // Try to connect wallet
            try {
              await connect();
            } catch (err) {
              throw new Error('Wallet connection required. Please connect your MetaMask wallet.');
            }
          }
        }

        // Prepare payment payload with wallet address
        const paymentPayload = {
          ...paymentRequest,
          payer_info: {
            ...paymentRequest.payer_info,
            wallet_address: account || paymentRequest.payer_info?.wallet_address,
          },
        };

        // Make initial request (may return 402 Payment Required)
        const response = await fetchWithAuth(endpoint, {
          method: options.method || 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            ...options.body,
            payment_payload: paymentPayload,
          }),
        });

        // Handle 402 Payment Required
        if (response.status === 402) {
          const paymentData = await response.json();
          
          // If facilitator URL is provided, redirect to x402 facilitator
          if (paymentData.facilitator_url) {
            // In a real implementation, you would:
            // 1. Open x402 facilitator in new window/tab
            // 2. Wait for payment completion callback
            // 3. Retry the original request with payment_payload
            
            // For now, return payment required status
            return {
              status: 'payment_required',
              payment_id: paymentData.payment_id,
              amount: paymentData.amount,
              currency: paymentData.currency,
              facilitator_url: paymentData.facilitator_url,
              message: 'Payment required. Please complete payment via x402 facilitator.',
            };
          }

          return {
            status: 'payment_required',
            ...paymentData,
            message: paymentData.message || 'Payment required to complete this action.',
          };
        }

        // Handle other errors
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: 'Payment processing failed' }));
          throw new Error(errorData.message || errorData.detail || `HTTP ${response.status}`);
        }

        // Payment successful
        const data = await response.json();
        
        if (data.transaction_hash) {
          setLastTransactionHash(data.transaction_hash);
        }

        return {
          status: 'paid',
          transaction_hash: data.transaction_hash,
          payment_id: data.payment_id,
          message: data.message || 'Payment processed successfully',
        };
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Payment processing failed';
        setError(errorMessage);
        return {
          status: 'failed',
          error: errorMessage,
          message: errorMessage,
        };
      } finally {
        setIsProcessing(false);
      }
    },
    [isConnected, account, connect]
  );

  return {
    processPayment,
    isProcessing,
    error,
    lastTransactionHash,
  };
}
