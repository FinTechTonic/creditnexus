import { type LocationType } from '@/types/greenFinance';
import { Building2, Home, Trees } from 'lucide-react';

interface LocationTypeBadgeProps {
  locationType?: LocationType | string;
  confidence?: number;
  compact?: boolean;
}

export function LocationTypeBadge({ locationType, confidence, compact = false }: LocationTypeBadgeProps) {
  if (!locationType) {
    return null;
  }

  const normalizedType = locationType.toLowerCase() as LocationType;

  const getIcon = (type: LocationType) => {
    switch (type) {
      case 'urban':
        return <Building2 className="w-3.5 h-3.5" />;
      case 'suburban':
        return <Home className="w-3.5 h-3.5" />;
      case 'rural':
        return <Trees className="w-3.5 h-3.5" />;
      default:
        return <Building2 className="w-3.5 h-3.5" />;
    }
  };

  const getColorClass = (type: LocationType) => {
    switch (type) {
      case 'urban':
        return 'bg-blue-500/20 text-blue-500 border-blue-500/30';
      case 'suburban':
        return 'bg-purple-500/20 text-purple-500 border-purple-500/30';
      case 'rural':
        return 'bg-green-500/20 text-green-500 border-green-500/30';
      default:
        return 'bg-gray-500/20 text-gray-500 border-gray-500/30';
    }
  };

  const getLabel = (type: LocationType) => {
    return type.charAt(0).toUpperCase() + type.slice(1);
  };

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs border ${getColorClass(normalizedType)}`}>
        {getIcon(normalizedType)}
        <span className="font-medium capitalize">{getLabel(normalizedType)}</span>
        {confidence !== undefined && (
          <span className="text-[10px] opacity-70">
            {(confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md border ${getColorClass(normalizedType)}`}>
      {getIcon(normalizedType)}
      <span className="font-medium capitalize">{getLabel(normalizedType)}</span>
      {confidence !== undefined && (
        <span className="text-xs opacity-70">
          {(confidence * 100).toFixed(0)}% confidence
        </span>
      )}
    </div>
  );
}
