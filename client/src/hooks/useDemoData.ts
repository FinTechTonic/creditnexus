/**
 * React hook for managing demo data operations.
 * 
 * Provides methods for seeding demo data, generating deals, checking status,
 * and resetting demo data.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useToast } from '@/components/ui/toast';

export interface DemoSeedRequest {
  seed_users?: boolean;
  seed_templates?: boolean;
  seed_policies?: boolean;
  seed_policy_templates?: boolean;
  generate_deals?: boolean;
  deal_count?: number;
  dry_run?: boolean;
}

export interface DemoSeedResponse {
  status: string;
  created: Record<string, number>;
  updated: Record<string, number>;
  errors: Record<string, string[]>;
  preview?: Record<string, any>;
  user_credentials?: Array<{
    email: string;
    password: string;
    role: string;
    display_name: string;
  }>;
}

export interface SeedingStatus {
  stage: string;
  progress: number;
  total: number;
  current: number;
  status: string;
  errors: string[];
  started_at: string | null;
  completed_at: string | null;
}

export interface SeedingStatusResponse {
  stage?: string;
  progress: number;
  total: number;
  current: number;
  errors: string[];
  status: string;
  started_at: string | null;
  completed_at: string | null;
  all_stages?: Record<string, SeedingStatus>;
}

export interface DemoDeal {
  id: number;
  deal_id: string;
  deal_type: string;
  status: string;
  borrower_name?: string;
  total_commitment?: number;
  currency?: string;
  created_at: string;
  deal_data?: {
    loan_amount?: number;
    interest_rate?: number;
  };
}

export interface UseDemoDataReturn {
  // Seeding methods
  seedData: (request: DemoSeedRequest) => Promise<DemoSeedResponse>;
  generateDeals: (count: number) => Promise<DemoSeedResponse>;
  getSeedingStatus: (stage?: string) => Promise<SeedingStatusResponse>;
  resetDemoData: () => Promise<{ status: string; message: string }>;
  getGeneratedDeals: (params?: {
    page?: number;
    limit?: number;
    status?: string;
    deal_type?: string;
    search?: string;
  }) => Promise<{ deals: DemoDeal[]; total: number }>;
  
  // State
  loading: boolean;
  error: string | null;
  seedingStatus: Record<string, SeedingStatus>;
  isPolling: boolean;
  
  // Control
  startPolling: () => void;
  stopPolling: () => void;
}

/**
 * Hook for managing demo data operations.
 * 
 * @returns Demo data management functions and state
 * 
 * @example
 * ```tsx
 * const { seedData, loading, error } = useDemoData();
 * 
 * const handleSeed = async () => {
 *   const result = await seedData({
 *     seed_users: true,
 *     seed_templates: true,
 *     generate_deals: true,
 *     deal_count: 12
 *   });
 *   console.log('Seeded:', result);
 * };
 * ```
 */
export function useDemoData(): UseDemoDataReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [seedingStatus, setSeedingStatus] = useState<Record<string, SeedingStatus>>({});
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Use ref for seedingStatus to avoid stale closure in polling interval
  const seedingStatusRef = useRef<Record<string, SeedingStatus>>({});
  seedingStatusRef.current = seedingStatus;
  const { addToast } = useToast();

  /**
   * Seed demo data (users, templates, policies).
   */
  const seedData = useCallback(async (request: DemoSeedRequest): Promise<DemoSeedResponse> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetchWithAuth('/api/demo/seed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to seed demo data');
      }
      
      const data: DemoSeedResponse = await response.json();
      
      // Show success/error notifications
      if (data.status === 'success') {
        const totalCreated = Object.values(data.created).reduce((sum, count) => sum + count, 0);
        addToast(`Successfully seeded ${totalCreated} items`, 'success');
      } else if (data.status === 'partial') {
        const totalCreated = Object.values(data.created).reduce((sum, count) => sum + count, 0);
        const totalErrors = Object.values(data.errors).reduce((sum, errs) => sum + errs.length, 0);
        addToast(`Seeded ${totalCreated} items with ${totalErrors} error(s)`, 'warning');
      } else {
        addToast('Failed to seed demo data', 'error');
      }
      
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to seed demo data';
      setError(errorMessage);
      addToast(errorMessage, 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  /**
   * Generate demo deals.
   */
  const generateDeals = useCallback(async (count: number): Promise<DemoSeedResponse> => {
    setLoading(true);
    setError(null);
    
    try {
      // For now, we'll use the seed endpoint with generate_deals flag
      // TODO: Create dedicated endpoint for deal generation if needed
      const response = await fetchWithAuth('/api/demo/seed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          seed_users: false,
          seed_templates: false,
          seed_policies: false,
          seed_policy_templates: false,
          generate_deals: true,
          deal_count: count,
          dry_run: false,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to generate deals');
      }
      
      const data: DemoSeedResponse = await response.json();
      
      // Show success notification
      if (data.status === 'success') {
        addToast(`Successfully generated ${count} deal(s)`, 'success');
      } else if (data.status === 'partial') {
        addToast(`Generated deals with some errors`, 'warning');
      } else {
        addToast('Failed to generate deals', 'error');
      }
      
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate deals';
      setError(errorMessage);
      addToast(errorMessage, 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  /**
   * Get seeding status for a specific stage or all stages.
   */
  const getSeedingStatus = useCallback(async (stage?: string): Promise<SeedingStatusResponse> => {
    try {
      const params = new URLSearchParams();
      if (stage) {
        params.append('stage', stage);
      }
      
      const response = await fetchWithAuth(`/api/demo/seed/status?${params.toString()}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to get seeding status');
      }
      
      const data: SeedingStatusResponse = await response.json();
      
      // Update local state
      if (data.all_stages) {
        setSeedingStatus(data.all_stages);
      } else if (data.stage) {
        setSeedingStatus(prev => ({
          ...prev,
          [data.stage!]: {
            stage: data.stage!,
            progress: data.progress,
            total: data.total,
            current: data.current,
            status: data.status,
            errors: data.errors,
            started_at: data.started_at,
            completed_at: data.completed_at,
          },
        }));
      }
      
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get seeding status';
      setError(errorMessage);
      throw err;
    }
  }, []);

  /**
   * Reset demo data (delete all demo deals and related data).
   */
  const resetDemoData = useCallback(async (): Promise<{ status: string; message: string }> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetchWithAuth('/api/demo/seed/reset', {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to reset demo data');
      }
      
      const data = await response.json();
      
      // Show success notification
      if (data.status === 'success') {
        addToast(data.message || 'Demo data reset successfully', 'success');
      } else {
        addToast('Failed to reset demo data', 'error');
      }
      
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reset demo data';
      setError(errorMessage);
      addToast(errorMessage, 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  /**
   * Get generated demo deals with pagination and filters.
   */
  const getGeneratedDeals = useCallback(async (params?: {
    page?: number;
    limit?: number;
    status?: string;
    deal_type?: string;
    search?: string;
  }): Promise<{ deals: DemoDeal[]; total: number }> => {
    setLoading(true);
    setError(null);
    
    try {
      const queryParams = new URLSearchParams();
      queryParams.append('is_demo', 'true');
      
      if (params?.page) {
        queryParams.append('offset', ((params.page - 1) * (params.limit || 10)).toString());
      }
      if (params?.limit) {
        queryParams.append('limit', params.limit.toString());
      }
      if (params?.status && params.status !== 'all') {
        queryParams.append('status', params.status);
      }
      if (params?.deal_type && params.deal_type !== 'all') {
        queryParams.append('deal_type', params.deal_type);
      }
      if (params?.search) {
        queryParams.append('search', params.search);
      }
      
      const response = await fetchWithAuth(`/api/deals?${queryParams.toString()}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to fetch deals');
      }
      
      const data = await response.json();
      return {
        deals: data.deals || [],
        total: data.total || 0,
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch deals';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Start polling for seeding status updates.
   */
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      return; // Already polling
    }
    
    setIsPolling(true);
    pollingIntervalRef.current = setInterval(async () => {
      try {
        await getSeedingStatus();
        
        // Use ref to get fresh seedingStatus (avoid stale closure)
        const currentStatus = seedingStatusRef.current;
        
        // Stop polling if all stages are completed or failed
        const allCompleted = Object.values(currentStatus).every(
          s => s.status === 'completed' || s.status === 'failed'
        );
        
        if (allCompleted && Object.keys(currentStatus).length > 0) {
          stopPolling();
        }
      } catch (err) {
        console.error('Error polling seeding status:', err);
      }
    }, 2000); // Poll every 2 seconds
  }, [getSeedingStatus]);

  /**
   * Stop polling for seeding status updates.
   */
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
      setIsPolling(false);
    }
  }, []);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    seedData,
    generateDeals,
    getSeedingStatus,
    resetDemoData,
    getGeneratedDeals,
    loading,
    error,
    seedingStatus,
    isPolling,
    startPolling,
    stopPolling,
  };
}
