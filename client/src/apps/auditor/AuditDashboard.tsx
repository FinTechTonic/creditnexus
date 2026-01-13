import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { AuditTimeline } from '@/components/audit/AuditTimeline';
import type { AuditEvent } from '@/components/audit/AuditTimeline';
import { AuditFilters, AuditFilters as AuditFiltersType } from '@/components/audit/AuditFilters';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, RefreshCw, TrendingUp, Users, FileText, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface DashboardStatistics {
  overview: {
    total_logs: number;
    unique_users: number;
    actions: Record<string, number>;
    target_types: Record<string, number>;
  };
  timeline: Array<{
    date: string;
    count: number;
  }>;
  top_users: Array<{
    user_id: number;
    user_name: string;
    user_email: string;
    count: number;
  }>;
  top_actions: Array<{
    action: string;
    count: number;
  }>;
  policy_decisions: {
    total_processed: number;
    decisions: {
      ALLOW: number;
      BLOCK: number;
      FLAG: number;
    };
  };
  recent_events: AuditEvent[];
}

export function AuditDashboard() {
  const navigate = useNavigate();
  const [statistics, setStatistics] = useState<DashboardStatistics | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditEvent[]>([]);
  const [filters, setFilters] = useState<AuditFiltersType>({
    startDate: null,
    endDate: null,
    action: null,
    targetType: null,
    userId: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // Fetch dashboard statistics
  useEffect(() => {
    const fetchStatistics = async () => {
      try {
        setLoading(true);
        setError(null);
        const params = new URLSearchParams();
        if (filters.startDate) params.append('start_date', filters.startDate);
        if (filters.endDate) params.append('end_date', filters.endDate);
        
        const response = await fetchWithAuth(
          `/api/auditor/dashboard?${params.toString()}`
        );
        if (!response.ok) {
          throw new Error('Failed to load dashboard statistics');
        }
        const data = await response.json();
        setStatistics(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load statistics');
      } finally {
        setLoading(false);
      }
    };
    
    fetchStatistics();
  }, [filters.startDate, filters.endDate]);
  
  // Fetch audit logs
  useEffect(() => {
    const fetchAuditLogs = async () => {
      try {
        const params = new URLSearchParams();
        if (filters.startDate) params.append('start_date', filters.startDate);
        if (filters.endDate) params.append('end_date', filters.endDate);
        if (filters.action) params.append('action', filters.action);
        if (filters.targetType) params.append('target_type', filters.targetType);
        if (filters.userId) params.append('user_id', filters.userId.toString());
        params.append('limit', '50');
        
        const response = await fetchWithAuth(
          `/api/auditor/logs?${params.toString()}`
        );
        if (!response.ok) {
          throw new Error('Failed to load audit logs');
        }
        const data = await response.json();
        setAuditLogs(data.logs || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load audit logs');
      }
    };
    
    fetchAuditLogs();
  }, [filters]);
  
  const handleFilterChange = (newFilters: Partial<AuditFiltersType>) => {
    setFilters({ ...filters, ...newFilters });
  };
  
  const handleExport = async (format: 'csv' | 'excel' | 'pdf') => {
    try {
      setExporting(true);
      const params = new URLSearchParams();
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.action) params.append('action', filters.action);
      if (filters.targetType) params.append('target_type', filters.targetType);
      if (filters.userId) params.append('user_id', filters.userId.toString());
      params.append('format', format);
      
      const response = await fetchWithAuth(
        `/api/auditor/export?${params.toString()}`
      );
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const extension = format === 'excel' ? 'xlsx' : format;
      a.download = `audit_export_${new Date().toISOString().split('T')[0]}.${extension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };
  
  const handleRefresh = () => {
    setFilters({ ...filters }); // Trigger re-fetch
  };

  const handleEventClick = (event: AuditEvent) => {
    navigate(`/auditor/logs/${event.id}`);
  };

  if (loading && !statistics) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    );
  }
  
  if (error && !statistics) {
    return (
      <div className="p-6">
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4 text-red-400">
          Error: {error}
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Audit Dashboard</h1>
          <p className="text-slate-400 mt-1">Comprehensive audit trail and compliance monitoring</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button 
            onClick={() => handleExport('csv')} 
            variant="outline" 
            size="sm"
            disabled={exporting}
          >
            <Download className="w-4 h-4 mr-2" />
            CSV
          </Button>
          <Button 
            onClick={() => handleExport('excel')} 
            variant="outline" 
            size="sm"
            disabled={exporting}
          >
            <Download className="w-4 h-4 mr-2" />
            Excel
          </Button>
          <Button 
            onClick={() => handleExport('pdf')} 
            variant="outline" 
            size="sm"
            disabled={exporting}
          >
            <Download className="w-4 h-4 mr-2" />
            PDF
          </Button>
        </div>
      </div>
      
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Total Audit Logs</CardTitle>
            <FileText className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-100">
              {statistics?.overview?.total_logs?.toLocaleString() || 0}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Unique Users</CardTitle>
            <Users className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-100">
              {statistics?.overview?.unique_users || 0}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Policy Decisions</CardTitle>
            <Shield className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-100">
              {statistics?.policy_decisions?.total_processed || 0}
            </div>
            <div className="flex gap-2 mt-2 text-xs">
              <span className="text-green-400">
                ALLOW: {statistics?.policy_decisions?.decisions?.ALLOW || 0}
              </span>
              <span className="text-red-400">
                BLOCK: {statistics?.policy_decisions?.decisions?.BLOCK || 0}
              </span>
              <span className="text-yellow-400">
                FLAG: {statistics?.policy_decisions?.decisions?.FLAG || 0}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Activity Trend</CardTitle>
            <TrendingUp className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-100">
              {statistics?.timeline?.length ? 
                statistics.timeline.reduce((sum, day) => sum + day.count, 0) : 0}
            </div>
            <p className="text-xs text-slate-400 mt-1">Last 30 days</p>
          </CardContent>
        </Card>
      </div>
      
      {/* Filters */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <AuditFilters
            filters={filters}
            onFilterChange={handleFilterChange}
            availableFilters={{
              actions: statistics?.top_actions?.map(a => a.action),
              targetTypes: Object.keys(statistics?.overview?.target_types || {}),
              users: statistics?.top_users?.map(u => ({
                id: u.user_id,
                name: u.user_name,
                email: u.user_email
              }))
            }}
          />
        </CardContent>
      </Card>
      
      {/* Activity Timeline */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Activity Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {statistics?.timeline && statistics.timeline.length > 0 ? (
            <div className="space-y-2">
              {statistics.timeline.slice(0, 7).map((day, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-slate-900/50 rounded">
                  <span className="text-sm text-slate-300">{day.date}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-32 bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-emerald-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min((day.count / (statistics.timeline[0]?.count || 1)) * 100, 100)}%`
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium text-slate-100 w-12 text-right">
                      {day.count}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-400 text-center py-8">No timeline data available</p>
          )}
        </CardContent>
      </Card>
      
      {/* Recent Events */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Recent Audit Events</CardTitle>
        </CardHeader>
        <CardContent>
          <AuditTimeline
            events={auditLogs}
            onEventClick={handleEventClick}
            height={400}
          />
        </CardContent>
      </Card>

      {/* Top Users and Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100">Top Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {statistics?.top_users?.slice(0, 5).map((user, index) => (
                <div key={user.user_id} className="flex items-center justify-between p-2 bg-slate-900/50 rounded">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-400 w-6">#{index + 1}</span>
                    <div>
                      <p className="text-sm text-slate-100">{user.user_name}</p>
                      <p className="text-xs text-slate-400">{user.user_email}</p>
                    </div>
                  </div>
                  <span className="text-sm font-medium text-emerald-400">{user.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100">Top Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {statistics?.top_actions?.slice(0, 5).map((action, index) => (
                <div key={action.action} className="flex items-center justify-between p-2 bg-slate-900/50 rounded">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-400 w-6">#{index + 1}</span>
                    <span className="text-sm text-slate-100 capitalize">
                      {action.action.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="text-sm font-medium text-emerald-400">{action.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
