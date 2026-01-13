import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  FileText,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  ExternalLink,
  Filter,
  RefreshCw,
  Download,
  Loader2,
  Building2,
  Globe
} from 'lucide-react';

interface FilingRequirement {
  authority: string;
  jurisdiction: string;
  agreement_type: string;
  filing_system: string;
  deadline: string;
  required_fields: string[];
  api_available: boolean;
  api_endpoint?: string;
  penalty?: string;
  language_requirement?: string;
  form_type?: string;
  priority: string;
}

interface FilingStatus {
  id: number;
  document_id: number;
  deal_id?: number;
  agreement_type: string;
  jurisdiction: string;
  filing_authority: string;
  filing_system: string;
  filing_reference?: string;
  filing_status: string;
  deadline?: string;
  filed_at?: string;
  filing_url?: string;
  manual_submission_url?: string;
}

interface FilingRequirementsPanelProps {
  documentId?: number;
  dealId?: number;
  agreementType?: string;
}

export function FilingRequirementsPanel({
  documentId,
  dealId,
  agreementType = 'facility_agreement'
}: FilingRequirementsPanelProps) {
  const [requirements, setRequirements] = useState<FilingRequirement[]>([]);
  const [filings, setFilings] = useState<FilingStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterJurisdiction, setFilterJurisdiction] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [preparingFiling, setPreparingFiling] = useState<number | null>(null);
  const [submittingFiling, setSubmittingFiling] = useState<number | null>(null);

  useEffect(() => {
    if (documentId) {
      fetchRequirements();
      fetchFilings();
    }
  }, [documentId, dealId, agreementType]);

  const fetchRequirements = async () => {
    if (!documentId) return;

    setLoading(true);
    setError(null);
    try {
      const url = `/api/documents/${documentId}/filing/requirements?deal_id=${dealId || ''}&agreement_type=${agreementType}&use_ai_evaluation=true`;
      const response = await fetchWithAuth(url);
      if (!response.ok) {
        throw new Error('Failed to fetch filing requirements');
      }
      const data = await response.json();
      setRequirements(data.required_filings || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load filing requirements');
    } finally {
      setLoading(false);
    }
  };

  const fetchFilings = async () => {
    if (!documentId) return;

    try {
      // Fetch filings for this document
      // Note: This would need a new endpoint or we can get from document details
      // For now, we'll fetch deadline alerts which include filing info
      const response = await fetchWithAuth(
        `/api/filings/deadline-alerts?document_id=${documentId}&days_ahead=365`
      );
      if (response.ok) {
        const data = await response.json();
        // Convert alerts to filing status format
        // In production, you'd have a dedicated endpoint for filings
      }
    } catch (err) {
      // Silently fail for filings - not critical
      console.error('Failed to fetch filings:', err);
    }
  };

  const handlePrepareFiling = async (requirement: FilingRequirement) => {
    if (!documentId) return;

    setPreparingFiling(requirements.indexOf(requirement));
    try {
      // First, create a filing record
      const prepareResponse = await fetchWithAuth(
        `/api/filings/prepare`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            document_id: documentId,
            filing_requirement: requirement
          })
        }
      );

      if (!prepareResponse.ok) {
        throw new Error('Failed to prepare filing');
      }

      const data = await prepareResponse.json();
      setFilings([...filings, data.filing as FilingStatus]);
      
      // Refresh requirements
      await fetchRequirements();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to prepare filing');
    } finally {
      setPreparingFiling(null);
    }
  };

  const handleSubmitAutomatic = async (filingId: number) => {
    setSubmittingFiling(filingId);
    try {
      const response = await fetchWithAuth(
        `/api/filings/${filingId}/submit-automatic`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error('Failed to submit filing');
      }

      await fetchFilings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit filing');
    } finally {
      setSubmittingFiling(null);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'submitted':
      case 'accepted':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'rejected':
        return 'bg-red-500/20 text-red-400 border-red-500/50';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  const getDaysUntilDeadline = (deadline: string) => {
    const deadlineDate = new Date(deadline);
    const today = new Date();
    const diffTime = deadlineDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const filteredRequirements = requirements.filter((req) => {
    if (filterJurisdiction !== 'all' && req.jurisdiction !== filterJurisdiction) {
      return false;
    }
    // Filter by status would require checking if filing exists
    return true;
  });

  const jurisdictions = Array.from(new Set(requirements.map((r) => r.jurisdiction)));

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Filters */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Filing Requirements
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchRequirements}
              className="text-slate-400 hover:text-slate-100"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-400" />
              <select
                value={filterJurisdiction}
                onChange={(e) => setFilterJurisdiction(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="all">All Jurisdictions</option>
                {jurisdictions.map((j) => (
                  <option key={j} value={j}>
                    {j}
                  </option>
                ))}
              </select>
            </div>
            <Badge variant="outline" className="text-slate-400">
              {filteredRequirements.length} requirement{filteredRequirements.length !== 1 ? 's' : ''}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Requirements List */}
      {filteredRequirements.length === 0 ? (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6 text-center text-slate-400">
            No filing requirements found for this document
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredRequirements.map((requirement, index) => {
            const daysUntil = getDaysUntilDeadline(requirement.deadline);
            const isUrgent = daysUntil <= 7;
            const existingFiling = filings.find(
              (f) =>
                f.filing_authority === requirement.authority &&
                f.jurisdiction === requirement.jurisdiction
            );

            return (
              <Card
                key={index}
                className={`bg-slate-800 border-slate-700 ${
                  isUrgent ? 'border-yellow-500/50' : ''
                }`}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Building2 className="h-5 w-5 text-slate-400" />
                        <CardTitle className="text-slate-100 text-lg">
                          {requirement.authority}
                        </CardTitle>
                        <Badge className={getPriorityColor(requirement.priority)}>
                          {requirement.priority}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
                        <div className="flex items-center gap-1">
                          <Globe className="h-4 w-4" />
                          {requirement.jurisdiction}
                        </div>
                        {requirement.form_type && (
                          <span>Form: {requirement.form_type}</span>
                        )}
                        {requirement.filing_system === 'companies_house_api' && (
                          <Badge variant="outline" className="text-emerald-400">
                            Automated
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {/* Deadline */}
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-slate-400" />
                      <span className="text-slate-300">
                        Deadline: {new Date(requirement.deadline).toLocaleDateString()}
                      </span>
                      {daysUntil >= 0 && (
                        <Badge
                          variant="outline"
                          className={
                            daysUntil <= 1
                              ? 'text-red-400 border-red-500/50'
                              : daysUntil <= 7
                              ? 'text-yellow-400 border-yellow-500/50'
                              : 'text-slate-400'
                          }
                        >
                          {daysUntil} day{daysUntil !== 1 ? 's' : ''} remaining
                        </Badge>
                      )}
                    </div>

                    {/* Penalty */}
                    {requirement.penalty && (
                      <div className="flex items-start gap-2">
                        <AlertCircle className="h-4 w-4 text-orange-400 mt-0.5" />
                        <span className="text-sm text-slate-400">
                          Penalty: <span className="text-orange-400">{requirement.penalty}</span>
                        </span>
                      </div>
                    )}

                    {/* Required Fields */}
                    {requirement.required_fields.length > 0 && (
                      <div>
                        <p className="text-sm text-slate-400 mb-2">Required Fields:</p>
                        <div className="flex flex-wrap gap-2">
                          {requirement.required_fields.map((field, idx) => (
                            <Badge key={idx} variant="outline" className="text-slate-400">
                              {field}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-2 border-t border-slate-700">
                      {existingFiling ? (
                        <>
                          <Badge className={getStatusColor(existingFiling.filing_status)}>
                            {existingFiling.filing_status}
                          </Badge>
                          {existingFiling.filing_url && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => window.open(existingFiling.filing_url, '_blank')}
                              className="text-slate-400 hover:text-slate-100"
                            >
                              <ExternalLink className="h-4 w-4 mr-2" />
                              View Filing
                            </Button>
                          )}
                        </>
                      ) : (
                        <>
                          {requirement.filing_system === 'companies_house_api' ? (
                            <Button
                              size="sm"
                              onClick={() => {
                                // Handle automatic filing
                                const filingId = filings.find(
                                  (f) =>
                                    f.filing_authority === requirement.authority &&
                                    f.jurisdiction === requirement.jurisdiction
                                )?.id;
                                if (filingId) {
                                  handleSubmitAutomatic(filingId);
                                }
                              }}
                              disabled={submittingFiling !== null}
                              className="bg-emerald-600 hover:bg-emerald-700 text-white"
                            >
                              {submittingFiling !== null ? (
                                <>
                                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                  Submitting...
                                </>
                              ) : (
                                <>
                                  <CheckCircle className="h-4 w-4 mr-2" />
                                  Submit Automatically
                                </>
                              )}
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() => handlePrepareFiling(requirement)}
                              disabled={preparingFiling === index}
                              className="bg-blue-600 hover:bg-blue-700 text-white"
                            >
                              {preparingFiling === index ? (
                                <>
                                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                  Preparing...
                                </>
                              ) : (
                                <>
                                  <FileText className="h-4 w-4 mr-2" />
                                  Prepare Manual Filing
                                </>
                              )}
                            </Button>
                          )}
                          {requirement.language_requirement && (
                            <Badge variant="outline" className="text-slate-400">
                              Language: {requirement.language_requirement}
                            </Badge>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
