/**
 * Agent Result Card Component
 * 
 * Reusable card component for displaying agent results in lists/grids.
 * Shows agent type, timestamp, status, and quick preview.
 */

import {
  Search,
  BarChart3,
  User,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Eye,
  Download,
  Link as LinkIcon,
  ExternalLink
} from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export type AgentType = 'deepresearch' | 'langalpha' | 'peoplehub';

interface AgentResultCardProps {
  agentType: AgentType;
  id: string;
  title: string;
  query?: string;
  status: 'completed' | 'in_progress' | 'pending' | 'failed';
  timestamp: string;
  preview?: string;
  onView?: () => void;
  onDownload?: () => void;
  onAttach?: () => void;
  dealId?: number | null;
  className?: string;
}

export function AgentResultCard({
  agentType,
  id: _id, // Prefix with _ - unused
  title,
  query,
  status,
  timestamp,
  preview,
  onView,
  onDownload,
  onAttach,
  dealId,
  className = ''
}: AgentResultCardProps) {
  const getAgentIcon = () => {
    switch (agentType) {
      case 'deepresearch':
        return <Search className="h-5 w-5" />;
      case 'langalpha':
        return <BarChart3 className="h-5 w-5" />;
      case 'peoplehub':
        return <User className="h-5 w-5" />;
      default:
        return <Search className="h-5 w-5" />;
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

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case 'in_progress':
        return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-amber-400" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-400" />;
      default:
        return <Clock className="h-4 w-4 text-slate-400" />;
    }
  };

  const statusColors: Record<string, { bg: string; text: string }> = {
    completed: { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
    in_progress: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
    pending: { bg: 'bg-amber-500/20', text: 'text-amber-400' },
    failed: { bg: 'bg-red-500/20', text: 'text-red-400' }
  };

  return (
    <Card className={`bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="text-emerald-400 flex-shrink-0">
              {getAgentIcon()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold text-slate-100 truncate">{title}</h3>
                <Badge variant="outline" className="text-xs flex-shrink-0">
                  {getAgentLabel()}
                </Badge>
              </div>
              {query && (
                <p className="text-sm text-slate-400 truncate" title={query}>
                  {query}
                </p>
              )}
            </div>
          </div>
          <Badge className={`${statusColors[status]?.bg || 'bg-slate-500/20'} flex items-center gap-1 flex-shrink-0`}>
            {getStatusIcon()}
            <span className={statusColors[status]?.text || 'text-slate-400'}>
              {status.replace('_', ' ')}
            </span>
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-3">
          {/* Preview */}
          {preview && (
            <p className="text-sm text-slate-300 line-clamp-2">{preview}</p>
          )}

          {/* Metadata */}
          <div className="flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>{new Date(timestamp).toLocaleString()}</span>
            </div>
            {dealId && (
              <div className="flex items-center gap-1">
                <LinkIcon className="h-3 w-3" />
                <span>Deal {dealId}</span>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-2 border-t border-slate-700">
            {onView && (
              <Button
                variant="outline"
                size="sm"
                onClick={onView}
                className="flex-1"
              >
                <Eye className="h-4 w-4 mr-2" />
                View
              </Button>
            )}
            {onDownload && status === 'completed' && (
              <Button
                variant="outline"
                size="sm"
                onClick={onDownload}
                className="flex-1"
              >
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            )}
            {onAttach && dealId && status === 'completed' && (
              <Button
                variant="outline"
                size="sm"
                onClick={onAttach}
                className="flex-1"
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Attach
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
