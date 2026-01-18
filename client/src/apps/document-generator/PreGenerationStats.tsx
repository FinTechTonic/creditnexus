/**
 * Pre-Generation Statistics Component
 * 
 * Displays field completeness, clause cache predictions, and template compatibility
 * before document generation to help users understand readiness and make decisions.
 */

import { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  AlertCircle, 
  Info, 
  TrendingUp, 
  Database, 
  Sparkles,
  Loader2,
  XCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { fetchWithAuth } from '@/context/AuthContext';
import type { CreditAgreementData } from '@/context/FDC3Context';

interface PreGenerationStatsProps {
  templateId: number | null;
  documentId: number | null;
  cdmData?: CreditAgreementData;
  fieldOverrides?: Record<string, any>;
  onClose?: () => void;
  onMissingFieldsDetected?: (missingFields: string[]) => void;
  className?: string;
}

interface AnalysisResult {
  field_completeness: {
    required_fields: string[];
    present_fields: string[];
    missing_fields: string[];
    optional_fields: string[];
    present_optional_fields: string[];
    completeness_score: number;
    total_required: number;
    total_present: number;
    total_missing: number;
  };
  clause_cache_predictions: {
    ai_sections: string[];
    cached_sections: string[];
    generated_sections: string[];
    cache_hit_rate: number;
    total_sections: number;
    cached_count: number;
    generated_count: number;
  };
  template_compatibility: {
    is_compatible: boolean;
    compatibility_score: number;
    issues: string[];
    warnings: string[];
  };
  recommendations: string[];
}

export function PreGenerationStats({
  templateId,
  documentId,
  cdmData,
  fieldOverrides,
  onClose,
  onMissingFieldsDetected,
  className = '',
}: PreGenerationStatsProps) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (templateId && (documentId || cdmData)) {
      loadAnalysis();
    }
  }, [templateId, documentId, cdmData, fieldOverrides]);

  const loadAnalysis = async () => {
    if (!templateId) return;

    try {
      setLoading(true);
      setError(null);

      const requestBody: any = {};
      if (documentId) {
        requestBody.document_id = documentId;
      } else if (cdmData) {
        requestBody.cdm_data = cdmData;
      }

      if (fieldOverrides && Object.keys(fieldOverrides).length > 0) {
        requestBody.field_overrides = fieldOverrides;
      }

      const response = await fetchWithAuth(
        `/api/templates/${templateId}/pre-generation-analysis`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to load analysis');
      }

      const data = await response.json();
      setAnalysis(data.analysis);
      
      // Notify parent about missing fields
      if (onMissingFieldsDetected && data.analysis?.field_completeness?.missing_fields) {
        onMissingFieldsDetected(data.analysis.field_completeness.missing_fields);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analysis');
      console.error('Error loading pre-generation analysis:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!templateId || (!documentId && !cdmData)) {
    return null;
  }

  if (loading) {
    return (
      <Card className={`bg-slate-800 border-slate-700 ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
            <span className="ml-2 text-sm text-slate-400">Analyzing...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`bg-slate-800 border-slate-700 ${className}`}>
        <CardContent className="p-6">
          <div className="flex items-center text-red-400">
            <XCircle className="w-5 h-5 mr-2" />
            <span className="text-sm">{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!analysis) {
    return null;
  }

  const { field_completeness, clause_cache_predictions, template_compatibility, recommendations } = analysis;

  const getCompletenessColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  // const getCompletenessBgColor = (score: number) => { // unused
  //   if (score >= 80) return 'bg-emerald-900/30';
  //   if (score >= 50) return 'bg-yellow-900/30';
  //   return 'bg-red-900/30';
  // };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <Info className="w-5 h-5 text-emerald-500" />
          Pre-Generation Analysis
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200"
          >
            <XCircle className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Field Completeness */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-100">
            <TrendingUp className="w-4 h-4" />
            Field Completeness
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">Completeness Score</span>
              <span className={`font-semibold ${getCompletenessColor(field_completeness.completeness_score)}`}>
                {field_completeness.completeness_score.toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={field_completeness.completeness_score} 
              className="h-2"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-slate-400">Required</div>
              <div className="font-semibold text-slate-200">
                {field_completeness.total_required}
              </div>
            </div>
            <div>
              <div className="text-slate-400">Present</div>
              <div className="font-semibold text-emerald-400">
                {field_completeness.total_present}
              </div>
            </div>
            <div>
              <div className="text-slate-400">Missing</div>
              <div className="font-semibold text-red-400">
                {field_completeness.total_missing}
              </div>
            </div>
          </div>

          {field_completeness.missing_fields.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-medium text-slate-300 mb-2">Missing Required Fields:</div>
              <div className="flex flex-wrap gap-2">
                {field_completeness.missing_fields.slice(0, 5).map((field, idx) => (
                  <Badge key={idx} variant="destructive" className="text-xs">
                    {field.split('.').pop()}
                  </Badge>
                ))}
                {field_completeness.missing_fields.length > 5 && (
                  <Badge variant="outline" className="text-xs border-slate-600 text-slate-300">
                    +{field_completeness.missing_fields.length - 5} more
                  </Badge>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Clause Cache Predictions */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-100">
            <Database className="w-4 h-4" />
            Clause Cache Predictions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">Cache Hit Rate</span>
              <span className="font-semibold text-emerald-400">
                {clause_cache_predictions.cache_hit_rate.toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={clause_cache_predictions.cache_hit_rate} 
              className="h-2"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-slate-400">Total Sections</div>
              <div className="font-semibold text-slate-200">
                {clause_cache_predictions.total_sections}
              </div>
            </div>
            <div>
              <div className="text-slate-400 flex items-center gap-1">
                <Database className="w-3 h-3" />
                Cached
              </div>
              <div className="font-semibold text-emerald-400">
                {clause_cache_predictions.cached_count}
              </div>
            </div>
            <div>
              <div className="text-slate-400 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                Generated
              </div>
              <div className="font-semibold text-blue-400">
                {clause_cache_predictions.generated_count}
              </div>
            </div>
          </div>

          {clause_cache_predictions.cached_sections.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-medium text-slate-300 mb-2">Cached Sections:</div>
              <div className="flex flex-wrap gap-2">
                {clause_cache_predictions.cached_sections.map((section, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs bg-emerald-900/30 text-emerald-300 border-emerald-700">
                    {section.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Template Compatibility */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-100">
            {template_compatibility.is_compatible ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-400" />
            )}
            Template Compatibility
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-400">Compatibility Score</span>
            <span className={`font-semibold ${
              template_compatibility.is_compatible ? 'text-emerald-400' : 'text-red-400'
            }`}>
              {template_compatibility.compatibility_score.toFixed(1)}%
            </span>
          </div>

          {template_compatibility.issues.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-medium text-red-300 mb-2 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Issues:
              </div>
              <ul className="list-disc list-inside text-xs text-red-400 space-y-1">
                {template_compatibility.issues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          {template_compatibility.warnings.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-medium text-yellow-300 mb-2 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Warnings:
              </div>
              <ul className="list-disc list-inside text-xs text-yellow-400 space-y-1">
                {template_compatibility.warnings.map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2 text-slate-100">
              <Info className="w-4 h-4" />
              Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {recommendations.map((rec, idx) => (
                <li key={idx} className="text-sm text-slate-300 flex items-start gap-2">
                  <span className="text-emerald-400 mt-0.5">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
