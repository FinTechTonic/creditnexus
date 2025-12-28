/**
 * MapView Component for Ground Truth Protocol
 * 
 * Displays a Leaflet map with:
 * - Asset location marker with popup
 * - Satellite imagery layer toggle
 * - NDVI status visualization on marker
 */

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Leaf } from 'lucide-react';

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
}

// Component to recenter map when selected asset changes
function MapRecenter({ lat, lon }: { lat: number; lon: number }) {
    const map = useMap();
    useEffect(() => {
        map.flyTo([lat, lon], 14, { duration: 1.5 });
    }, [lat, lon, map]);
    return null;
}

export function MapView({
    assets,
    selectedAssetId,
    onAssetSelect,
    height = '400px',
    showSatellite = false,
}: MapViewProps) {
    const [mapReady, setMapReady] = useState(false);

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
            className="rounded-xl overflow-hidden border border-slate-700/50"
            style={{ height }}
        >
            <MapContainer
                key={`${center[0]}-${center[1]}`}
                center={center}
                zoom={validAssets.length === 1 ? 14 : 5}
                style={{ height: '100%', width: '100%' }}
                whenReady={() => setMapReady(true)}
            >
                {/* Base map layer */}
                {showSatellite ? (
                    <TileLayer
                        attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
                        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    />
                ) : (
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
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
        </div>
    );
}

export default MapView;
