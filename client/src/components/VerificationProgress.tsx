/**
 * Verification Progress Display Component.
 * 
 * Replaces simple button spinner with detailed progress display showing:
 * - Progress bar with percentage
 * - Current stage indicator
 * - Stage checklist
 * - Estimated time remaining
 * - Cancel button
 */

import { useEffect, useState } from 'react';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, Circle, Loader2, X, AlertCircle } from 'lucide-react';
import type { VerificationProgress as VerificationProgressType } from '@/types/layers';

interface VerificationProgressProps {
  progress?: VerificationProgressType;
  currentStage?: string;
  percentage?: number;
  estimatedSecondsRemaining?: number;
  stages?: StageInfo[];
  onCancel?: () => void;
  error?: string | null;
  className?: string;
}

interface StageInfo {
  id: string;
  name: string;
  status: 'pending' | 'in_progress' | 'complete' | 'error';
  message?: string;
}

const STAGE_NAMES: Record<string, string> = {
  geocoding: 'Geocoding Address',
  fetching_bands: 'Fetching Satellite Data',
  calculating_ndvi: 'Calculating NDVI',
  classifying: 'Land Use Classification',
  generating_layers: 'Generating Layers',
  complete: 'Complete'
};

export function VerificationProgress({
  progress,
  currentStage,
  percentage = 0,
  estimatedSecondsRemaining,
  stages: providedStages,
  onCancel,
  error,
  className = ''
}: VerificationProgressProps) {
  const [stages, setStages] = useState<StageInfo[]>(providedStages || []);

  // Update stages based on progress
  useEffect(() => {
    if (progress) {
      const stageId = progress.stage;
      const stageName = STAGE_NAMES[stageId] || stageId;
      
      setStages(prev => {
        const updated = [...prev];
        
        // Mark previous stages as complete
        const currentIndex = updated.findIndex(s => s.id === stageId);
        if (currentIndex > 0) {
          for (let i = 0; i < currentIndex; i++) {
            if (updated[i].status !== 'complete') {
              updated[i] = { ...updated[i], status: 'complete' };
            }
          }
        }
        
        // Update current stage
        const stageIndex = updated.findIndex(s => s.id === stageId);
        if (stageIndex !== -1) {
          updated[stageIndex] = {
            ...updated[stageIndex],
            status: 'in_progress',
            message: progress.message || `${stageName}...`
          };
        } else {
          // Add new stage
          updated.push({
            id: stageId,
            name: stageName,
            status: 'in_progress',
            message: progress.message
          });
        }
        
        return updated;
      });
    }
  }, [progress]);

  // Calculate percentage from progress or use provided
  const displayPercentage = progress?.percentage ?? percentage;
  const displayStage = progress?.stage ?? currentStage ?? 'pending';
  const displayEstimatedTime = progress?.estimated_seconds_remaining ?? estimatedSecondsRemaining;

  const formatTimeRemaining = (seconds?: number): string => {
    if (!seconds) return '';
    if (seconds < 60) return `${Math.round(seconds)} seconds`;
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${minutes}m ${secs}s`;
  };

  const getStageIcon = (status: StageInfo['status']) => {
    switch (status) {
      case 'complete':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'in_progress':
        return <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Circle className="w-5 h-5 text-zinc-500" />;
    }
  };

  return (
    <Card className={`bg-zinc-900/50 border-zinc-700 ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-white">
            Verification Progress
          </CardTitle>
          {onCancel && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
              className="text-zinc-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-400">
              {STAGE_NAMES[displayStage] || displayStage}
            </span>
            <span className="text-white font-mono">
              {Math.round(displayPercentage)}%
            </span>
          </div>
          <Progress 
            value={displayPercentage} 
            className="h-2 bg-zinc-800"
          />
        </div>

        {/* Estimated Time */}
        {displayEstimatedTime !== undefined && displayEstimatedTime > 0 && (
          <div className="text-xs text-zinc-500">
            Estimated time remaining: {formatTimeRemaining(displayEstimatedTime)}
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="p-3 bg-red-900/20 border border-red-700/50 rounded-lg">
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{error}</span>
            </div>
          </div>
        )}

        {/* Stage Checklist */}
        {stages.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-zinc-700">
            <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
              Stages
            </div>
            {stages.map((stage) => (
              <div
                key={stage.id}
                className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${
                  stage.status === 'in_progress'
                    ? 'bg-indigo-500/10 border border-indigo-500/20'
                    : stage.status === 'complete'
                    ? 'bg-green-500/10 border border-green-500/20'
                    : stage.status === 'error'
                    ? 'bg-red-500/10 border border-red-500/20'
                    : 'bg-zinc-800/50 border border-zinc-700/50'
                }`}
              >
                {getStageIcon(stage.status)}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white">
                    {stage.name}
                  </div>
                  {stage.message && (
                    <div className="text-xs text-zinc-400 mt-0.5">
                      {stage.message}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Current Layer Info (if fetching bands) */}
        {progress?.stage === 'fetching_bands' && progress.band && (
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
            <div className="text-xs text-indigo-400">
              Processing band {progress.band} ({progress.current}/{progress.total})
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
