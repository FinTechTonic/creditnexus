import { getAQILevel, getAQIColor, type AQILevel } from '@/types/greenFinance';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, CheckCircle2, AlertTriangle } from 'lucide-react';

interface AirQualityIndicatorProps {
  aqi?: number;
  pm25?: number;
  pm10?: number;
  no2?: number;
  compact?: boolean;
}

export function AirQualityIndicator({ aqi, pm25, pm10, no2, compact = false }: AirQualityIndicatorProps) {
  if (!aqi && !pm25 && !pm10 && !no2) {
    return (
      <div className="text-xs text-zinc-500">
        No air quality data available
      </div>
    );
  }

  const displayAQI = aqi || 50; // Default to moderate if not provided
  const level = getAQILevel(displayAQI);
  const colorClass = getAQIColor(displayAQI);

  const getStatusIcon = (level: AQILevel) => {
    switch (level) {
      case 'good':
      case 'moderate':
        return <CheckCircle2 className="w-4 h-4" />;
      case 'unhealthy_sensitive':
        return <AlertTriangle className="w-4 h-4" />;
      default:
        return <AlertCircle className="w-4 h-4" />;
    }
  };

  const getStatusLabel = (level: AQILevel) => {
    switch (level) {
      case 'good': return 'Good';
      case 'moderate': return 'Moderate';
      case 'unhealthy_sensitive': return 'Unhealthy for Sensitive Groups';
      case 'unhealthy': return 'Unhealthy';
      case 'very_unhealthy': return 'Very Unhealthy';
      case 'hazardous': return 'Hazardous';
      default: return 'Unknown';
    }
  };

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs ${colorClass}`}>
        {getStatusIcon(level)}
        <span className="font-semibold">AQI: {Math.round(displayAQI)}</span>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <div className={`p-1.5 rounded ${colorClass}`}>
            {getStatusIcon(level)}
          </div>
          Air Quality Index
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-2xl font-bold">{Math.round(displayAQI)}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${colorClass}`}>
              {getStatusLabel(level)}
            </span>
          </div>
          <div className="w-full bg-zinc-800 rounded-full h-2 mt-2">
            <div
              className={`h-2 rounded-full transition-all ${
                level === 'good' ? 'bg-green-500' :
                level === 'moderate' ? 'bg-yellow-500' :
                level === 'unhealthy_sensitive' ? 'bg-orange-500' :
                level === 'unhealthy' ? 'bg-red-500' :
                level === 'very_unhealthy' ? 'bg-purple-500' :
                'bg-red-800'
              }`}
              style={{ width: `${Math.min(100, (displayAQI / 500) * 100)}%` }}
            />
          </div>
        </div>

        {(pm25 || pm10 || no2) && (
          <div className="pt-2 border-t border-zinc-800 space-y-1.5">
            <div className="text-xs text-zinc-400 uppercase tracking-wider mb-2">Measurements</div>
            {pm25 && (
              <div className="flex justify-between text-xs">
                <span className="text-zinc-400">PM2.5</span>
                <span className="text-zinc-300">{pm25.toFixed(1)} µg/m³</span>
              </div>
            )}
            {pm10 && (
              <div className="flex justify-between text-xs">
                <span className="text-zinc-400">PM10</span>
                <span className="text-zinc-300">{pm10.toFixed(1)} µg/m³</span>
              </div>
            )}
            {no2 && (
              <div className="flex justify-between text-xs">
                <span className="text-zinc-400">NO₂</span>
                <span className="text-zinc-300">{no2.toFixed(1)} µg/m³</span>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
