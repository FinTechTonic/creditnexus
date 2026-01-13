/**
 * Layer Browser Component.
 * 
 * Allows users to browse and view all available satellite layers for an asset.
 * Features:
 * - List of all available layers with metadata
 * - Preview thumbnails
 * - Layer selection
 * - Layer comparison mode
 * - Search/filter functionality
 */

import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Layers, Eye, EyeOff, Info, RefreshCw, Search, Image as ImageIcon } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import type { LayerListItem, LayerListResponse } from '@/types/layers';
import { useLayerStore } from '@/stores/layerStore';

interface LayerBrowserProps {
  assetId: number;
  onLayerSelect?: (layerId: string) => void;
  selectedLayerId?: string;
  className?: string;
}

export function LayerBrowser({
  assetId,
  onLayerSelect,
  selectedLayerId,
  className = ''
}: LayerBrowserProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedLayer, setExpandedLayer] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  
  // Get layers map from store - use selector to subscribe to changes
  const layersMap = useLayerStore((state) => state.layers);
  const selectLayer = useLayerStore((state) => state.selectLayer);
  const addOverlay = useLayerStore((state) => state.addOverlay);
  const setLayers = useLayerStore((state) => state.setLayers);
  
  // Memoize store layers to prevent infinite loops
  const storeLayers = useMemo(() => {
    const assetLayers = layersMap.get(assetId);
    return assetLayers ? [...assetLayers] : [];
  }, [layersMap, assetId]);
  
  // Convert store layers to LayerListItem format
  const layers: LayerListItem[] = useMemo(() => storeLayers.map(l => ({
    id: l.id,
    layer_type: l.type,
    metadata: l.metadata,
    bounds: l.bounds,
    thumbnail_url: l.thumbnail_url,
    created_at: l.created_at,
    band_number: l.metadata?.band_number || undefined
  })), [storeLayers]);

  useEffect(() => {
    if (assetId > 0) {
      fetchLayers();
    }
  }, [assetId]);

  const fetchLayers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetchWithAuth(`/api/layers/${assetId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch layers: ${response.statusText}`);
      }
      
      const data: LayerListResponse = await response.json();
      
      // Update store - this will trigger re-render via selector
      setLayers(assetId, data.layers.map(l => ({
        id: l.id,
        type: l.layer_type,
        metadata: l.metadata,
        bounds: l.bounds,
        thumbnail_url: l.thumbnail_url || undefined,
        created_at: l.created_at
      })));
      
    } catch (err) {
      console.error('Failed to fetch layers:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch layers');
    } finally {
      setLoading(false);
    }
  };

  const mapState = useLayerStore((state) => state.mapState);
  
  const handleLayerSelect = (layerId: string) => {
    selectLayer(layerId);
    
    // Also add as overlay when selected (like LayerControls does)
    const layer = storeLayers.find(l => String(l.id) === layerId);
    if (layer) {
      const existingOverlay = mapState.overlays.find(o => o.layerId === layerId);
      if (!existingOverlay) {
        addOverlay({
          layerId,
          opacity: 0.7,
          visible: true,
          blendingMode: 'normal',
          zIndex: mapState.overlays.length
        });
      }
    }
    
    onLayerSelect?.(layerId);
  };

  const handleExpand = (layerId: string) => {
    setExpandedLayer(expandedLayer === layerId ? null : layerId);
  };

  // Filter layers
  const filteredLayers = layers.filter(layer => {
    const matchesSearch = searchQuery === '' || 
      layer.metadata.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      layer.layer_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      layer.band_number?.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesFilter = filterType === 'all' || layer.layer_type === filterType;
    
    return matchesSearch && matchesFilter;
  });

  // Get unique layer types for filter
  const layerTypes = Array.from(new Set(layers.map(l => l.layer_type)));

  if (loading && layers.length === 0) {
    return (
      <Card className={`bg-zinc-900/50 border-zinc-700 ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-zinc-400 animate-spin" />
            <span className="ml-2 text-zinc-400">Loading layers...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`bg-zinc-900/50 border-zinc-700 ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between mb-4">
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <Layers className="w-5 h-5" />
            Available Layers
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchLayers}
            disabled={loading}
            className="text-zinc-400 hover:text-white"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <Input
              type="text"
              placeholder="Search layers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 bg-zinc-800 border-zinc-700 text-white"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-sm text-white"
          >
            <option value="all">All Types</option>
            {layerTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="p-3 bg-red-900/20 border border-red-700/50 rounded-lg mb-4">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {filteredLayers.length === 0 ? (
          <div className="text-center py-8 text-zinc-500">
            <ImageIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No layers found</p>
            {searchQuery && <p className="text-xs mt-1">Try a different search term</p>}
          </div>
        ) : (
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {filteredLayers.map(layer => (
              <LayerItem
                key={layer.id}
                layer={layer}
                isSelected={String(layer.id) === selectedLayerId}
                isExpanded={expandedLayer === String(layer.id)}
                onSelect={() => handleLayerSelect(String(layer.id))}
                onExpand={() => handleExpand(String(layer.id))}
              />
            ))}
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-zinc-700 text-xs text-zinc-500">
          {filteredLayers.length} of {layers.length} layer(s)
        </div>
      </CardContent>
    </Card>
  );
}

interface LayerItemProps {
  layer: LayerListItem;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onExpand: () => void;
}

function LayerItem({
  layer,
  isSelected,
  isExpanded,
  onSelect,
  onExpand
}: LayerItemProps) {
  const metadata = layer.metadata || {};
  
  return (
    <div
      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
        isSelected
          ? 'border-indigo-500 bg-indigo-500/10'
          : 'border-zinc-700 bg-zinc-800/50 hover:border-zinc-600'
      }`}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Thumbnail */}
          <div className="w-12 h-12 bg-zinc-900 rounded flex items-center justify-center flex-shrink-0 border border-zinc-700">
            {layer.thumbnail_url ? (
              <img
                src={layer.thumbnail_url}
                alt={metadata.name || layer.layer_type}
                className="w-full h-full object-cover rounded"
                onError={(e) => {
                  // Fallback to icon if image fails to load
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  if (target.parentElement) {
                    target.parentElement.innerHTML = '<div class="w-full h-full flex items-center justify-center"><ImageIcon class="w-6 h-6 text-zinc-500" /></div>';
                  }
                }}
              />
            ) : (
              <ImageIcon className="w-6 h-6 text-zinc-500" />
            )}
          </div>

          {/* Layer Info */}
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm text-white truncate">
              {metadata.name || layer.layer_type}
            </div>
            <div className="text-xs text-zinc-400 flex items-center gap-2">
              {metadata.resolution && (
                <span>{metadata.resolution}m</span>
              )}
              {layer.band_number && (
                <span>• {layer.band_number}</span>
              )}
              {metadata.wavelength && (
                <span>• {metadata.wavelength}nm</span>
              )}
            </div>
          </div>
        </div>

        {/* Expand Button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onExpand();
          }}
          className="ml-2 text-zinc-400 hover:text-white"
        >
          {isExpanded ? (
            <EyeOff className="w-4 h-4" />
          ) : (
            <Eye className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Expanded Metadata */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-zinc-700 space-y-2">
          {metadata.description && (
            <div className="text-xs text-zinc-400">
              <Info className="w-3 h-3 inline mr-1" />
              {metadata.description}
            </div>
          )}
          
          {metadata.min_value !== undefined && metadata.max_value !== undefined && (
            <div className="text-xs text-zinc-500">
              Range: {metadata.min_value.toFixed(3)} to {metadata.max_value.toFixed(3)}
              {metadata.mean_value !== undefined && (
                <span className="ml-2">(mean: {metadata.mean_value.toFixed(3)})</span>
              )}
            </div>
          )}
          
          {metadata.classification && (
            <div className="text-xs text-zinc-500">
              Classification: {metadata.classification}
              {metadata.confidence !== undefined && (
                <span className="ml-2">({(metadata.confidence * 100).toFixed(1)}% confidence)</span>
              )}
            </div>
          )}
          
          <div className="text-xs text-zinc-600">
            Created: {new Date(layer.created_at).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}
