/**
 * Real-Time MapView Component with WebSocket Integration.
 * 
 * Wraps MapView with WebSocket connection for real-time layer updates
 * during verification. Displays layers as they are processed.
 */

import { useEffect, useState } from 'react';
import { MapView } from './MapView';
import { useVerificationWebSocket } from '@/hooks/useVerificationWebSocket';
import { useLayerStore } from '@/stores/layerStore';
import { VerificationProgress } from './VerificationProgress';
import type { LayerUpdate, VerificationProgress as VerificationProgressType, VerificationComplete } from '@/types/layers';

interface RealTimeMapViewProps {
  assetId: number;
  assets: any[];
  selectedAssetId?: number;
  onAssetSelect?: (asset: any) => void;
  height?: string;
  showSatellite?: boolean;
  showLayerControls?: boolean;
  onVerificationComplete?: (complete: VerificationComplete) => void;
}

export function RealTimeMapView({
  assetId,
  assets,
  selectedAssetId,
  onAssetSelect,
  height = '400px',
  showSatellite = false,
  showLayerControls = true,
  onVerificationComplete
}: RealTimeMapViewProps) {
  const [progress, setProgress] = useState<VerificationProgressType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  
  const { 
    addLayer, 
    setLayers, 
    selectAsset,
    getLayersForAsset 
  } = useLayerStore();

  // WebSocket connection for real-time updates
  // Connect when assetId is available (not just when verifying) so it's ready when user clicks start
  const {
    connected,
    connectionError,
    sendMessage
  } = useVerificationWebSocket({
    assetId,
    enabled: assetId > 0, // Always connect when assetId is available
    onLayerUpdate: (update: LayerUpdate) => {
      console.log('Layer update received:', update);
      
      if (update.status === 'complete' && update.metadata) {
        // Convert update to LayerData format
        const layerData = {
          id: parseInt(update.layer_id),
          type: update.layer_type,
          metadata: update.metadata,
          bounds: update.metadata.bounds || {
            north: 0,
            south: 0,
            east: 0,
            west: 0
          },
          thumbnail_url: update.thumbnail_url,
          created_at: new Date().toISOString()
        };
        
        // Add layer to store
        addLayer(assetId, layerData);
        
        // Automatically add as overlay when layer is complete
        const store = useLayerStore.getState();
        const existingOverlay = store.mapState.overlays.find(o => o.layerId === update.layer_id);
        if (!existingOverlay) {
          store.addOverlay({
            layerId: update.layer_id,
            opacity: 0.7,
            visible: true,
            blendingMode: 'normal',
            zIndex: store.mapState.overlays.length
          });
        }
      }
    },
    onProgress: (progressUpdate: VerificationProgressType) => {
      setProgress(progressUpdate);
      
      // Update verification state
      if (progressUpdate.stage === 'complete') {
        setIsVerifying(false);
      } else {
        setIsVerifying(true);
      }
    },
    onComplete: (complete: VerificationComplete) => {
      setIsVerifying(false);
      setProgress(null);
      onVerificationComplete?.(complete);
      
      // Refresh layers from API
      fetchLayers();
    },
    onError: (err: Error) => {
      setError(err.message);
      setIsVerifying(false);
    }
  });

  // Fetch layers from API
  const fetchLayers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/layers/${assetId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        const layers = (data.layers || []).map((l: any) => ({
          id: l.id,
          type: l.layer_type,
          metadata: l.metadata,
          bounds: l.bounds,
          thumbnail_url: l.thumbnail_url,
          created_at: l.created_at
        }));
        
        setLayers(assetId, layers);
      }
    } catch (err) {
      console.error('Failed to fetch layers:', err);
    }
  };

  // Initial layer fetch
  useEffect(() => {
    if (assetId > 0) {
      fetchLayers();
      selectAsset(assetId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetId]);

  // Start verification via WebSocket
  const startVerification = () => {
    if (!connected) {
      setError('WebSocket not connected. Please wait a moment and try again.');
      return;
    }
    
    setIsVerifying(true);
    setError(null);
    setProgress(null);
    
    // Send start verification message
    sendMessage({ type: 'start_verification' });
  };

  const handleCancel = () => {
    setIsVerifying(false);
    setProgress(null);
    // WebSocket will handle disconnection if needed
  };

  return (
    <div className="relative w-full h-full">
      {/* Map View */}
      <MapView
        assets={assets}
        selectedAssetId={selectedAssetId}
        onAssetSelect={onAssetSelect}
        height={height}
        showSatellite={showSatellite}
        assetId={assetId}
        showLayerControls={showLayerControls}
      />

      {/* Verification Progress Overlay */}
      {isVerifying && (
        <div className="absolute top-4 left-4 z-[1001] max-w-md">
          <VerificationProgress
            progress={progress || undefined}
            onCancel={handleCancel}
            error={error}
          />
        </div>
      )}

      {/* Connection Status Indicator */}
      {connected && (
        <div className="absolute bottom-4 left-4 z-[1001] bg-green-500/20 border border-green-500/50 rounded px-3 py-1.5 text-xs text-green-400">
          <span className="w-2 h-2 bg-green-500 rounded-full inline-block mr-2 animate-pulse"></span>
          Connected
        </div>
      )}

      {connectionError && (
        <div className="absolute bottom-4 left-4 z-[1001] bg-red-500/20 border border-red-500/50 rounded px-3 py-1.5 text-xs text-red-400">
          Connection Error: {connectionError.message}
        </div>
      )}

      {/* Start Verification Button (if not verifying) */}
      {!isVerifying && assetId > 0 && (
        <div className="absolute bottom-4 right-4 z-[1001]">
          <button
            onClick={startVerification}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Start Verification
          </button>
        </div>
      )}
    </div>
  );
}
