import { useEffect, useState, useCallback } from 'react';
import type { Context, Listener } from '@finos/fdc3';

// Custom context type for CreditNexus loan data
export interface CreditNexusLoanContext extends Context {
  type: 'fdc3.creditnexus.loan';
  loan?: {
    agreementDate?: string;
    parties?: Array<{ name: string; role: string }>;
    facilities?: Array<{ name: string; amount: number; currency: string }>;
  };
}

export function useFDC3() {
  const [isAvailable, setIsAvailable] = useState(false);
  const [context, setContext] = useState<CreditNexusLoanContext | null>(null);

  useEffect(() => {
    // Check if FDC3 is available
    const available = typeof window !== 'undefined' && !!window.fdc3;
    setIsAvailable(available);

    if (available && window.fdc3) {
      let subscription: Listener | null = null;

      // Listen for incoming loan context
      window.fdc3.addContextListener('fdc3.creditnexus.loan', (ctx: Context) => {
        setContext(ctx as CreditNexusLoanContext);
      }).then((listener: Listener) => {
        subscription = listener;
      }).catch(() => {
        // Ignore errors
      });

      return () => {
        if (subscription) {
          subscription.unsubscribe();
        }
      };
    } else {
      // Mock mode: log to console
      console.log('[FDC3 Mock] FDC3 not available, using mock mode');
    }
  }, []);

  const broadcast = useCallback((loanContext: CreditNexusLoanContext) => {
    if (isAvailable && window.fdc3) {
      window.fdc3.broadcast(loanContext as Context)
        .then(() => {
          console.log('[FDC3] Broadcast successful:', loanContext);
        })
        .catch((error) => {
          console.error('[FDC3] Broadcast failed:', error);
        });
    } else {
      // Mock mode: log to console
      console.log('[FDC3 Mock] Would broadcast:', loanContext);
    }
  }, [isAvailable]);

  return {
    isAvailable,
    context,
    broadcast,
  };
}

