/**
 * Layer state management store using Zustand.
 * 
 * Manages:
 * - Layer cache
 * - Selected layer state
 * - Animation state
 * - Map overlay configuration
 */

import { create } from 'zustand';
import type {
  LayerData,
  LayerAnimationState,
  LayerOverlayConfig,
  MapLayerState,
  LayerUpdate,
  VerificationProgress,
  VerificationComplete
} from '@/types/layers';

interface LayerStore {
  // Layer cache
  layers: Map<number, LayerData[]>;  // asset_id -> layers
  layerCache: Map<number, LayerData>;  // layer_id -> layer data
  
  // Selected layer state
  selectedAssetId: number | null;
  selectedLayerId: string | null;
  
  // Animation state
  animation: LayerAnimationState;
  
  // Map layer state
  mapState: MapLayerState;
  
  // WebSocket connection state
  isConnected: boolean;
  connectionError: string | null;
  
  // Actions: Layer management
  setLayers: (assetId: number, layers: LayerData[]) => void;
  addLayer: (assetId: number, layer: LayerData) => void;
  updateLayer: (layerId: number, updates: Partial<LayerData>) => void;
  removeLayer: (assetId: number, layerId: number) => void;
  clearLayers: (assetId: number) => void;
  
  // Actions: Selection
  selectAsset: (assetId: number | null) => void;
  selectLayer: (layerId: string | null) => void;
  
  // Actions: Animation
  setAnimationState: (state: Partial<LayerAnimationState>) => void;
  playAnimation: () => void;
  pauseAnimation: () => void;
  nextLayer: () => void;
  previousLayer: () => void;
  setAnimationSpeed: (speed: 'slow' | 'normal' | 'fast') => void;
  toggleLoop: () => void;
  
  // Actions: Map state
  setMapState: (state: Partial<MapLayerState>) => void;
  addOverlay: (overlay: LayerOverlayConfig) => void;
  removeOverlay: (layerId: string) => void;
  updateOverlay: (layerId: string, updates: Partial<LayerOverlayConfig>) => void;
  setBaseMap: (baseMap: 'satellite' | 'street') => void;
  
  // Actions: WebSocket
  handleLayerUpdate: (update: LayerUpdate) => void;
  handleProgress: (progress: VerificationProgress) => void;
  handleVerificationComplete: (complete: VerificationComplete) => void;
  setConnectionState: (connected: boolean, error: string | null) => void;
  
  // Actions: Cache
  getLayer: (layerId: number) => LayerData | undefined;
  getLayersForAsset: (assetId: number) => LayerData[];
  cacheLayer: (layer: LayerData) => void;
  clearCache: () => void;
}

export const useLayerStore = create<LayerStore>((set, get) => ({
  // Initial state
  layers: new Map(),
  layerCache: new Map(),
  selectedAssetId: null,
  selectedLayerId: null,
  animation: {
    isPlaying: false,
    currentIndex: 0,
    speed: 'normal',
    loop: false,
    layers: []
  },
  mapState: {
    selectedLayer: undefined,
    overlays: [],
    baseMap: 'satellite'
  },
  isConnected: false,
  connectionError: null,
  
  // Layer management
  setLayers: (assetId, layers) => {
    set((state) => {
      const newLayers = new Map(state.layers);
      newLayers.set(assetId, layers);
      
      // Update cache
      const newCache = new Map(state.layerCache);
      layers.forEach(layer => {
        newCache.set(layer.id, layer);
      });
      
      return {
        layers: newLayers,
        layerCache: newCache
      };
    });
  },
  
  addLayer: (assetId, layer) => {
    set((state) => {
      const assetLayers = state.layers.get(assetId) || [];
      const newLayers = new Map(state.layers);
      newLayers.set(assetId, [...assetLayers, layer]);
      
      const newCache = new Map(state.layerCache);
      newCache.set(layer.id, layer);
      
      return {
        layers: newLayers,
        layerCache: newCache
      };
    });
  },
  
  updateLayer: (layerId, updates) => {
    set((state) => {
      const layer = state.layerCache.get(layerId);
      if (!layer) return state;
      
      const updatedLayer = { ...layer, ...updates };
      const newCache = new Map(state.layerCache);
      newCache.set(layerId, updatedLayer);
      
      // Update in layers map
      const newLayers = new Map(state.layers);
      for (const [assetId, layers] of newLayers.entries()) {
        const index = layers.findIndex(l => l.id === layerId);
        if (index !== -1) {
          newLayers.set(assetId, [
            ...layers.slice(0, index),
            updatedLayer,
            ...layers.slice(index + 1)
          ]);
        }
      }
      
      return {
        layers: newLayers,
        layerCache: newCache
      };
    });
  },
  
  removeLayer: (assetId, layerId) => {
    set((state) => {
      const assetLayers = state.layers.get(assetId) || [];
      const newLayers = new Map(state.layers);
      newLayers.set(assetId, assetLayers.filter(l => l.id !== layerId));
      
      const newCache = new Map(state.layerCache);
      newCache.delete(layerId);
      
      return {
        layers: newLayers,
        layerCache: newCache
      };
    });
  },
  
  clearLayers: (assetId) => {
    set((state) => {
      const newLayers = new Map(state.layers);
      newLayers.delete(assetId);
      
      return { layers: newLayers };
    });
  },
  
  // Selection
  selectAsset: (assetId) => {
    set({ selectedAssetId: assetId });
    
    // Auto-select first layer if available
    const state = get();
    const layers = state.layers.get(assetId || 0) || [];
    if (layers.length > 0) {
      set({ selectedLayerId: String(layers[0].id) });
    }
  },
  
  selectLayer: (layerId) => {
    set({ selectedLayerId: layerId });
  },
  
  // Animation
  setAnimationState: (updates) => {
    set((state) => ({
      animation: { ...state.animation, ...updates }
    }));
  },
  
  playAnimation: () => {
    set((state) => ({
      animation: { ...state.animation, isPlaying: true }
    }));
  },
  
  pauseAnimation: () => {
    set((state) => ({
      animation: { ...state.animation, isPlaying: false }
    }));
  },
  
  nextLayer: () => {
    set((state) => {
      const { animation } = state;
      const nextIndex = animation.loop
        ? (animation.currentIndex + 1) % animation.layers.length
        : Math.min(animation.currentIndex + 1, animation.layers.length - 1);
      
      return {
        animation: { ...animation, currentIndex: nextIndex },
        selectedLayerId: String(animation.layers[nextIndex]?.id || '')
      };
    });
  },
  
  previousLayer: () => {
    set((state) => {
      const { animation } = state;
      const prevIndex = animation.loop
        ? (animation.currentIndex - 1 + animation.layers.length) % animation.layers.length
        : Math.max(animation.currentIndex - 1, 0);
      
      return {
        animation: { ...animation, currentIndex: prevIndex },
        selectedLayerId: String(animation.layers[prevIndex]?.id || '')
      };
    });
  },
  
  setAnimationSpeed: (speed) => {
    set((state) => ({
      animation: { ...state.animation, speed }
    }));
  },
  
  toggleLoop: () => {
    set((state) => ({
      animation: { ...state.animation, loop: !state.animation.loop }
    }));
  },
  
  // Map state
  setMapState: (updates) => {
    set((state) => ({
      mapState: { ...state.mapState, ...updates }
    }));
  },
  
  addOverlay: (overlay) => {
    set((state) => ({
      mapState: {
        ...state.mapState,
        overlays: [...state.mapState.overlays, overlay]
      }
    }));
  },
  
  removeOverlay: (layerId) => {
    set((state) => ({
      mapState: {
        ...state.mapState,
        overlays: state.mapState.overlays.filter(o => o.layerId !== layerId)
      }
    }));
  },
  
  updateOverlay: (layerId, updates) => {
    set((state) => ({
      mapState: {
        ...state.mapState,
        overlays: state.mapState.overlays.map(o =>
          o.layerId === layerId ? { ...o, ...updates } : o
        )
      }
    }));
  },
  
  setBaseMap: (baseMap) => {
    set((state) => ({
      mapState: { ...state.mapState, baseMap }
    }));
  },
  
  // WebSocket handlers
  handleLayerUpdate: (update) => {
    if (update.status === 'complete' && update.metadata) {
      // Convert update to LayerData and add to store
      const layer: LayerData = {
        id: parseInt(update.layer_id),
        type: update.layer_type,
        metadata: update.metadata,
        bounds: update.metadata.bounds || {
          north: 0, south: 0, east: 0, west: 0
        },
        thumbnail_url: update.thumbnail_url
      };
      
      // Find asset ID from current selection or use default
      const state = get();
      const assetId = state.selectedAssetId || 0;
      get().addLayer(assetId, layer);
    }
  },
  
  handleProgress: (progress) => {
    // Progress updates can be used for UI feedback
    // Store can emit events or components can subscribe
    console.log('Verification progress:', progress);
  },
  
  handleVerificationComplete: (complete) => {
    set({ isConnected: false });
    console.log('Verification complete:', complete);
  },
  
  setConnectionState: (connected, error) => {
    set({ isConnected: connected, connectionError: error });
  },
  
  // Cache helpers
  getLayer: (layerId) => {
    return get().layerCache.get(layerId);
  },
  
  getLayersForAsset: (assetId) => {
    return get().layers.get(assetId) || [];
  },
  
  cacheLayer: (layer) => {
    set((state) => {
      const newCache = new Map(state.layerCache);
      newCache.set(layer.id, layer);
      return { layerCache: newCache };
    });
  },
  
  clearCache: () => {
    set({
      layers: new Map(),
      layerCache: new Map()
    });
  }
}));
