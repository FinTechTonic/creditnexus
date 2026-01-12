import { useState, useCallback } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useToast } from '@/components/ui/toast';

interface UploadResponse {
  status: string;
  agreement?: any;
  message?: string;
  extracted_text: string;
}

interface CreateLoanAssetRequest {
  loan_id: string;
  title: string;
  document_text: string;
}

interface GreenFinanceMetrics {
  location_type?: string;
  air_quality_index?: number;
  composite_sustainability_score?: number;
  sustainability_components?: {
    vegetation_health?: number;
    air_quality?: number;
    urban_activity?: number;
    green_infrastructure?: number;
    pollution_levels?: number;
  };
  osm_metrics?: {
    building_count?: number;
    road_density?: number;
    building_density?: number;
    green_infrastructure_coverage?: number;
  };
  air_quality?: {
    pm25?: number;
    pm10?: number;
    no2?: number;
    data_source?: string;
  };
  location_confidence?: number;
}

interface LoanAsset {
  id: number;
  loan_id: string;
  collateral_address?: string;
  geo_lat?: number;
  geo_lon?: number;
  risk_status: string;
  last_verified_score?: number;
  spt_threshold?: number;
  current_interest_rate?: number;
  // Green Finance Metrics (Enhanced Satellite Verification)
  location_type?: string;
  air_quality_index?: number;
  composite_sustainability_score?: number;
  green_finance_metrics?: GreenFinanceMetrics;
}

interface AuditResult {
  stages_completed: string[];
  loan_asset?: LoanAsset;
}

interface CreateLoanAssetResponse {
  status: string;
  message: string;
  loan_asset: LoanAsset;
  audit: AuditResult;
}

interface VerificationStatusResponse {
  loan_id: string;
  risk_status: string;
  ndvi_score?: number;
  spt_threshold?: number;
  last_verified_at?: string;
  verification_error?: string;
}

export function useVerification() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { addToast } = useToast();

  const uploadAndExtract = useCallback(async (file: File): Promise<UploadResponse | null> => {
    try {
      setLoading(true);
      setError(null);

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetchWithAuth('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: { message: 'Upload failed' } }));
        throw new Error(errorData.detail?.message || 'Upload failed');
      }

      const data: UploadResponse = await response.json();
      
      addToast({
        title: 'Upload successful',
        description: 'File uploaded and extracted successfully',
        type: 'success',
      });

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload file';
      setError(errorMessage);
      addToast({
        title: 'Upload failed',
        description: errorMessage,
        type: 'error',
      });
      return null;
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  const createLoanAsset = useCallback(async (
    request: CreateLoanAssetRequest
  ): Promise<CreateLoanAssetResponse | null> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetchWithAuth('/api/loan-assets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: { message: 'Verification failed' } }));
        throw new Error(errorData.detail?.message || 'Verification failed');
      }

      const data: CreateLoanAssetResponse = await response.json();
      
      addToast({
        title: 'Verification complete',
        description: data.message || 'Loan asset created and verified',
        type: 'success',
      });

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to verify loan asset';
      setError(errorMessage);
      addToast({
        title: 'Verification failed',
        description: errorMessage,
        type: 'error',
      });
      return null;
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  const getLoanAsset = useCallback(async (assetId: number): Promise<LoanAsset | null> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetchWithAuth(`/api/loan-assets/${assetId}`);

      if (!response.ok) {
        throw new Error('Failed to fetch loan asset');
      }

      const data = await response.json();
      return data.loan_asset;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch loan asset';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const verifyLoanAsset = useCallback(async (assetId: number): Promise<any> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetchWithAuth(`/api/loan-assets/${assetId}/verify`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: { message: 'Verification failed' } }));
        throw new Error(errorData.detail?.message || 'Verification failed');
      }

      const data = await response.json();
      
      addToast({
        title: 'Verification complete',
        description: data.message || 'Loan asset verified',
        type: 'success',
      });

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to verify loan asset';
      setError(errorMessage);
      addToast({
        title: 'Verification failed',
        description: errorMessage,
        type: 'error',
      });
      return null;
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  const getVerificationStatus = useCallback(async (assetId: number): Promise<VerificationStatusResponse | null> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetchWithAuth(`/api/loan-assets/${assetId}/status`);

      if (!response.ok) {
        throw new Error('Failed to fetch verification status');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch verification status';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    uploadAndExtract,
    createLoanAsset,
    getLoanAsset,
    verifyLoanAsset,
    getVerificationStatus,
    loading,
    error,
  };
}
