import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { type SustainabilityComponents } from '@/types/greenFinance';
import { Leaf, Wind, Activity, Trees, AlertCircle } from 'lucide-react';

interface SustainabilityScoreCardProps {
  compositeScore?: number;
  components?: SustainabilityComponents;
  compact?: boolean;
}

export function SustainabilityScoreCard({ compositeScore, components, compact = false }: SustainabilityScoreCardProps) {
  if (compositeScore === undefined && !components) {
    return (
      <div className="text-xs text-zinc-500">
        No sustainability data available
      </div>
    );
  }

  const score = compositeScore || 0.5;
  const scorePercentage = score * 100;

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-500';
    if (score >= 0.6) return 'text-yellow-500';
    if (score >= 0.4) return 'text-orange-500';
    return 'text-red-500';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.6) return 'bg-yellow-500';
    if (score >= 0.4) return 'bg-orange-500';
    return 'bg-red-500';
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-zinc-400">Sustainability</span>
            <span className={`text-sm font-semibold ${getScoreColor(score)}`}>
              {(scorePercentage).toFixed(0)}%
            </span>
          </div>
          <Progress value={scorePercentage} className="h-1.5" />
        </div>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Leaf className="w-4 h-4 text-green-500" />
          Composite Sustainability Score
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className={`text-3xl font-bold ${getScoreColor(score)}`}>
              {(scorePercentage).toFixed(1)}%
            </span>
            <span className="text-xs text-zinc-400">/ 100%</span>
          </div>
          <Progress value={scorePercentage} className="h-2" />
        </div>

        {components && (
          <div className="pt-3 border-t border-zinc-800 space-y-2">
            <div className="text-xs text-zinc-400 uppercase tracking-wider mb-2">Component Breakdown</div>
            
            <div className="space-y-2">
              <ComponentBar
                label="Vegetation Health"
                value={components.vegetation_health}
                icon={<Leaf className="w-3 h-3" />}
                color="text-green-500"
              />
              <ComponentBar
                label="Air Quality"
                value={components.air_quality}
                icon={<Wind className="w-3 h-3" />}
                color="text-blue-500"
              />
              <ComponentBar
                label="Urban Activity"
                value={components.urban_activity}
                icon={<Activity className="w-3 h-3" />}
                color="text-purple-500"
              />
              <ComponentBar
                label="Green Infrastructure"
                value={components.green_infrastructure}
                icon={<Trees className="w-3 h-3" />}
                color="text-emerald-500"
              />
              <ComponentBar
                label="Pollution Levels"
                value={components.pollution_levels}
                icon={<AlertCircle className="w-3 h-3" />}
                color="text-red-500"
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ComponentBar({ label, value, icon, color }: { label: string; value: number; icon: React.ReactNode; color: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5">
          <span className={color}>{icon}</span>
          <span className="text-zinc-400">{label}</span>
        </div>
        <span className="text-zinc-300 font-medium">{(value * 100).toFixed(0)}%</span>
      </div>
      <Progress value={value * 100} className="h-1.5" />
    </div>
  );
}
