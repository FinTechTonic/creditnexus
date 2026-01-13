/**
 * Layer Controls Component.
 * 
 * Control panel for layer overlays on the map.
 * Features:
 * - Layer selector dropdown
 * - Opacity sliders for each overlay
 * - Visibility toggles
 * - Layer info tooltips
 * - Layer blending mode selector
 * - Reset controls
 */

import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Layers, Eye, EyeOff, Info, RotateCcw, Settings, X, ChevronDown, ChevronUp } from 'lucide-react';
import { useLayerStore } from '@/stores/layerStore';
import type { LayerOverlayConfig } from '@/types/layers';

interface LayerControlsProps {
  assetId: number;
  className?: string;
  compact?: boolean;
}

export function LayerControls({
  assetId,
  className = '',
  compact = false
}: LayerControlsProps) {
  const mapState = useLayerStore((state) => state.mapState);
  // Get layers from store - use selector to subscribe to changes
  const layersMap = useLayerStore((state) => state.layers);
  // Memoize layers array to prevent infinite loops
  const layers = useMemo(() => {
    const assetLayers = layersMap.get(assetId);
    return assetLayers ? [...assetLayers] : [];
  }, [layersMap, assetId]);
  const overlays = mapState.overlays;
  const addOverlay = useLayerStore((state) => state.addOverlay);
  const removeOverlay = useLayerStore((state) => state.removeOverlay);
  const updateOverlay = useLayerStore((state) => state.updateOverlay);
  const setMapState = useLayerStore((state) => state.setMapState);
  const setLayers = useLayerStore((state) => state.setLayers);
  const [isVisible, setIsVisible] = useState(true);
  const [expanded, setExpanded] = useState(!compact);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    addLayer: true,
    activeOverlays: true,
    baseMap: false
  });
  
  // Fetch layers when assetId changes
  useEffect(() => {
    if (assetId > 0) {
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
            setLayers(assetId, (data.layers || []).map((l: any) => ({
              id: l.id,
              type: l.layer_type,
              metadata: l.metadata,
              bounds: l.bounds,
              thumbnail_url: l.thumbnail_url || undefined,
              created_at: l.created_at
            })));
          }
        } catch (err) {
          console.error('Failed to fetch layers:', err);
        }
      };
      
      fetchLayers();
    }
  }, [assetId]);
  
  // Hide panel when close button is clicked
  const handleClose = () => {
    setIsVisible(false);
    if (compact) {
      setExpanded(false);
    }
  };
  
  // Don't render if not visible (unless compact mode)
  if (!isVisible && !compact) {
    return null;
  }
  
  // Show button to reopen if closed in compact mode
  if (!isVisible && compact) {
    return (
      <div className={`absolute top-4 right-4 z-[1000] ${className}`}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setExpanded(true);
            setIsVisible(true);
          }}
          className="bg-black/90 backdrop-blur border-zinc-700 text-white hover:bg-black hover:border-zinc-600 shadow-lg"
          title="Show Layer Controls"
        >
          <Layers className="w-4 h-4 mr-2" />
          Layers {overlays.length > 0 && `(${overlays.length})`}
        </Button>
      </div>
    );
  }
  
  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const handleLayerSelect = (layerId: string) => {
    const layer = layers.find(l => String(l.id) === layerId);
    if (!layer) return;

    // Check if overlay already exists
    const existingOverlay = overlays.find(o => o.layerId === layerId);
    if (existingOverlay) {
      // Toggle visibility
      updateOverlay(layerId, { visible: !existingOverlay.visible });
    } else {
      // Add new overlay
      addOverlay({
        layerId,
        opacity: 0.7,
        visible: true,
        blendingMode: 'normal',
        zIndex: overlays.length
      });
    }
  };

  const handleOpacityChange = (layerId: string, opacity: number[]) => {
    updateOverlay(layerId, { opacity: opacity[0] });
  };

  const handleVisibilityToggle = (layerId: string) => {
    const overlay = overlays.find(o => o.layerId === layerId);
    if (overlay) {
      updateOverlay(layerId, { visible: !overlay.visible });
    }
  };

  const handleBlendingModeChange = (layerId: string, mode: LayerOverlayConfig['blendingMode']) => {
    updateOverlay(layerId, { blendingMode: mode });
  };

  const handleRemoveOverlay = (layerId: string) => {
    removeOverlay(layerId);
  };

  const handleReset = () => {
    overlays.forEach(overlay => {
      removeOverlay(overlay.layerId);
    });
    setMapState({ selectedLayer: undefined });
  };

  if (compact && !expanded) {
    return (
      <div className={`absolute top-4 right-4 z-[1000] ${className}`}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setExpanded(true);
            setIsVisible(true);
          }}
          className="bg-black/90 backdrop-blur border-zinc-700 text-white hover:bg-black hover:border-zinc-600 shadow-lg"
          title="Show Layer Controls"
        >
          <Layers className="w-4 h-4 mr-2" />
          Layers {overlays.length > 0 && `(${overlays.length})`}
        </Button>
      </div>
    );
  }

  return (
    <Card className={`absolute top-4 right-4 z-[1000] bg-black/90 backdrop-blur border-zinc-700 shadow-xl ${className}`} style={{ maxWidth: '320px', maxHeight: '85vh' }}>
      <CardHeader className="pb-2 border-b border-zinc-700">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
            <Layers className="w-4 h-4" />
            Layer Overlays
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClose}
            className="h-6 w-6 p-0 text-zinc-400 hover:text-white hover:bg-zinc-700"
            title="Close"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 overflow-y-auto" style={{ maxHeight: 'calc(85vh - 60px)' }}>
        {/* Layer Selector - Collapsible */}
        <div className="border-b border-zinc-700 pb-2">
          <button
            onClick={() => toggleSection('addLayer')}
            className="w-full flex items-center justify-between text-xs text-zinc-300 hover:text-white transition-colors"
          >
            <span className="font-medium">Add Layer</span>
            {expandedSections.addLayer ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {expandedSections.addLayer && (
            <div className="mt-2">
              <select
                value={mapState.selectedLayer || ''}
                onChange={(e) => {
                  const layerId = e.target.value;
                  if (layerId) {
                    setMapState({ selectedLayer: layerId });
                    handleLayerSelect(layerId);
                  }
                }}
                className="w-full bg-zinc-900 text-white text-xs p-2 rounded border border-zinc-700 focus:border-indigo-500 focus:outline-none"
              >
                <option value="">Select a layer...</option>
                {layers.length === 0 ? (
                  <option value="" disabled>No layers available</option>
                ) : (
                  layers.map(layer => (
                    <option key={layer.id} value={String(layer.id)}>
                      {layer.metadata.name || layer.type} {layer.band_number ? `(${layer.band_number})` : ''}
                    </option>
                  ))
                )}
              </select>
            </div>
          )}
        </div>

        {/* Active Overlays - Collapsible */}
        {overlays.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-zinc-700">
            <button
              onClick={() => toggleSection('activeOverlays')}
              className="w-full flex items-center justify-between text-xs text-zinc-300 hover:text-white transition-colors"
            >
              <span className="font-medium">Active Overlays ({overlays.length})</span>
              {expandedSections.activeOverlays ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
            {expandedSections.activeOverlays && (
              <div className="space-y-2 mt-2">
            {overlays.map(overlay => {
              const layer = layers.find(l => String(l.id) === overlay.layerId);
              if (!layer) return null;

              return (
                <div
                  key={overlay.layerId}
                  className="p-2 bg-zinc-900/50 rounded border border-zinc-700 space-y-2"
                >
                  {/* Layer Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleVisibilityToggle(overlay.layerId)}
                        className="h-6 w-6 p-0 text-zinc-400 hover:text-white"
                      >
                        {overlay.visible ? (
                          <Eye className="w-4 h-4" />
                        ) : (
                          <EyeOff className="w-4 h-4" />
                        )}
                      </Button>
                      <span className="text-xs text-white truncate">
                        {layer.metadata.name || layer.type}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveOverlay(overlay.layerId)}
                      className="h-6 w-6 p-0 text-zinc-400 hover:text-red-400"
                    >
                      ×
                    </Button>
                  </div>

                  {/* Opacity Slider */}
                  {overlay.visible && (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-zinc-400">Opacity</span>
                        <span className="text-white font-mono">
                          {Math.round(overlay.opacity * 100)}%
                        </span>
                      </div>
                      <Slider
                        value={[overlay.opacity]}
                        onValueChange={(value) => handleOpacityChange(overlay.layerId, value)}
                        min={0}
                        max={1}
                        step={0.01}
                        className="w-full"
                      />
                    </div>
                  )}

                  {/* Blending Mode */}
                  {overlay.visible && (
                    <div>
                      <label className="text-xs text-zinc-400 mb-1 block">Blending</label>
                      <select
                        value={overlay.blendingMode}
                        onChange={(e) => handleBlendingModeChange(
                          overlay.layerId,
                          e.target.value as LayerOverlayConfig['blendingMode']
                        )}
                        className="w-full bg-zinc-800 text-white text-xs p-1.5 rounded border border-zinc-700 focus:border-indigo-500 focus:outline-none"
                      >
                        <option value="normal">Normal</option>
                        <option value="multiply">Multiply</option>
                        <option value="screen">Screen</option>
                        <option value="overlay">Overlay</option>
                      </select>
                    </div>
                  )}

                  {/* Layer Info */}
                  <details className="text-xs">
                    <summary className="text-zinc-500 cursor-pointer hover:text-zinc-400 flex items-center gap-1">
                      <Info className="w-3 h-3" />
                      Info
                    </summary>
                    <div className="mt-2 p-2 bg-zinc-800 rounded space-y-1 text-zinc-400">
                      {layer.metadata.description && (
                        <div>{layer.metadata.description}</div>
                      )}
                      {layer.metadata.resolution && (
                        <div>Resolution: {layer.metadata.resolution}m</div>
                      )}
                      {layer.metadata.min_value !== undefined && layer.metadata.max_value !== undefined && (
                        <div>
                          Range: {layer.metadata.min_value.toFixed(3)} - {layer.metadata.max_value.toFixed(3)}
                        </div>
                      )}
                    </div>
                  </details>
                </div>
              );
            })}
              </div>
            )}
          </div>
        )}

        {/* Reset Button */}
        {overlays.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            className="w-full text-xs border-zinc-700 text-zinc-400 hover:text-white"
          >
            <RotateCcw className="w-3 h-3 mr-2" />
            Clear All
          </Button>
        )}

        {/* Base Map Toggle - Collapsible */}
        <div className="pt-2 border-t border-zinc-700">
          <button
            onClick={() => toggleSection('baseMap')}
            className="w-full flex items-center justify-between text-xs text-zinc-300 hover:text-white transition-colors"
          >
            <span className="font-medium">Base Map</span>
            {expandedSections.baseMap ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {expandedSections.baseMap && (
            <div className="flex gap-2 mt-2">
              <Button
                variant={mapState.baseMap === 'satellite' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setMapState({ baseMap: 'satellite' })}
                className="flex-1 text-xs"
              >
                Satellite
              </Button>
              <Button
                variant={mapState.baseMap === 'street' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setMapState({ baseMap: 'street' })}
                className="flex-1 text-xs"
              >
                Street
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
