/**
 * Green Finance TypeScript interfaces and types
 * 
 * These types correspond to the backend green finance models and API responses.
 */

export interface EnvironmentalMetrics {
  air_quality_index?: number;
  pm25?: number;
  pm10?: number;
  no2?: number;
  o3?: number;
  so2?: number;
  co?: number;
  vehicle_emissions?: number;
  methane_level?: number;
}

export interface UrbanActivityMetrics {
  vehicle_count?: number;
  vehicle_density?: number;
  road_density?: number;
  building_density?: number;
  building_count?: number;
  poi_count?: number;
  traffic_flow?: number;
}

export interface SustainabilityComponents {
  vegetation_health: number;
  air_quality: number;
  urban_activity: number;
  green_infrastructure: number;
  pollution_levels: number;
}

export interface SDGAlignment {
  sdg_11?: number;
  sdg_13?: number;
  sdg_15?: number;
  overall_alignment: number;
  aligned_goals: string[];
  needs_improvement: string[];
}

export interface GreenFinanceMetrics {
  location_type?: string;
  location_confidence?: number;
  air_quality_index?: number;
  composite_sustainability_score?: number;
  sustainability_components?: SustainabilityComponents;
  osm_metrics?: UrbanActivityMetrics & {
    green_infrastructure_coverage?: number;
  };
  air_quality?: {
    pm25?: number;
    pm10?: number;
    no2?: number;
    o3?: number;
    so2?: number;
    co?: number;
    data_source?: string;
  };
  sdg_alignment?: SDGAlignment;
}

export interface GreenFinanceAssessment {
  id: number;
  transaction_id: string;
  deal_id?: number;
  loan_asset_id?: number;
  location_lat: number;
  location_lon: number;
  location_type?: string;
  location_confidence?: number;
  environmental_metrics?: EnvironmentalMetrics;
  urban_activity_metrics?: UrbanActivityMetrics;
  sustainability_score?: number;
  sustainability_components?: SustainabilityComponents;
  sdg_alignment?: SDGAlignment;
  policy_decisions?: any[];
  cdm_events?: any[];
  assessed_at: string;
  created_at: string;
  updated_at: string;
}

export interface GreenFinanceAssessmentRequest {
  location_lat: number;
  location_lon: number;
  transaction_id?: string;
  deal_id?: number;
  loan_asset_id?: number;
}

export interface UrbanSustainabilityAssessment {
  location_type: string;
  location_confidence: number;
  urban_sustainability_score: number;
  metrics: {
    road_density: number;
    building_density: number;
    green_coverage: number;
    air_quality_index: number;
  };
  compliance_status: 'compliant' | 'needs_improvement';
}

export interface EmissionsCompliance {
  compliance_status: 'compliant' | 'warning' | 'non_compliant';
  air_quality_index: number;
  violations: Array<{
    parameter: string;
    value: number;
    limit: number;
    unit: string;
  }>;
  measurements: {
    pm25?: number;
    pm10?: number;
    no2?: number;
  };
}

export type LocationType = 'urban' | 'suburban' | 'rural';

export type AQILevel = 'good' | 'moderate' | 'unhealthy_sensitive' | 'unhealthy' | 'very_unhealthy' | 'hazardous';

export function getAQILevel(aqi: number): AQILevel {
  if (aqi <= 50) return 'good';
  if (aqi <= 100) return 'moderate';
  if (aqi <= 150) return 'unhealthy_sensitive';
  if (aqi <= 200) return 'unhealthy';
  if (aqi <= 300) return 'very_unhealthy';
  return 'hazardous';
}

export function getAQIColor(aqi: number): string {
  const level = getAQILevel(aqi);
  switch (level) {
    case 'good': return 'text-green-500 bg-green-500/20';
    case 'moderate': return 'text-yellow-500 bg-yellow-500/20';
    case 'unhealthy_sensitive': return 'text-orange-500 bg-orange-500/20';
    case 'unhealthy': return 'text-red-500 bg-red-500/20';
    case 'very_unhealthy': return 'text-purple-500 bg-purple-500/20';
    case 'hazardous': return 'text-red-800 bg-red-800/20';
    default: return 'text-gray-500 bg-gray-500/20';
  }
}
