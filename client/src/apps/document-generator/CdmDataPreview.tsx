/**
 * CDM Data Preview Component
 * 
 * Displays CDM data in a readable format with parties, facilities, dates, etc.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Users,
  Briefcase,
  Calendar,
  DollarSign,
  Scale,
  Building2,
  FileText,
  X,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import type { CreditAgreementData } from '@/context/FDC3Context';

interface CdmDataPreviewProps {
  cdmData: CreditAgreementData;
  documentTitle?: string;
  onClose?: () => void;
  className?: string;
}

export function CdmDataPreview({
  cdmData,
  documentTitle,
  onClose,
  className = '',
}: CdmDataPreviewProps) {
  const formatCurrency = (amount: number | null | undefined, currency: string | null | undefined): string => {
    if (!amount) return 'N/A';
    const currencySymbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : currency || '';
    return `${currencySymbol}${amount.toLocaleString()}`;
  };

  const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  const totalCommitment = cdmData.facilities?.reduce((sum, facility) => {
    const amount = facility.commitment_amount?.amount || 0;
    return sum + (typeof amount === 'number' ? amount : parseFloat(String(amount)) || 0);
  }, 0) || 0;

  const currency = cdmData.facilities?.[0]?.commitment_amount?.currency || 'USD';

  return (
    <Card className={`border-slate-700 bg-slate-800/50 ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-emerald-400" />
            <CardTitle className="text-lg text-slate-100">
              CDM Data Preview
            </CardTitle>
          </div>
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="text-slate-400 hover:text-slate-100"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
        {documentTitle && (
          <p className="text-sm text-slate-400 mt-1">{documentTitle}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-4 w-4 text-emerald-400" />
              <span className="text-sm font-medium text-slate-300">Parties</span>
            </div>
            <p className="text-2xl font-bold text-slate-100">
              {cdmData.parties?.length || 0}
            </p>
          </div>
          <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <Briefcase className="h-4 w-4 text-emerald-400" />
              <span className="text-sm font-medium text-slate-300">Facilities</span>
            </div>
            <p className="text-2xl font-bold text-slate-100">
              {cdmData.facilities?.length || 0}
            </p>
          </div>
          <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-emerald-400" />
              <span className="text-sm font-medium text-slate-300">Total Commitment</span>
            </div>
            <p className="text-2xl font-bold text-slate-100">
              {formatCurrency(totalCommitment, currency)}
            </p>
          </div>
        </div>

        {/* Key Information */}
        <div className="space-y-4">
          <h3 className="text-md font-semibold text-slate-100 flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Key Information
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {cdmData.deal_id && (
              <div className="flex items-center gap-3 p-3 bg-slate-900/50 rounded-lg border border-slate-700">
                <FileText className="h-4 w-4 text-slate-400" />
                <div>
                  <p className="text-xs text-slate-500">Deal ID</p>
                  <p className="text-sm font-medium text-slate-200">{cdmData.deal_id}</p>
                </div>
              </div>
            )}
            {cdmData.loan_identification_number && (
              <div className="flex items-center gap-3 p-3 bg-slate-900/50 rounded-lg border border-slate-700">
                <FileText className="h-4 w-4 text-slate-400" />
                <div>
                  <p className="text-xs text-slate-500">Loan ID</p>
                  <p className="text-sm font-medium text-slate-200">{cdmData.loan_identification_number}</p>
                </div>
              </div>
            )}
            {cdmData.agreement_date && (
              <div className="flex items-center gap-3 p-3 bg-slate-900/50 rounded-lg border border-slate-700">
                <Calendar className="h-4 w-4 text-slate-400" />
                <div>
                  <p className="text-xs text-slate-500">Agreement Date</p>
                  <p className="text-sm font-medium text-slate-200">{formatDate(cdmData.agreement_date)}</p>
                </div>
              </div>
            )}
            {cdmData.governing_law && (
              <div className="flex items-center gap-3 p-3 bg-slate-900/50 rounded-lg border border-slate-700">
                <Scale className="h-4 w-4 text-slate-400" />
                <div>
                  <p className="text-xs text-slate-500">Governing Law</p>
                  <p className="text-sm font-medium text-slate-200">{cdmData.governing_law}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Parties */}
        {cdmData.parties && cdmData.parties.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-md font-semibold text-slate-100 flex items-center gap-2">
              <Users className="h-4 w-4" />
              Parties ({cdmData.parties.length})
            </h3>
            <div className="space-y-2">
              {cdmData.parties.map((party, idx) => (
                <div
                  key={party.id || idx}
                  className="p-4 bg-slate-900/50 rounded-lg border border-slate-700"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Building2 className="h-4 w-4 text-emerald-400" />
                        <p className="font-medium text-slate-100">{party.name || 'Unnamed Party'}</p>
                        {party.role && (
                          <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded">
                            {party.role}
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                        {party.lei && (
                          <div>
                            <p className="text-xs text-slate-500">LEI</p>
                            <p className="text-slate-200">{party.lei}</p>
                          </div>
                        )}
                        {(party as any).address && (
                          <div>
                            <p className="text-xs text-slate-500">Address</p>
                            <p className="text-slate-200">{(party as any).address}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Facilities */}
        {cdmData.facilities && cdmData.facilities.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-md font-semibold text-slate-100 flex items-center gap-2">
              <Briefcase className="h-4 w-4" />
              Facilities ({cdmData.facilities.length})
            </h3>
            <div className="space-y-2">
              {cdmData.facilities.map((facility, idx) => (
                <div
                  key={facility.facility_name || idx}
                  className="p-4 bg-slate-900/50 rounded-lg border border-slate-700"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <p className="font-medium text-slate-100">
                        {facility.facility_name || `Facility ${idx + 1}`}
                      </p>
                      {(facility as any).facility_type && (
                        <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded">
                          {(facility as any).facility_type}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm mt-3">
                    {facility.commitment_amount && (
                      <div>
                        <p className="text-xs text-slate-500">Commitment</p>
                        <p className="text-slate-200 font-medium">
                          {formatCurrency(
                            facility.commitment_amount.amount,
                            facility.commitment_amount.currency
                          )}
                        </p>
                      </div>
                    )}
                    {facility.interest_terms?.rate_option && (
                      <div>
                        <p className="text-xs text-slate-500">Interest Rate</p>
                        <p className="text-slate-200 font-medium">
                          {facility.interest_terms.rate_option.benchmark} + {facility.interest_terms.rate_option.spread_bps / 100}%
                        </p>
                      </div>
                    )}
                    {facility.maturity_date && (
                      <div>
                        <p className="text-xs text-slate-500">Maturity Date</p>
                        <p className="text-slate-200 font-medium">{formatDate(facility.maturity_date)}</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Data Completeness Indicator */}
        <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-300">Data Completeness</span>
            <div className="flex items-center gap-2">
              {cdmData.parties && cdmData.parties.length > 0 && cdmData.facilities && cdmData.facilities.length > 0 ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-yellow-400" />
              )}
            </div>
          </div>
          <div className="space-y-2 text-xs text-slate-400">
            {cdmData.parties && cdmData.parties.length > 0 ? (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                <span>Parties data available</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-3 w-3 text-yellow-400" />
                <span>No parties data</span>
              </div>
            )}
            {cdmData.facilities && cdmData.facilities.length > 0 ? (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                <span>Facilities data available</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-3 w-3 text-yellow-400" />
                <span>No facilities data</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
