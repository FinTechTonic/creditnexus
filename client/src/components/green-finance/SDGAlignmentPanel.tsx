import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { type SDGAlignment } from '@/types/greenFinance';
import { Target, CheckCircle2, AlertTriangle } from 'lucide-react';

interface SDGAlignmentPanelProps {
  sdgAlignment?: SDGAlignment;
  compact?: boolean;
}

export function SDGAlignmentPanel({ sdgAlignment, compact = false }: SDGAlignmentPanelProps) {
  if (!sdgAlignment) {
    return (
      <div className="text-xs text-zinc-500">
        No SDG alignment data available
      </div>
    );
  }

  const { sdg_11, sdg_13, sdg_15, overall_alignment, aligned_goals, needs_improvement } = sdgAlignment;

  if (compact) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-zinc-400">Overall SDG Alignment</span>
          <span className="text-sm font-semibold">
            {(overall_alignment * 100).toFixed(0)}%
          </span>
        </div>
        <Progress value={overall_alignment * 100} className="h-1.5" />
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Target className="w-4 h-4 text-blue-500" />
          SDG Alignment
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall Alignment */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Overall Alignment</span>
            <span className="text-lg font-bold">
              {(overall_alignment * 100).toFixed(1)}%
            </span>
          </div>
          <Progress value={overall_alignment * 100} className="h-2" />
        </div>

        {/* Individual SDG Scores */}
        <div className="pt-3 border-t border-zinc-800 space-y-3">
          <div className="text-xs text-zinc-400 uppercase tracking-wider mb-2">SDG Goals</div>
          
          {sdg_11 !== undefined && (
            <SDGGoalBar
              goal="SDG 11"
              label="Sustainable Cities and Communities"
              score={sdg_11}
            />
          )}
          {sdg_13 !== undefined && (
            <SDGGoalBar
              goal="SDG 13"
              label="Climate Action"
              score={sdg_13}
            />
          )}
          {sdg_15 !== undefined && (
            <SDGGoalBar
              goal="SDG 15"
              label="Life on Land"
              score={sdg_15}
            />
          )}
        </div>

        {/* Status Summary */}
        {(aligned_goals.length > 0 || needs_improvement.length > 0) && (
          <div className="pt-3 border-t border-zinc-800 space-y-2">
            {aligned_goals.length > 0 && (
              <div className="flex items-start gap-2 text-xs">
                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-zinc-400 mb-1">Aligned Goals (≥70%)</div>
                  <div className="flex flex-wrap gap-1">
                    {aligned_goals.map((goal) => (
                      <span key={goal} className="px-2 py-0.5 bg-green-500/20 text-green-500 rounded text-[10px]">
                        {goal}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
            {needs_improvement.length > 0 && (
              <div className="flex items-start gap-2 text-xs">
                <AlertTriangle className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-zinc-400 mb-1">Needs Improvement (&lt;50%)</div>
                  <div className="flex flex-wrap gap-1">
                    {needs_improvement.map((goal) => (
                      <span key={goal} className="px-2 py-0.5 bg-orange-500/20 text-orange-500 rounded text-[10px]">
                        {goal}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SDGGoalBar({ goal, label, score }: { goal: string; label: string; score: number }) {
  const getScoreColor = (score: number) => {
    if (score >= 0.7) return 'text-green-500';
    if (score >= 0.5) return 'text-yellow-500';
    return 'text-orange-500';
  };

  const getProgressColor = (score: number) => {
    if (score >= 0.7) return 'bg-green-500';
    if (score >= 0.5) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-zinc-300">{goal}</span>
          <span className="text-zinc-500 text-[10px]">{label}</span>
        </div>
        <span className={`font-medium ${getScoreColor(score)}`}>
          {(score * 100).toFixed(0)}%
        </span>
      </div>
      <div className="relative">
        <Progress value={score * 100} className="h-1.5" />
        <div 
          className={`absolute top-0 left-0 h-1.5 rounded-full ${getProgressColor(score)}`}
          style={{ width: `${score * 100}%` }}
        />
      </div>
    </div>
  );
}
