/**
 * Asset Verification Card Component
 * 
 * Displays the live loan status with:
 * - Risk status badge (🟢 COMPLIANT / 🟠 WARNING / 🔴 BREACH)
 * - Dynamic interest rate updates
 * - FINOS CDM compliance badge
 * - NDVI score visualization
 */

import { useState, useEffect } from 'react';
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  // TrendingDown removed - unused
  Leaf,
  RefreshCw,
  MapPin,
  Clock,
  Percent,
  FileCheck,
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useLayerStore } from '@/stores/layerStore';

interface LoanAsset {
  id: number;
  loan_id: string;
  collateral_address: string | null;
  geo_lat: number | null;
  geo_lon: number | null;
  spt_data: object | null;
  last_verified_score: number | null;
  spt_threshold: number | null;
  risk_status: string;
  base_interest_rate: number | null;
  current_interest_rate: number | null;
  penalty_bps: number | null;
  created_at: string | null;
  last_verified_at: string | null;
  verification_error: string | null;
}

interface AssetVerificationCardProps {
  assetId: number;
  onVerify?: () => void;
}

const statusConfig: Record<string, { color: string; bg: string; icon: typeof CheckCircle; label: string }> = {
  COMPLIANT: {
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/20',
    icon: CheckCircle,
    label: '🟢 Compliant',
  },
  WARNING: {
    color: 'text-amber-400',
    bg: 'bg-amber-500/20',
    icon: AlertTriangle,
    label: '🟠 Warning',
  },
  BREACH: {
    color: 'text-red-400',
    bg: 'bg-red-500/20',
    icon: XCircle,
    label: '🔴 Breach',
  },
  PENDING: {
    color: 'text-slate-400',
    bg: 'bg-slate-500/20',
    icon: Clock,
    label: '⏳ Pending',
  },
  ERROR: {
    color: 'text-red-400',
    bg: 'bg-red-500/20',
    icon: AlertTriangle,
    label: '❌ Error',
  },
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Never';
  return new Date(dateStr).toLocaleString();
}

function formatNDVI(score: number | null): string {
  if (score === null) return 'N/A';
  return (score * 100).toFixed(1) + '%';
}

export function AssetVerificationCard({ assetId, onVerify }: AssetVerificationCardProps) {
  const [asset, setAsset] = useState<LoanAsset | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAsset = async () => {
    try {
      setLoading(true);
      const response = await fetchWithAuth(`/api/loan-assets/${assetId}`);
      if (response.ok) {
        const data = await response.json();
        setAsset(data.loan_asset);
        setError(null);
      } else {
        throw new Error('Failed to fetch asset');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  /** Fetch layers from API and hydrate into layer store + map overlays after audit/run. */
  const refetchAndHydrateLayers = async (id: number) => {
    try {
      const res = await fetchWithAuth(`/api/layers/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      const layers = (data.layers || []).map((l: { id: number; layer_type: string; metadata?: Record<string, unknown>; bounds?: { north?: number; south?: number; east?: number; west?: number }; thumbnail_url?: string; created_at?: string }) => ({
        id: l.id,
        type: l.layer_type,
        metadata: l.metadata || {},
        bounds: l.bounds && l.bounds.north != null && l.bounds.south != null && l.bounds.east != null && l.bounds.west != null
          ? { north: l.bounds.north, south: l.bounds.south, east: l.bounds.east, west: l.bounds.west }
          : { north: 0, south: 0, east: 0, west: 0 },
        thumbnail_url: l.thumbnail_url,
        created_at: l.created_at
      }));
      const store = useLayerStore.getState();
      store.setLayers(id, layers);
      const overlays = store.mapState.overlays;
      layers.forEach((layer, i) => {
        if (!overlays.find((o) => o.layerId === String(layer.id))) {
          store.addOverlay({
            layerId: String(layer.id),
            opacity: 0.7,
            visible: true,
            blendingMode: 'normal',
            zIndex: overlays.length + i
          });
        }
      });
    } catch (e) {
      console.error('Failed to hydrate layers after verification', e);
    }
  };

  const runVerification = async () => {
    try {
      setVerifying(true);
      const response = await fetchWithAuth(`/api/audit/run/${assetId}`, {
        method: 'POST',
      });
      if (response.ok) {
        const data = await response.json();
        setAsset(data.loan_asset);
        onVerify?.();
        // Hydrate layers into the layer store so MapView/LayerOverlays can display them
        await refetchAndHydrateLayers(assetId);
      } else {
        // Get error message from response
        const errorData = await response.json().catch(() => ({ detail: 'Verification failed' }));
        const errorMessage = errorData.detail?.message || errorData.detail || 'Verification failed';
        throw new Error(errorMessage);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    fetchAsset();
    // Poll for updates every 30 seconds
    const interval = setInterval(fetchAsset, 30000);
    return () => clearInterval(interval);
  }, [assetId]);

  if (loading && !asset) {
    return (
      <div className="bg-[var(--surface-panel)]/50 rounded-xl p-6 border border-[var(--surface-panel-border)]/50 animate-pulse">
        <div className="h-6 bg-[var(--surface-panel-border)] rounded w-1/3 mb-4"></div>
        <div className="h-20 bg-[var(--surface-panel-border)] rounded mb-4"></div>
        <div className="h-4 bg-[var(--surface-panel-border)] rounded w-2/3"></div>
      </div>
    );
  }

  if (error && !asset) {
    return (
      <div className="bg-red-500/10 rounded-xl p-6 border border-red-500/30">
        <p className="text-red-400">Error: {error}</p>
      </div>
    );
  }

  if (!asset) return null;

  const status = statusConfig[asset.risk_status] || statusConfig.PENDING;
  const StatusIcon = status.icon;
  const hasRateIncrease = asset.current_interest_rate && asset.base_interest_rate && 
    asset.current_interest_rate > asset.base_interest_rate;

  return (
    <div className="bg-[var(--surface-panel)] rounded-xl border border-[var(--surface-panel-border)] overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${status.bg}`}>
            <StatusIcon className={`w-5 h-5 ${status.color}`} />
          </div>
          <div>
            <h3 className="font-semibold text-[var(--color-foreground)]">Loan Asset #{asset.loan_id}</h3>
            <p className="text-sm text-[var(--color-muted-foreground)]">Ground Truth Status</p>
          </div>
        </div>
        
        {/* CDM Badge */}
        {asset.spt_data && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--color-primary)]/20 rounded-full border border-[var(--color-primary)]/30">
            <FileCheck className="w-4 h-4 text-[var(--color-primary)]" />
            <span className="text-xs font-medium text-[var(--color-primary)]">FINOS CDM Compliant</span>
          </div>
        )}
      </div>

      {/* Status Banner */}
      <div className={`px-4 py-3 ${status.bg}`}>
        <span className={`text-lg font-bold ${status.color}`}>{status.label}</span>
      </div>

      {/* Metrics Grid */}
      <div className="p-4 grid grid-cols-2 gap-4">
        {/* NDVI Score */}
        <div className="bg-[var(--surface-panel-secondary)] rounded-lg p-3">
          <div className="flex items-center gap-2 text-[var(--color-muted-foreground)] text-sm mb-1">
            <Leaf className="w-4 h-4" />
            <span>NDVI Score</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-foreground)]">{formatNDVI(asset.last_verified_score)}</p>
          <p className="text-xs text-[var(--color-muted-foreground)]">Threshold: {formatNDVI(asset.spt_threshold)}</p>
        </div>

        {/* Interest Rate */}
        <div className="bg-[var(--surface-panel-secondary)] rounded-lg p-3">
          <div className="flex items-center gap-2 text-[var(--color-muted-foreground)] text-sm mb-1">
            <Percent className="w-4 h-4" />
            <span>Interest Rate</span>
            {hasRateIncrease && <TrendingUp className="w-4 h-4 text-red-400" />}
          </div>
          <p className={`text-2xl font-bold ${hasRateIncrease ? 'text-red-400' : 'text-[var(--color-foreground)]'}`}>
            {asset.current_interest_rate?.toFixed(2)}%
          </p>
          {hasRateIncrease && (
            <p className="text-xs text-red-400">
              Base: {asset.base_interest_rate?.toFixed(2)}% (+{asset.penalty_bps} bps penalty)
            </p>
          )}
        </div>
      </div>

      {/* Location */}
      {asset.collateral_address && (
        <div className="px-4 pb-2">
          <div className="flex items-center gap-2 text-[var(--color-muted-foreground)] text-sm">
            <MapPin className="w-4 h-4" />
            <span className="truncate">{asset.collateral_address}</span>
          </div>
        </div>
      )}

      {/* Last Verified */}
      <div className="px-4 pb-2">
        <div className="flex items-center gap-2 text-[var(--color-muted-foreground)] text-xs">
          <Clock className="w-3 h-3" />
          <span>Last verified: {formatDate(asset.last_verified_at)}</span>
        </div>
      </div>

      {/* Error Message */}
      {asset.verification_error && (
        <div className="mx-4 mb-4 p-3 bg-red-500/10 rounded-lg border border-red-500/30">
          <p className="text-sm text-red-400">{asset.verification_error}</p>
        </div>
      )}

      {/* Action Button */}
      <div className="p-4 border-t border-[var(--surface-panel-border)]">
        <button
          onClick={runVerification}
          disabled={verifying}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {verifying ? (
            <>
              <RefreshCw className="w-5 h-5 animate-spin" />
              Verifying...
            </>
          ) : (
            <>
              <Shield className="w-5 h-5" />
              Securitize & Verify
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default AssetVerificationCard;
