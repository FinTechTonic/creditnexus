/**
 * TypeScript types for satellite layer visualization.
 * 
 * Defines all types used for layer data, metadata, and visualization.
 */

/**
 * Layer type enumeration.
 */
export enum LayerType {
  SENTINEL_BAND = 'sentinel_band',
  NDVI = 'ndvi',
  FALSE_COLOR = 'false_color',
  CLASSIFICATION = 'classification',
  RISK_STATUS = 'risk_status',
  AIR_QUALITY = 'air_quality',
  OSM_OVERLAY = 'osm_overlay'
}

/**
 * Sentinel-2 band identifiers.
 */
export type SentinelBand = 
  | 'B01' | 'B02' | 'B03' | 'B04' | 'B05' | 'B06' | 'B07' 
  | 'B08' | 'B8A' | 'B09' | 'B10' | 'B11' | 'B12';

/**
 * Geographic bounds.
 */
export interface Bounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

/**
 * Layer metadata.
 */
export interface LayerMetadata {
  name?: string;
  description?: string;
  resolution?: number;  // meters
  band_name?: string;
  wavelength?: number;  // nanometers
  min_value?: number;
  max_value?: number;
  mean_value?: number;
  std_value?: number;
  formula?: string;
  composition?: string;
  classification?: string;
  confidence?: number;
  model?: string;
  created_at?: string;
  bounds?: Bounds;
  crs?: string;
  [key: string]: any;  // Allow additional metadata
}

/**
 * Layer data structure.
 */
export interface LayerData {
  id: number;
  type: LayerType | string;
  band_number?: SentinelBand | string;
  data?: number[][] | number[][][] | string;  // Array data or image URL
  metadata: LayerMetadata;
  bounds: Bounds;
  thumbnail_url?: string;
  file_path?: string;
  created_at?: string;
}

/**
 * Layer update message (for WebSocket).
 */
export interface LayerUpdate {
  type: 'layer_update';
  layer_id: string;
  layer_type: LayerType | string;
  status: 'processing' | 'complete' | 'error';
  progress?: number;  // 0.0 to 1.0
  metadata?: LayerMetadata;
  thumbnail_url?: string;
  error?: string;
}

/**
 * Verification progress message (for WebSocket).
 */
export interface VerificationProgress {
  type: 'progress';
  stage: 
    | 'geocoding'
    | 'fetching_bands'
    | 'calculating_ndvi'
    | 'classifying'
    | 'generating_layers'
    | 'complete';
  current?: number;
  total?: number;
  band?: string;
  percentage?: number;
  estimated_seconds_remaining?: number;
  message?: string;
}

/**
 * Verification complete message (for WebSocket).
 */
export interface VerificationComplete {
  type: 'verification_complete';
  asset_id: number;
  layers_generated: string[];
  ndvi_score?: number;
  risk_status?: string;
}

/**
 * WebSocket error message.
 */
export interface WebSocketError {
  type: 'error';
  message: string;
  stage?: string;
  retryable?: boolean;
}

/**
 * Union type for all WebSocket messages.
 */
export type WebSocketMessage = 
  | LayerUpdate 
  | VerificationProgress 
  | VerificationComplete 
  | WebSocketError;

/**
 * Layer list item (from API).
 */
export interface LayerListItem {
  id: number;
  layer_type: string;
  band_number?: string | null;
  metadata: Record<string, any>;
  thumbnail_url?: string | null;
  bounds: Bounds;
  created_at: string;
}

/**
 * Layer list response (from API).
 */
export interface LayerListResponse {
  layers: LayerListItem[];
  total: number;
}

/**
 * Generate layers request.
 */
export interface GenerateLayersRequest {
  layer_types: string[];
  force_regenerate?: boolean;
}

/**
 * Generate layers response.
 */
export interface GenerateLayersResponse {
  generated: number[];
  existing: number[];
  failed: string[];
}

/**
 * Layer animation state.
 */
export interface LayerAnimationState {
  isPlaying: boolean;
  currentIndex: number;
  speed: 'slow' | 'normal' | 'fast';
  loop: boolean;
  layers: LayerData[];
}

/**
 * Layer overlay configuration.
 */
export interface LayerOverlayConfig {
  layerId: string;
  opacity: number;  // 0.0 to 1.0
  visible: boolean;
  blendingMode: 'normal' | 'multiply' | 'screen' | 'overlay';
  zIndex?: number;
}

/**
 * Map layer state.
 */
export interface MapLayerState {
  selectedLayer?: string;
  overlays: LayerOverlayConfig[];
  baseMap: 'satellite' | 'street';
}

/**
 * Color scheme for NDVI visualization.
 */
export interface NDVIColorScheme {
  min: number;  // -1.0
  max: number;  // 1.0
  colors: {
    value: number;
    color: string;  // Hex color
  }[];
}

/**
 * Default NDVI color scheme.
 */
export const DEFAULT_NDVI_COLORS: NDVIColorScheme = {
  min: -1.0,
  max: 1.0,
  colors: [
    { value: -1.0, color: '#000080' },  // Blue (water)
    { value: 0.0, color: '#FFFF00' },   // Yellow (bare soil)
    { value: 0.3, color: '#90EE90' },   // Light green (sparse vegetation)
    { value: 0.6, color: '#228B22' },   // Green (moderate vegetation)
    { value: 1.0, color: '#006400' },   // Dark green (dense vegetation)
  ]
};

/**
 * Risk status color mapping.
 */
export const RISK_STATUS_COLORS: Record<string, string> = {
  COMPLIANT: '#10b981',  // Green
  WARNING: '#f59e0b',     // Yellow
  BREACH: '#ef4444',      // Red
  PENDING: '#6b7280',     // Gray
  ERROR: '#dc2626'        // Dark red
};
