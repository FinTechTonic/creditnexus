import { useMemo } from 'react';
import { Clock, User, FileText, Workflow, Shield, AlertCircle, CheckCircle, XCircle } from 'lucide-react';

export interface AuditEvent {
  id: number;
  occurred_at: string;
  action: string;
  target_type: string;
  target_id: number | null;
  user?: {
    id: number;
    name: string;
    email: string;
  } | null;
  action_metadata?: Record<string, any>;
}

interface AuditTimelineProps {
  events: AuditEvent[];
  onEventClick?: (event: AuditEvent) => void;
  height?: number;
}

export function AuditTimeline({ events, onEventClick, height = 400 }: AuditTimelineProps) {
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => 
      new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()
    );
  }, [events]);

  const getActionIcon = (action: string) => {
    if (action.includes('create') || action.includes('approve')) {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    }
    if (action.includes('delete') || action.includes('reject')) {
      return <XCircle className="h-4 w-4 text-red-500" />;
    }
    if (action.includes('update') || action.includes('edit')) {
      return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
    return <Clock className="h-4 w-4 text-blue-500" />;
  };

  const getTargetIcon = (targetType: string) => {
    switch (targetType?.toLowerCase()) {
      case 'document':
        return <FileText className="h-3 w-3" />;
      case 'workflow':
        return <Workflow className="h-3 w-3" />;
      case 'deal':
        return <Shield className="h-3 w-3" />;
      default:
        return <FileText className="h-3 w-3" />;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (sortedEvents.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <div className="text-center">
          <Clock className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No audit events found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative" style={{ minHeight: `${height}px` }}>
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-700" />
      
      <div className="space-y-4">
        {sortedEvents.map((event, index) => (
          <div
            key={event.id}
            className="relative flex items-start gap-4 group cursor-pointer hover:bg-slate-800/50 rounded-lg p-3 transition-colors"
            onClick={() => onEventClick?.(event)}
          >
            {/* Timeline dot */}
            <div className="relative z-10 flex items-center justify-center w-8 h-8 rounded-full bg-slate-800 border-2 border-slate-600 group-hover:border-emerald-500 transition-colors">
              {getActionIcon(event.action)}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-slate-100 capitalize">
                      {event.action.replace(/_/g, ' ')}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-slate-400">
                      {getTargetIcon(event.target_type)}
                      <span className="capitalize">{event.target_type}</span>
                      {event.target_id && (
                        <span className="text-slate-500">#{event.target_id}</span>
                      )}
                    </span>
                  </div>
                  
                  {event.user && (
                    <div className="flex items-center gap-2 text-sm text-slate-400 mb-1">
                      <User className="h-3 w-3" />
                      <span>{event.user.name}</span>
                      <span className="text-slate-500">({event.user.email})</span>
                    </div>
                  )}
                  
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Clock className="h-3 w-3" />
                    <span>{formatDate(event.occurred_at)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
