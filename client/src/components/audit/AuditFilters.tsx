import { useState } from 'react';
import { Calendar, Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
// Simple select component - using native select for now

export interface AuditFilters {
  startDate: string | null;
  endDate: string | null;
  action: string | null;
  targetType: string | null;
  userId: number | null;
}

interface AuditFiltersProps {
  filters: AuditFilters;
  onFilterChange: (filters: Partial<AuditFilters>) => void;
  availableFilters?: {
    actions?: string[];
    targetTypes?: string[];
    users?: Array<{ id: number; name: string; email: string }>;
  };
}

export function AuditFilters({
  filters,
  onFilterChange,
  availableFilters
}: AuditFiltersProps) {
  const [showFilters, setShowFilters] = useState(false);

  const handleClear = () => {
    onFilterChange({
      startDate: null,
      endDate: null,
      action: null,
      targetType: null,
      userId: null,
    });
  };

  const hasActiveFilters = 
    filters.startDate || 
    filters.endDate || 
    filters.action || 
    filters.targetType || 
    filters.userId;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-300">Filters</span>
          {hasActiveFilters && (
            <span className="px-2 py-0.5 text-xs bg-emerald-600 text-white rounded-full">
              Active
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClear}
              className="text-xs"
            >
              <X className="h-3 w-3 mr-1" />
              Clear
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            {showFilters ? 'Hide' : 'Show'} Filters
          </Button>
        </div>
      </div>

      {showFilters && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
          {/* Date Range */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400 flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Start Date
            </label>
            <Input
              type="datetime-local"
              value={filters.startDate || ''}
              onChange={(e) => onFilterChange({ startDate: e.target.value || null })}
              className="bg-slate-900 border-slate-700 text-slate-100"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400 flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              End Date
            </label>
            <Input
              type="datetime-local"
              value={filters.endDate || ''}
              onChange={(e) => onFilterChange({ endDate: e.target.value || null })}
              className="bg-slate-900 border-slate-700 text-slate-100"
            />
          </div>

          {/* Action Filter */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400">Action</label>
            <select
              value={filters.action || ''}
              onChange={(e) => onFilterChange({ action: e.target.value || null })}
              className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 py-1 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="">All actions</option>
              {availableFilters?.actions?.map((action) => (
                <option key={action} value={action}>
                  {action.replace(/_/g, ' ').toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Target Type Filter */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400">Target Type</label>
            <select
              value={filters.targetType || ''}
              onChange={(e) => onFilterChange({ targetType: e.target.value || null })}
              className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 py-1 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="">All types</option>
              {availableFilters?.targetTypes?.map((type) => (
                <option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* User Filter */}
          {availableFilters?.users && availableFilters.users.length > 0 && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-400">User</label>
              <select
                value={filters.userId?.toString() || ''}
                onChange={(e) => 
                  onFilterChange({ userId: e.target.value ? parseInt(e.target.value) : null })
                }
                className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 py-1 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value="">All users</option>
                {availableFilters.users.map((user) => (
                  <option key={user.id} value={user.id.toString()}>
                    {user.name} ({user.email})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
