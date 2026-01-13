/**
 * MapView Component for Ground Truth Protocol
 * 
 * Displays a Leaflet map with:
 * - Asset location marker with popup
 * - Satellite imagery layer toggle
 * - NDVI status visualization on marker
 */

import { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, ImageOverlay } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Leaf } from 'lucide-react';
import { useLayerStore } from '@/stores/layerStore';
import { LayerControls } from './LayerControls';
import type { LayerData, Bounds } from '@/types/layers';

// Fix for default marker icons in React-Leaflet
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom colored markers based on risk status
const createColoredIcon = (color: string) => {
    return L.divIcon({
        className: 'custom-marker',
        html: `
      <div style="
        background-color: ${color};
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="
          width: 8px;
          height: 8px;
          background-color: white;
          border-radius: 50%;
        "></div>
      </div>
    `,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -12],
    });
};

const statusColors: Record<string, string> = {
    COMPLIANT: '#10b981',  // Emerald
    WARNING: '#f59e0b',    // Amber
    BREACH: '#ef4444',     // Red
    PENDING: '#64748b',    // Slate
    ERROR: '#dc2626',      // Dark Red
};

interface LoanAsset {
    id: number;
    loan_id: string;
    collateral_address: string | null;
    geo_lat: number | null;
    geo_lon: number | null;
    risk_status: string;
    last_verified_score: number | null;
    spt_threshold: number | null;
    current_interest_rate: number | null;
}

interface MapViewProps {
    assets: LoanAsset[];
    selectedAssetId?: number;
    onAssetSelect?: (asset: LoanAsset) => void;
    height?: string;
    showSatellite?: boolean;
    assetId?: number;  // For layer support
    showLayerControls?: boolean;  // Show layer controls panel
}

// Component to recenter map when selected asset changes
function MapRecenter({ lat, lon }: { lat: number; lon: number }) {
    const map = useMap();
    useEffect(() => {
        map.flyTo([lat, lon], 14, { duration: 1.5 });
    }, [lat, lon, map]);
    return null;
}

// Component to handle base map layer switching
function BaseMapLayer({ baseMapType }: { baseMapType: 'satellite' | 'street' }) {
    return baseMapType === 'satellite' ? (
        <TileLayer
            key="satellite" // Key forces re-render when switching
            attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />
    ) : (
        <TileLayer
            key="street" // Key forces re-render when switching
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
    );
}

// Component to render layer overlays
function LayerOverlays({ assetId, overlays }: { assetId?: number; overlays: any[] }) {
    const getLayersForAsset = useLayerStore((state) => state.getLayersForAsset);
    const mapState = useLayerStore((state) => state.mapState);
    
    // Get current overlays from store (reactive)
    const currentOverlays = mapState.overlays;
    const layers = assetId ? getLayersForAsset(assetId) : [];
    
    // Use currentOverlays from store instead of prop
    const overlaysToRender = currentOverlays.length > 0 ? currentOverlays : overlays;
    
    if (overlaysToRender.length === 0) {
        return null;
    }
    
    return (
        <>
            {overlaysToRender.map(overlay => {
                const layer = layers.find(l => String(l.id) === overlay.layerId);
                if (!layer || !overlay.visible) {
                    return null;
                }
                
                // Get image URL from layer - use the API endpoint
                const imageUrl = layer.thumbnail_url || 
                    `/api/layers/${assetId}/${layer.id}?format=png`;
                
                // Create bounds from layer metadata
                const bounds: [[number, number], [number, number]] | null = layer.bounds && 
                    layer.bounds.north != null && layer.bounds.south != null && 
                    layer.bounds.east != null && layer.bounds.west != null &&
                    layer.bounds.north !== layer.bounds.south &&
                    layer.bounds.east !== layer.bounds.west
                    ? [
                        [layer.bounds.south, layer.bounds.west],
                        [layer.bounds.north, layer.bounds.east]
                      ]
                    : null;
                
                // Skip if bounds are invalid
                if (!bounds) {
                    console.warn(`Layer ${layer.id} has invalid bounds:`, layer.bounds);
                    return null;
                }
                
                // Apply opacity
                const opacity = overlay.opacity || 0.7;
                
                return (
                    <ImageOverlay
                        key={`overlay-${overlay.layerId}-${assetId}`}
                        url={imageUrl}
                        bounds={bounds}
                        opacity={opacity}
                        zIndex={overlay.zIndex || 100}
                    />
                );
            })}
        </>
    );
}

export function MapView({
    assets,
    selectedAssetId,
    onAssetSelect,
    height = '400px',
    showSatellite = false,
    assetId,
    showLayerControls = false,
}: MapViewProps) {
    const [mapReady, setMapReady] = useState(false);
    const mapState = useLayerStore((state) => state.mapState);
    const getLayersForAsset = useLayerStore((state) => state.getLayersForAsset);
    
    // Use assetId from props or selectedAssetId
    const activeAssetId = assetId || selectedAssetId;
    const overlays = mapState.overlays;
    
    // Determine base map from store or prop - this will re-render when mapState.baseMap changes
    const baseMapType = mapState.baseMap || (showSatellite ? 'satellite' : 'street');

    // Filter assets with valid coordinates
    const validAssets = assets.filter(a => a.geo_lat && a.geo_lon);

    // Calculate center from assets or use default (US center)
    const center: [number, number] = validAssets.length > 0
        ? [validAssets[0].geo_lat!, validAssets[0].geo_lon!]
        : [39.8283, -98.5795];  // US center

    // Find selected asset
    const selectedAsset = validAssets.find(a => a.id === selectedAssetId);

    if (validAssets.length === 0) {
        return (
            <div
                className="bg-slate-800/50 rounded-xl border border-slate-700/50 flex items-center justify-center"
                style={{ height }}
            >
                <div className="text-center text-slate-400">
                    <MapPin className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No assets with location data</p>
                </div>
            </div>
        );
    }

    return (
        <div
            className="rounded-xl overflow-hidden border border-slate-700/50 relative"
            style={{ height }}
        >
            <MapContainer
                key={`${center[0]}-${center[1]}`}
                center={center}
                zoom={validAssets.length === 1 ? 14 : 5}
                style={{ height: '100%', width: '100%' }}
                whenReady={() => setMapReady(true)}
            >
                {/* Base map layer - handled by BaseMapLayer component */}
                <BaseMapLayer baseMapType={baseMapType} />

                {/* Layer Overlays - Always render component, it handles empty state */}
                {activeAssetId && (
                    <LayerOverlays assetId={activeAssetId} overlays={overlays} />
                )}

                {/* Asset markers */}
                {validAssets.map(asset => {
                    const color = statusColors[asset.risk_status] || statusColors.PENDING;
                    const icon = createColoredIcon(color);

                    return (
                        <Marker
                            key={asset.id}
                            position={[asset.geo_lat!, asset.geo_lon!]}
                            icon={icon}
                            eventHandlers={{
                                click: () => onAssetSelect?.(asset),
                            }}
                        >
                            <Popup>
                                <div className="min-w-[200px]">
                                    <div className="font-bold text-lg mb-1">{asset.loan_id}</div>

                                    <div className="flex items-center gap-2 mb-2">
                                        <span
                                            className="px-2 py-0.5 rounded-full text-xs font-medium"
                                            style={{
                                                backgroundColor: `${color}20`,
                                                color: color,
                                            }}
                                        >
                                            {asset.risk_status}
                                        </span>
                                    </div>

                                    {asset.last_verified_score !== null && (
                                        <div className="flex items-center gap-1 text-sm text-gray-600 mb-1">
                                            <Leaf className="w-4 h-4" style={{ color }} />
                                            <span>NDVI: {(asset.last_verified_score * 100).toFixed(1)}%</span>
                                        </div>
                                    )}

                                    {asset.current_interest_rate && (
                                        <div className="text-sm text-gray-600 mb-2">
                                            Rate: {asset.current_interest_rate.toFixed(2)}%
                                        </div>
                                    )}

                                    {asset.collateral_address && (
                                        <div className="text-xs text-gray-500 border-t pt-2 mt-2">
                                            {asset.collateral_address}
                                        </div>
                                    )}
                                </div>
                            </Popup>
                        </Marker>
                    );
                })}

                {/* Recenter when selected asset changes */}
                {mapReady && selectedAsset && (
                    <MapRecenter
                        lat={selectedAsset.geo_lat!}
                        lon={selectedAsset.geo_lon!}
                    />
                )}
            </MapContainer>
            
            {/* Layer Controls Panel - Always show in compact mode so it can be reopened */}
            {showLayerControls && activeAssetId && (
                <LayerControls assetId={activeAssetId} compact={true} />
            )}
        </div>
    );
}

export default MapView;
