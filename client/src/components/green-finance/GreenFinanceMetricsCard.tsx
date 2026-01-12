import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { type GreenFinanceMetrics } from '@/types/greenFinance';
import { LocationTypeBadge } from './LocationTypeBadge';
import { AirQualityIndicator } from './AirQualityIndicator';
import { SustainabilityScoreCard } from './SustainabilityScoreCard';
import { SDGAlignmentPanel } from './SDGAlignmentPanel';
import { Building2, MapPin, Trees } from 'lucide-react';

interface GreenFinanceMetricsCardProps {
  metrics?: GreenFinanceMetrics;
  compact?: boolean;
}

export function GreenFinanceMetricsCard({ metrics, compact = false }: GreenFinanceMetricsCardProps) {
  if (!metrics) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-zinc-500 text-sm">
          No green finance metrics available
        </CardContent>
      </Card>
    );
  }

  if (compact) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          {metrics.location_type && (
            <LocationTypeBadge 
              locationType={metrics.location_type} 
              confidence={metrics.location_confidence}
              compact
            />
          )}
          {metrics.air_quality_index && (
            <AirQualityIndicator 
              aqi={metrics.air_quality_index}
              pm25={metrics.air_quality?.pm25}
              pm10={metrics.air_quality?.pm10}
              no2={metrics.air_quality?.no2}
              compact
            />
          )}
        </div>
        {metrics.composite_sustainability_score !== undefined && (
          <SustainabilityScoreCard 
            compositeScore={metrics.composite_sustainability_score}
            components={metrics.sustainability_components}
            compact
          />
        )}
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Trees className="w-5 h-5 text-green-500" />
          Green Finance Metrics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Location Classification */}
        {metrics.location_type && (
          <div>
            <div className="text-xs text-zinc-400 uppercase tracking-wider mb-2">Location</div>
            <LocationTypeBadge 
              locationType={metrics.location_type} 
              confidence={metrics.location_confidence}
            />
          </div>
        )}

        {/* Air Quality */}
        {metrics.air_quality_index && (
          <AirQualityIndicator 
            aqi={metrics.air_quality_index}
            pm25={metrics.air_quality?.pm25}
            pm10={metrics.air_quality?.pm10}
            no2={metrics.air_quality?.no2}
          />
        )}

        {/* Sustainability Score */}
        {metrics.composite_sustainability_score !== undefined && (
          <SustainabilityScoreCard 
            compositeScore={metrics.composite_sustainability_score}
            components={metrics.sustainability_components}
          />
        )}

        {/* OSM Metrics */}
        {metrics.osm_metrics && (
          <div className="pt-3 border-t border-zinc-800">
            <div className="text-xs text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <MapPin className="w-3 h-3" />
              OpenStreetMap Metrics
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              {metrics.osm_metrics.building_count !== undefined && (
                <div>
                  <div className="text-zinc-400 mb-0.5">Buildings</div>
                  <div className="text-zinc-200 font-medium">{metrics.osm_metrics.building_count}</div>
                </div>
              )}
              {metrics.osm_metrics.road_density !== undefined && (
                <div>
                  <div className="text-zinc-400 mb-0.5">Road Density</div>
                  <div className="text-zinc-200 font-medium">
                    {metrics.osm_metrics.road_density.toFixed(2)} km/km²
                  </div>
                </div>
              )}
              {metrics.osm_metrics.building_density !== undefined && (
                <div>
                  <div className="text-zinc-400 mb-0.5">Building Density</div>
                  <div className="text-zinc-200 font-medium">
                    {metrics.osm_metrics.building_density.toFixed(1)} /km²
                  </div>
                </div>
              )}
              {metrics.osm_metrics.green_infrastructure_coverage !== undefined && (
                <div>
                  <div className="text-zinc-400 mb-0.5">Green Coverage</div>
                  <div className="text-zinc-200 font-medium">
                    {(metrics.osm_metrics.green_infrastructure_coverage * 100).toFixed(1)}%
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* SDG Alignment */}
        {metrics.sdg_alignment && (
          <SDGAlignmentPanel sdgAlignment={metrics.sdg_alignment} />
        )}
      </CardContent>
    </Card>
  );
}
