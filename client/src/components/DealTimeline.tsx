import { useMemo } from 'react';
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  FileText,
  MessageSquare,
  GitBranch,
  ArrowRight,
  RefreshCw,
  Shield,
  Eye
} from 'lucide-react';

export interface TimelineEvent {
  event_type: string;
  timestamp: string | null;
  data: Record<string, unknown>;
  status?: 'success' | 'failure' | 'pending' | 'review_needed' | 'warning';
  verification_step?: boolean;
  requires_review?: boolean;
  branch_id?: string; // For branching paths
  parent_branch?: string; // Parent branch for nested branches
}

interface DealTimelineProps {
  events: TimelineEvent[] | null | undefined;
  dealStatus?: string;
  className?: string;
}

interface Node {
  id: string;
  event: TimelineEvent;
  x: number;
  y: number;
  width: number;
  height: number;
  status: 'success' | 'failure' | 'pending' | 'review_needed' | 'warning' | 'default';
  hasBranch: boolean;
  branchId?: string;
  parentBranch?: string;
}

const NODE_WIDTH = 200;
const NODE_HEIGHT = 100;
const HORIZONTAL_SPACING = 250;
const VERTICAL_SPACING = 150;
const PIPE_WIDTH = 4;

// Color scheme for different statuses
const STATUS_COLORS = {
  success: {
    node: 'bg-emerald-500',
    border: 'border-emerald-400',
    pipe: '#10b981', // emerald-500
    text: 'text-emerald-100'
  },
  failure: {
    node: 'bg-red-500',
    border: 'border-red-400',
    pipe: '#ef4444', // red-500
    text: 'text-red-100'
  },
  pending: {
    node: 'bg-yellow-500',
    border: 'border-yellow-400',
    pipe: '#eab308', // yellow-500
    text: 'text-yellow-100'
  },
  review_needed: {
    node: 'bg-blue-500',
    border: 'border-blue-400',
    pipe: '#3b82f6', // blue-500
    text: 'text-blue-100'
  },
  warning: {
    node: 'bg-orange-500',
    border: 'border-orange-400',
    pipe: '#f97316', // orange-500
    text: 'text-orange-100'
  },
  default: {
    node: 'bg-slate-500',
    border: 'border-slate-400',
    pipe: '#64748b', // slate-500
    text: 'text-slate-100'
  }
};

const getEventStatus = (event: TimelineEvent): TimelineEvent['status'] => {
  if (event.status) return event.status;
  
  // Infer status from event type and data
  const eventType = event.event_type.toLowerCase();
  const data = event.data || {};
  
  if (eventType.includes('approved') || eventType.includes('success') || eventType.includes('completed')) {
    return 'success';
  }
  if (eventType.includes('rejected') || eventType.includes('failed') || eventType.includes('error')) {
    return 'failure';
  }
  if (eventType.includes('review') || event.requires_review) {
    return 'review_needed';
  }
  if (eventType.includes('pending') || eventType.includes('waiting')) {
    return 'pending';
  }
  if (eventType.includes('warning') || eventType.includes('flag')) {
    return 'warning';
  }
  
  return 'default';
};

const getEventIcon = (event: TimelineEvent, status: string) => {
  if (event.verification_step) {
    return <Shield className="h-5 w-5" />;
  }
  
  switch (status) {
    case 'success':
      return <CheckCircle className="h-5 w-5" />;
    case 'failure':
      return <XCircle className="h-5 w-5" />;
    case 'review_needed':
      return <Eye className="h-5 w-5" />;
    case 'pending':
      return <Clock className="h-5 w-5" />;
    case 'warning':
      return <AlertCircle className="h-5 w-5" />;
    default:
      if (event.event_type.includes('document')) {
        return <FileText className="h-5 w-5" />;
      }
      if (event.event_type.includes('note') || event.event_type.includes('message')) {
        return <MessageSquare className="h-5 w-5" />;
      }
      return <Clock className="h-5 w-5" />;
  }
};

const formatEventType = (eventType: string): string => {
  return eventType
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
};

export function DealTimeline({ events, dealStatus, className = '' }: DealTimelineProps) {
  // Process events and create nodes with positions
  const nodes = useMemo(() => {
    if (!events || events.length === 0) {
      return [];
    }
    
    const processedNodes: Node[] = [];
    const branchMap = new Map<string, number>(); // Track vertical positions for branches
    let currentX = 50;
    let mainBranchY = 50;
    
    events.forEach((event, index) => {
      const status = getEventStatus(event);
      const hasBranch = !!event.branch_id || !!event.verification_step;
      
      let y = mainBranchY;
      
      // Handle branching
      if (event.branch_id) {
        if (!branchMap.has(event.branch_id)) {
          branchMap.set(event.branch_id, mainBranchY + VERTICAL_SPACING);
        }
        y = branchMap.get(event.branch_id)!;
      } else if (event.parent_branch) {
        // Nested branch - offset further
        const parentY = branchMap.get(event.parent_branch) || mainBranchY;
        y = parentY + VERTICAL_SPACING;
      }
      
      const node: Node = {
        id: `node-${index}`,
        event,
        x: currentX,
        y,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        status,
        hasBranch,
        branchId: event.branch_id,
        parentBranch: event.parent_branch
      };
      
      processedNodes.push(node);
      
      // Move to next position
      if (!event.branch_id && !event.parent_branch) {
        // Main branch - move forward
        currentX += HORIZONTAL_SPACING;
        mainBranchY = y;
      } else {
        // Branch - move forward but keep same X for parallel branches
        if (index < events.length - 1 && !events[index + 1].branch_id) {
          currentX += HORIZONTAL_SPACING;
        }
      }
    });
    
    return processedNodes;
  }, [events]);
  
  // Calculate SVG dimensions
  const svgWidth = useMemo(() => {
    if (nodes.length === 0) return 800;
    const maxX = Math.max(...nodes.map(n => n.x + n.width));
    return maxX + 100;
  }, [nodes]);
  
  const svgHeight = useMemo(() => {
    if (nodes.length === 0) return 400;
    const maxY = Math.max(...nodes.map(n => n.y + n.height));
    return maxY + 100;
  }, [nodes]);
  
  // Generate pipe connections
  const pipes = useMemo(() => {
    const connections: Array<{
      from: Node;
      to: Node;
      isBranch: boolean;
    }> = [];
    
    for (let i = 0; i < nodes.length - 1; i++) {
      const from = nodes[i];
      const to = nodes[i + 1];
      
      // Check if this is a branch connection
      const isBranch = !!to.branchId || !!to.parentBranch;
      
      connections.push({ from, to, isBranch });
    }
    
    return connections;
  }, [nodes]);
  
  // Handle null/undefined or empty events
  if (!events || events.length === 0) {
    return (
      <div className={`bg-slate-800 border border-slate-700 rounded-lg p-8 text-center ${className}`}>
        <Clock className="h-12 w-12 text-slate-500 mx-auto mb-4" />
        <p className="text-slate-400">No timeline events yet</p>
      </div>
    );
  }
  
  return (
    <div className={`bg-slate-900 border border-slate-700 rounded-lg p-6 overflow-auto ${className}`}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-100">Deal Timeline</h3>
        {dealStatus && (
          <span className="text-sm text-slate-400">Status: {dealStatus.replace(/_/g, ' ').toUpperCase()}</span>
        )}
      </div>
      
      <div className="relative" style={{ minHeight: `${svgHeight}px` }}>
        <svg
          width={svgWidth}
          height={svgHeight}
          className="absolute inset-0"
          style={{ overflow: 'visible' }}
        >
          {/* Render pipes/connections */}
          {pipes.map((pipe, index) => {
            const fromX = pipe.from.x + pipe.from.width;
            const fromY = pipe.from.y + pipe.from.height / 2;
            const toX = pipe.to.x;
            const toY = pipe.to.y + pipe.to.height / 2;
            
            const pipeColor = STATUS_COLORS[pipe.from.status].pipe;
            const isBranch = pipe.isBranch;
            
            // For branches, create a curved path
            if (isBranch) {
              const midX = (fromX + toX) / 2;
              const controlY = fromY + (toY > fromY ? VERTICAL_SPACING / 2 : -VERTICAL_SPACING / 2);
              
              return (
                <g key={`pipe-${index}`}>
                  {/* Horizontal line from source */}
                  <line
                    x1={fromX}
                    y1={fromY}
                    x2={midX}
                    y2={fromY}
                    stroke={pipeColor}
                    strokeWidth={PIPE_WIDTH}
                    strokeLinecap="round"
                  />
                  {/* Curved vertical line */}
                  <path
                    d={`M ${midX} ${fromY} Q ${midX} ${controlY} ${midX} ${toY}`}
                    stroke={pipeColor}
                    strokeWidth={PIPE_WIDTH}
                    fill="none"
                    strokeLinecap="round"
                  />
                  {/* Horizontal line to target */}
                  <line
                    x1={midX}
                    y1={toY}
                    x2={toX}
                    y2={toY}
                    stroke={pipeColor}
                    strokeWidth={PIPE_WIDTH}
                    strokeLinecap="round"
                  />
                  {/* Branch indicator */}
                  <circle
                    cx={midX}
                    cy={fromY}
                    r={6}
                    fill={pipeColor}
                  />
                </g>
              );
            }
            
            // Straight pipe for main flow
            return (
              <line
                key={`pipe-${index}`}
                x1={fromX}
                y1={fromY}
                x2={toX}
                y2={toY}
                stroke={pipeColor}
                strokeWidth={PIPE_WIDTH}
                strokeLinecap="round"
                markerEnd="url(#arrowhead)"
              />
            );
          })}
          
          {/* Arrow marker definition */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3, 0 6"
                fill={STATUS_COLORS.default.pipe}
              />
            </marker>
          </defs>
        </svg>
        
        {/* Render nodes */}
        <div className="relative">
          {nodes.map((node) => {
            const colors = STATUS_COLORS[node.status];
            const icon = getEventIcon(node.event, node.status);
            
            return (
              <div
                key={node.id}
                className={`absolute ${colors.node} ${colors.border} border-2 rounded-lg p-4 shadow-lg transition-all hover:scale-105`}
                style={{
                  left: `${node.x}px`,
                  top: `${node.y}px`,
                  width: `${node.width}px`,
                  minHeight: `${node.height}px`
                }}
              >
                <div className="flex items-start gap-3">
                  <div className={`flex-shrink-0 ${colors.text}`}>
                    {icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className={`font-semibold text-sm ${colors.text} truncate`}>
                        {formatEventType(node.event.event_type)}
                      </h4>
                      {node.hasBranch && (
                        <GitBranch className="h-4 w-4 text-slate-300" />
                      )}
                      {node.event.verification_step && (
                        <Shield className="h-4 w-4 text-slate-300" />
                      )}
                    </div>
                    {node.event.timestamp && (
                      <p className="text-xs text-slate-300 opacity-75">
                        {new Date(node.event.timestamp).toLocaleString()}
                      </p>
                    )}
                    {node.event.requires_review && (
                      <div className="mt-2 px-2 py-1 bg-blue-500/20 rounded text-xs text-blue-200">
                        Review Required
                      </div>
                    )}
                    {node.status === 'failure' && node.event.data && (
                      <div className="mt-2 px-2 py-1 bg-red-500/20 rounded text-xs text-red-200">
                        {node.event.data.reason || 'Failed'}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Legend */}
      <div className="mt-6 pt-4 border-t border-slate-700">
        <h4 className="text-sm font-semibold text-slate-300 mb-3">Status Legend</h4>
        <div className="flex flex-wrap gap-4">
          {Object.entries(STATUS_COLORS).map(([status, colors]) => (
            <div key={status} className="flex items-center gap-2">
              <div className={`w-4 h-4 rounded ${colors.node}`} />
              <span className="text-xs text-slate-400 capitalize">{status.replace(/_/g, ' ')}</span>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-4 mt-3">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-slate-400" />
            <span className="text-xs text-slate-400">Branch</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-slate-400" />
            <span className="text-xs text-slate-400">Verification Step</span>
          </div>
        </div>
      </div>
    </div>
  );
}
