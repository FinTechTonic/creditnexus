/**
 * CDM Preview Card Component
 * 
 * Displays a single CDM document as a card in a grid layout.
 * Shows key fields and allows selection.
 */

import { FileText, Building2, Calendar, DollarSign, Scale, CheckCircle2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
// CreditAgreementData type not used directly in this component

interface CdmPreviewCardProps {
  documentId: number;
  title: string;
  borrowerName?: string | null;
  borrowerLei?: string | null;
  governingLaw?: string | null;
  totalCommitment?: number | null;
  currency?: string | null;
  agreementDate?: string | null;
  completenessScore?: number;
  isSelected?: boolean;
  onSelect: (documentId: number) => void;
  onPreview?: (documentId: number) => void;
}

export function CdmPreviewCard({
  documentId,
  title,
  borrowerName,
  // borrowerLei, // Unused - kept in props for API compatibility
  governingLaw,
  totalCommitment,
  currency,
  agreementDate,
  completenessScore,
  isSelected = false,
  onSelect,
  onPreview,
}: CdmPreviewCardProps) {
  const formatCurrency = (amount: number | null, curr: string | null | undefined) => {
    if (!amount) return 'N/A';
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: curr || 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
    return formatted;
  };

  const formatDate = (date: string | null) => {
    if (!date) return 'N/A';
    try {
      return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return date;
    }
  };

  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-lg ${
        isSelected
          ? 'ring-2 ring-emerald-500 border-emerald-500 bg-slate-800'
          : 'border-slate-700 hover:border-slate-600 bg-slate-800/50'
      }`}
      onClick={() => onSelect(documentId)}
    >
      <CardContent className="p-4">
        {/* Header with selection indicator */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <h4 className="font-medium text-sm text-slate-100 truncate">{title}</h4>
            </div>
            {isSelected && (
              <div className="flex items-center gap-1 text-emerald-400 text-xs mt-1">
                <CheckCircle2 className="w-3 h-3" />
                <span>Selected</span>
              </div>
            )}
          </div>
        </div>

        {/* Completeness Score */}
        {completenessScore !== undefined && (
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-400">Completeness</span>
              <span className={`font-medium ${
                completenessScore >= 80 ? 'text-emerald-400' :
                completenessScore >= 50 ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                {completenessScore}%
              </span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full ${
                  completenessScore >= 80 ? 'bg-emerald-500' :
                  completenessScore >= 50 ? 'bg-yellow-500' :
                  'bg-red-500'
                }`}
                style={{ width: `${completenessScore}%` }}
              />
            </div>
          </div>
        )}

        {/* Key Fields */}
        <div className="space-y-2 text-xs">
          {borrowerName && (
            <div className="flex items-center gap-2 text-slate-300">
              <Building2 className="w-3 h-3 text-slate-400 flex-shrink-0" />
              <span className="truncate">{borrowerName}</span>
            </div>
          )}
          
          {totalCommitment && (
            <div className="flex items-center gap-2 text-slate-300">
              <DollarSign className="w-3 h-3 text-slate-400 flex-shrink-0" />
              <span className="truncate">
                {formatCurrency(totalCommitment, currency)}
              </span>
            </div>
          )}
          
          {agreementDate && (
            <div className="flex items-center gap-2 text-slate-300">
              <Calendar className="w-3 h-3 text-slate-400 flex-shrink-0" />
              <span className="truncate">{formatDate(agreementDate)}</span>
            </div>
          )}
          
          {governingLaw && (
            <div className="flex items-center gap-2 text-slate-300">
              <Scale className="w-3 h-3 text-slate-400 flex-shrink-0" />
              <span className="truncate">{governingLaw}</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <Button
            size="sm"
            variant={isSelected ? "default" : "outline"}
            className={`flex-1 text-xs h-7 ${
              isSelected
                ? 'bg-emerald-600 text-white hover:bg-emerald-500'
                : 'bg-slate-700 text-slate-200 hover:bg-slate-600 border-slate-600'
            }`}
            onClick={(e) => {
              e.stopPropagation();
              onSelect(documentId);
            }}
          >
            {isSelected ? 'Selected' : 'Select'}
          </Button>
          {onPreview && (
            <Button
              size="sm"
              variant="ghost"
              className="text-xs h-7 px-2 text-slate-300 hover:text-slate-100 hover:bg-slate-700"
              onClick={(e) => {
                e.stopPropagation();
                onPreview(documentId);
              }}
            >
              View
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
