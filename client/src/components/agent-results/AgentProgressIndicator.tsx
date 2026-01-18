/**
 * Agent Progress Indicator Component
 * 
 * Displays real-time progress for agent workflows:
 * - Current step/agent
 * - Progress percentage
 * - Estimated time remaining
 * - Status messages
 * - Cancel action (if supported)
 */

import {
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  XCircle,
  Activity,
  X
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export type AgentProgressStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface AgentProgressStep {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  message?: string;
  timestamp?: Date;
}

export interface AgentProgressIndicatorProps {
  agentType: 'deepresearch' | 'langalpha' | 'peoplehub';
  status: AgentProgressStatus;
  currentStep?: string;
  progress?: number; // 0-100
  steps?: AgentProgressStep[];
  message?: string;
  estimatedTimeRemaining?: number; // seconds
  onCancel?: () => void;
  className?: string;
}

export function AgentProgressIndicator({
  agentType,
  status,
  currentStep,
  progress,
  steps,
  message,
  estimatedTimeRemaining,
  onCancel,
  className = ''
}: AgentProgressIndicatorProps) {
  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-400" />;
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-emerald-400" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-400" />;
      case 'cancelled':
        return <XCircle className="h-5 w-5 text-slate-400" />;
      default:
        return <Clock className="h-5 w-5 text-amber-400" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' };
      case 'completed':
        return { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30' };
      case 'failed':
        return { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' };
      case 'cancelled':
        return { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/30' };
      default:
        return { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30' };
    }
  };

  const getAgentLabel = () => {
    switch (agentType) {
      case 'deepresearch':
        return 'DeepResearch';
      case 'langalpha':
        return 'LangAlpha';
      case 'peoplehub':
        return 'PeopleHub';
      default:
        return 'Agent';
    }
  };

  const formatTimeRemaining = (seconds: number): string => {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${minutes}m ${secs}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  };

  const statusColors = getStatusColor();
  const displayProgress = progress !== undefined ? progress : (status === 'completed' ? 100 : status === 'failed' ? 0 : undefined);

  return (
    <Card className={`bg-slate-800 border-slate-700 ${statusColors.border} ${className}`}>
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {getStatusIcon()}
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-100">{getAgentLabel()}</span>
                  <Badge className={statusColors.bg}>
                    <span className={statusColors.text}>
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </span>
                  </Badge>
                </div>
                {currentStep && (
                  <p className="text-sm text-slate-400 mt-1">
                    {currentStep}
                  </p>
                )}
              </div>
            </div>
            {onCancel && status === 'running' && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onCancel}
                className="h-8 w-8 text-slate-400 hover:text-red-400"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* Progress Bar */}
          {displayProgress !== undefined && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Progress</span>
                <span className="text-slate-300">{displayProgress}%</span>
              </div>
              <Progress 
                value={displayProgress} 
                className="h-2"
              />
            </div>
          )}

          {/* Message */}
          {message && (
            <div className="flex items-start gap-2 p-2 bg-slate-900/50 rounded-lg">
              <Activity className="h-4 w-4 text-slate-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-slate-300 flex-1">{message}</p>
            </div>
          )}

          {/* Steps */}
          {steps && steps.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Steps</p>
              <div className="space-y-1">
                {steps.map((step, idx) => {
                  const stepColors = {
                    pending: { bg: 'bg-slate-700/30', text: 'text-slate-400', icon: Clock },
                    running: { bg: 'bg-blue-500/20', text: 'text-blue-400', icon: Loader2 },
                    completed: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', icon: CheckCircle2 },
                    failed: { bg: 'bg-red-500/20', text: 'text-red-400', icon: AlertCircle },
                    skipped: { bg: 'bg-slate-700/30', text: 'text-slate-500', icon: XCircle }
                  };
                  const stepConfig = stepColors[step.status];
                  const StepIcon = stepConfig.icon;
                  
                  return (
                    <div
                      key={idx}
                      className={`flex items-center gap-2 p-2 rounded-lg ${stepConfig.bg}`}
                    >
                      <StepIcon 
                        className={`h-4 w-4 ${stepConfig.text} ${step.status === 'running' ? 'animate-spin' : ''}`} 
                      />
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm ${stepConfig.text}`}>
                          {step.name}
                        </p>
                        {step.message && (
                          <p className="text-xs text-slate-400 mt-0.5">
                            {step.message}
                          </p>
                        )}
                      </div>
                      {step.timestamp && (
                        <span className="text-xs text-slate-500">
                          {step.timestamp.toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Estimated Time Remaining */}
          {estimatedTimeRemaining !== undefined && status === 'running' && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Clock className="h-3 w-3" />
              <span>Estimated time remaining: {formatTimeRemaining(estimatedTimeRemaining)}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
