import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowLeft, Download, FileText, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
}

interface ReportGenerationRequest {
  report_type: 'overview' | 'deal' | 'loan' | 'filing' | 'custom';
  date_range: {
    start: string | null;
    end: string | null;
  };
  entity_selection?: {
    type: 'all' | 'deal' | 'loan' | 'filing';
    ids?: number[];
  };
  template: 'standard' | 'comprehensive' | 'executive';
  include_sections?: {
    executive_summary?: boolean;
    compliance_analysis?: boolean;
    recommendations?: boolean;
    detailed_trail?: boolean;
  };
}

export function AuditReportGenerator() {
  const navigate = useNavigate();
  const [generating, setGenerating] = useState(false);
  const [reportId, setReportId] = useState<string | null>(null);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [request, setRequest] = useState<ReportGenerationRequest>({
    report_type: 'overview',
    date_range: {
      start: null,
      end: null,
    },
    template: 'standard',
    include_sections: {
      executive_summary: true,
      compliance_analysis: true,
      recommendations: true,
      detailed_trail: true,
    },
  });

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      setReport(null);
      
      const response = await fetchWithAuth('/api/auditor/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate report');
      }
      
      const data = await response.json();
      setReportId(data.report_id);
      setReport(data.report);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (format: 'pdf' | 'word' | 'excel') => {
    if (!reportId) return;
    
    try {
      // TODO: Implement download endpoint
      // For now, show a message
      alert(`Download ${format} functionality will be implemented soon`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/auditor')}
            className="text-slate-400 hover:text-slate-100"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-2">
              <FileText className="h-8 w-8" />
              Audit Report Generator
            </h1>
            <p className="text-slate-400 mt-1">Generate comprehensive audit reports with LLM-powered analysis</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4 text-red-400">
          Error: {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Configuration */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100">Report Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Report Type */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Report Type</label>
              <select
                value={request.report_type}
                onChange={(e) => setRequest({ ...request, report_type: e.target.value as any })}
                className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 py-1 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value="overview">Overview</option>
                <option value="deal">Deal</option>
                <option value="loan">Loan</option>
                <option value="filing">Filing</option>
                <option value="custom">Custom</option>
              </select>
            </div>

            {/* Date Range */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Start Date</label>
              <Input
                type="datetime-local"
                value={request.date_range.start || ''}
                onChange={(e) => setRequest({
                  ...request,
                  date_range: { ...request.date_range, start: e.target.value || null }
                })}
                className="bg-slate-900 border-slate-700 text-slate-100"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">End Date</label>
              <Input
                type="datetime-local"
                value={request.date_range.end || ''}
                onChange={(e) => setRequest({
                  ...request,
                  date_range: { ...request.date_range, end: e.target.value || null }
                })}
                className="bg-slate-900 border-slate-700 text-slate-100"
              />
            </div>

            {/* Template */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Template</label>
              <select
                value={request.template}
                onChange={(e) => setRequest({ ...request, template: e.target.value as any })}
                className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-3 py-1 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value="standard">Standard</option>
                <option value="comprehensive">Comprehensive</option>
                <option value="executive">Executive</option>
              </select>
            </div>

            {/* Sections */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-300">Include Sections</label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={request.include_sections?.executive_summary ?? true}
                    onChange={(e) => setRequest({
                      ...request,
                      include_sections: {
                        ...request.include_sections,
                        executive_summary: e.target.checked
                      }
                    })}
                    className="rounded border-slate-700"
                  />
                  Executive Summary
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={request.include_sections?.compliance_analysis ?? true}
                    onChange={(e) => setRequest({
                      ...request,
                      include_sections: {
                        ...request.include_sections,
                        compliance_analysis: e.target.checked
                      }
                    })}
                    className="rounded border-slate-700"
                  />
                  Compliance Analysis
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={request.include_sections?.recommendations ?? true}
                    onChange={(e) => setRequest({
                      ...request,
                      include_sections: {
                        ...request.include_sections,
                        recommendations: e.target.checked
                      }
                    })}
                    className="rounded border-slate-700"
                  />
                  Recommendations
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={request.include_sections?.detailed_trail ?? true}
                    onChange={(e) => setRequest({
                      ...request,
                      include_sections: {
                        ...request.include_sections,
                        detailed_trail: e.target.checked
                      }
                    })}
                    className="rounded border-slate-700"
                  />
                  Detailed Trail
                </label>
              </div>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={generating}
              className="w-full"
            >
              {generating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4 mr-2" />
                  Generate Report
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Report Preview */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100">Report Preview</CardTitle>
          </CardHeader>
          <CardContent>
            {generating ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-12 w-12 animate-spin text-emerald-500 mb-4" />
                <p className="text-slate-400">Generating report with LLM analysis...</p>
                <p className="text-sm text-slate-500 mt-2">This may take up to 2 minutes</p>
              </div>
            ) : report ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-green-400">
                  <CheckCircle className="h-5 w-5" />
                  <span className="font-medium">Report Generated Successfully</span>
                </div>
                
                <div className="space-y-2">
                  <p className="text-sm text-slate-400">Report ID: {report.report_id}</p>
                  <p className="text-sm text-slate-400">Type: {report.report_type}</p>
                  <p className="text-sm text-slate-400">Template: {report.template}</p>
                  <p className="text-sm text-slate-400">
                    Generated: {new Date(report.generated_at).toLocaleString()}
                  </p>
                </div>

                {/* Executive Summary Preview */}
                {report.sections?.executive_summary && (
                  <div className="p-4 bg-slate-900/50 rounded-lg">
                    <h3 className="font-medium text-slate-100 mb-2">Executive Summary</h3>
                    <p className="text-sm text-slate-300">
                      {report.sections.executive_summary.overview || 'No summary available'}
                    </p>
                  </div>
                )}

                {/* Download Options */}
                <div className="flex gap-2 pt-4 border-t border-slate-700">
                  <Button
                    onClick={() => handleDownload('pdf')}
                    variant="outline"
                    size="sm"
                    className="flex-1"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    PDF
                  </Button>
                  <Button
                    onClick={() => handleDownload('word')}
                    variant="outline"
                    size="sm"
                    className="flex-1"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Word
                  </Button>
                  <Button
                    onClick={() => handleDownload('excel')}
                    variant="outline"
                    size="sm"
                    className="flex-1"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Excel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                <AlertCircle className="h-12 w-12 mb-4 opacity-50" />
                <p>No report generated yet</p>
                <p className="text-sm mt-2">Configure and generate a report to see preview</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
