import { Card, CardContent, CardHeader } from './ui/card';
import { Button } from './ui/button';
import { 
  Eye, 
  Edit, 
  FileText, 
  Calendar, 
  DollarSign, 
  Building2
} from 'lucide-react';

export interface DemoDeal {
  id: number;
  deal_id: string;
  deal_type: string;
  status: string;
  borrower_name?: string;
  total_commitment?: number;
  currency?: string;
  created_at: string;
  deal_data?: {
    loan_amount?: number;
    interest_rate?: number;
  };
}

interface DemoDealCardProps {
  deal: DemoDeal;
  onView?: (deal: DemoDeal) => void;
  onEdit?: (deal: DemoDeal) => void;
  onViewDocuments?: (deal: DemoDeal) => void;
  className?: string;
}

export function DemoDealCard({ 
  deal, 
  onView, 
  onEdit, 
  onViewDocuments,
  className = '' 
}: DemoDealCardProps) {
  const formatCurrency = (amount: number | undefined, currency: string = 'USD') => {
    if (!amount) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
      submitted: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      under_review: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
      approved: 'bg-green-500/20 text-green-300 border-green-500/30',
      rejected: 'bg-red-500/20 text-red-300 border-red-500/30',
      active: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      closed: 'bg-slate-600/20 text-slate-400 border-slate-600/30',
    };
    return colors[status] || 'bg-slate-500/20 text-slate-300 border-slate-500/30';
  };

  const getDealTypeLabel = (dealType: string) => {
    return dealType
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const amount = deal.total_commitment || deal.deal_data?.loan_amount;
  const currency = deal.currency || 'USD';

  return (
    <Card className={`hover:border-indigo-500/50 transition-colors ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <h3 className="font-mono text-sm font-semibold text-white truncate">
                {deal.deal_id}
              </h3>
              <span className={`text-xs px-2 py-0.5 rounded border ${getStatusColor(deal.status)} flex-shrink-0`}>
                {deal.status.replace('_', ' ').toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-slate-400 capitalize">
              {getDealTypeLabel(deal.deal_type)}
            </p>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="space-y-3">
          {/* Borrower Info */}
          {deal.borrower_name && (
            <div className="flex items-center gap-2 text-sm">
              <Building2 className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span className="text-slate-300 truncate">{deal.borrower_name}</span>
            </div>
          )}

          {/* Amount */}
          {amount && (
            <div className="flex items-center gap-2 text-sm">
              <DollarSign className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span className="text-white font-semibold">
                {formatCurrency(amount, currency)}
              </span>
              {deal.deal_data?.interest_rate && (
                <span className="text-slate-400 text-xs">
                  @ {deal.deal_data.interest_rate}%
                </span>
              )}
            </div>
          )}

          {/* Date */}
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Calendar className="w-4 h-4 flex-shrink-0" />
            <span>{formatDate(deal.created_at)}</span>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2 pt-2 border-t border-slate-700">
            {onView && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onView(deal)}
                className="flex-1 text-xs"
              >
                <Eye className="w-3 h-3 mr-1" />
                View
              </Button>
            )}
            {onViewDocuments && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onViewDocuments(deal)}
                className="flex-1 text-xs"
              >
                <FileText className="w-3 h-3 mr-1" />
                Documents
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
