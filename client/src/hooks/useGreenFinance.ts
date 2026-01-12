import { useState, useCallback } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useToast } from '@/components/ui/toast';
import type { 
  GreenFinanceAssessment, 
  GreenFinanceAssessmentRequest,
  UrbanSustainabilityAssessment,
  EmissionsCompliance,
  SDGAlignment
} from '@/types/greenFinance';

export function useGreenFinance() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addToast } = useToast();

  const assessGreenFinance = useCallback(async (
    request: GreenFinanceAssessmentRequest
  ): Promise<GreenFinanceAssessment | null> => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        location_lat: request.location_lat.toString(),
        location_lon: request.location_lon.toString(),
      });
      
      if (request.transaction_id) {
        params.append('transaction_id', request.transaction_id);
      }
      if (request.deal_id) {
        params.append('deal_id', request.deal_id.toString());
      }
      if (request.loan_asset_id) {
        params.append('loan_asset_id', request.loan_asset_id.toString());
      }

      const response = await fetchWithAuth(`/api/green-finance/assess?${params.toString()}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: { message: 'Assessment failed' } }));
        throw new Error(errorData.detail?.message || 'Green finance assessment failed');
      }

      const data = await response.json();
      
      addToast({
        title: 'Assessment complete',
        description: 'Green finance assessment completed successfully',
        type: 'success',
      });

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to assess green finance';
      setError(errorMessage);
      addToast({
        title: 'Assessment failed',
        description: errorMessage,
        type: 'error',
      });
      return null;
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  const assessUrbanSustainability = useCallback(async (
    location_lat: number,
    location_lon: number
  ): Promise<UrbanSustainabilityAssessment | null> => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        location_lat: location_lat.toString(),
        location_lon: location_lon.toString(),
      });

      const response = await fetchWithAuth(`/api/green-finance/urban-sustainability?${params.toString()}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: { message: 'Assessment failed' } }));
        throw new Error(errorData.detail?.message || 'Urban sustainability assessment failed');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to assess urban sustainability';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const monitorEmissionsCompliance = useCallback(async (
    location_lat: number,
    location_lon: number
  ): Promise<EmissionsCompliance | null> => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        location_lat: location_lat.toString(),
        location_lon: location_lon.toString(),
      });

      const response = await fetchWithAuth(`/api/green-finance/emissions-compliance?${params.toString()}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: { message: 'Monitoring failed' } }));
        throw new Error(errorData.detail?.message || 'Emissions compliance monitoring failed');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to monitor emissions compliance';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const evaluateSDGAlignment = useCallback(async (
    location_lat: number,
    location_lon: number,
    sustainability_components?: Record<string, number>,
    green_finance_metrics?: any
  ): Promise<SDGAlignment | null> => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        location_lat: location_lat.toString(),
        location_lon: location_lon.toString(),
      });

      const body: any = {};
      if (sustainability_components) {
        body.sustainability_components = sustainability_components;
      }
      if (green_finance_metrics) {
        body.green_finance_metrics = green_finance_metrics;
      }

      const response = await fetchWithAuth(`/api/green-finance/sdg-alignment?${params.toString()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: Object.keys(body).length > 0 ? JSON.stringify(body) : undefined,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: { message: 'Evaluation failed' } }));
        throw new Error(errorData.detail?.message || 'SDG alignment evaluation failed');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to evaluate SDG alignment';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const listAssessments = useCallback(async (
    dealId?: number,
    loanAssetId?: number,
    page: number = 1,
    limit: number = 20
  ): Promise<GreenFinanceAssessment[]> => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      });
      
      if (dealId) {
        params.append('deal_id', dealId.toString());
      }
      if (loanAssetId) {
        params.append('loan_asset_id', loanAssetId.toString());
      }

      const response = await fetchWithAuth(`/api/green-finance/assessments?${params.toString()}`);

      if (!response.ok) {
        throw new Error('Failed to fetch assessments');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch assessments';
      setError(errorMessage);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const getAssessment = useCallback(async (
    assessmentId: number
  ): Promise<GreenFinanceAssessment | null> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetchWithAuth(`/api/green-finance/assessments/${assessmentId}`);

      if (!response.ok) {
        throw new Error('Failed to fetch assessment');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch assessment';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    assessGreenFinance,
    assessUrbanSustainability,
    monitorEmissionsCompliance,
    evaluateSDGAlignment,
    listAssessments,
    getAssessment,
    loading,
    error,
  };
}
