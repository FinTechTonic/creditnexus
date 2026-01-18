/**
 * PeopleHub Result View Component
 * 
 * Displays PeopleHub research results with:
 * - Individual/business profile
 * - Psychometric analysis
 * - LinkedIn data
 * - Web research summaries
 * - Credit check data
 */

import { useState, useEffect } from 'react';
import {
  User,
  // Building2 removed - unused
  Linkedin,
  Globe,
  Brain,
  Shield,
  // CheckCircle2 removed - unused
  AlertCircle,
  Loader2,
  Copy,
  Download,
  X,
  FileText,
  // TrendingUp, TrendingDown removed - unused
  Award,
  Briefcase
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/components/ui/toast';

interface PeopleHubResult {
  id: number;
  person_name: string;
  linkedin_url: string | null;
  profile_data: {
    linkedin_data?: Record<string, unknown>;
    web_summaries?: Array<{
      url?: string;
      summary?: string;
      key_points?: string[];
    }>;
    research_report?: string;
    psychometric_analysis?: {
      personality_traits?: string[];
      risk_assessment?: string;
      behavioral_insights?: string[];
    };
    credit_check?: {
      risk_score?: number;
      credit_rating?: string;
      flags?: string[];
    };
  } | null;
  deal_id: number | null;
  created_at: string;
  updated_at: string;
}

interface PeopleHubResultViewProps {
  profileId: number;
  onClose?: () => void;
  dealId?: number | null;
}

export function PeopleHubResultView({
  profileId,
  onClose,
  dealId: _dealId // Prefix with _ - unused
}: PeopleHubResultViewProps) {
  const [result, setResult] = useState<PeopleHubResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { addToast } = useToast();

  useEffect(() => {
    const fetchResult = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Note: API endpoint may need to be created
        // For now, try to fetch from individual_profiles endpoint
        const response = await fetchWithAuth(`/api/business-intelligence/individual-profile/${profileId}`);
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: 'Failed to load result' }));
          throw new Error(errorData.detail?.message || errorData.message || 'Failed to load profile');
        }
        
        const data = await response.json();
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile result');
        addToast({
          title: 'Error',
          description: err instanceof Error ? err.message : 'Failed to load profile result',
          variant: 'destructive'
        });
      } finally {
        setLoading(false);
      }
    };
    
    fetchResult();
  }, [profileId, addToast]);

  const handleCopyReport = () => {
    if (result?.profile_data?.research_report) {
      navigator.clipboard.writeText(result.profile_data.research_report);
      addToast({
        title: 'Copied',
        description: 'Report copied to clipboard',
        variant: 'default'
      });
    }
  };

  const handleDownloadReport = () => {
    if (!result) return;
    
    const report = {
      person_name: result.person_name,
      linkedin_url: result.linkedin_url,
      profile_data: result.profile_data,
      created_at: result.created_at,
      updated_at: result.updated_at
    };
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `peoplehub_${result.person_name.replace(/\s+/g, '_')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    addToast({
      title: 'Downloaded',
      description: 'Profile report downloaded',
      variant: 'default'
    });
  };

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-emerald-500 mb-4" />
            <p className="text-slate-400">Loading profile result...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
            <p className="text-red-400 mb-2">Error loading result</p>
            <p className="text-slate-400 text-sm">{error}</p>
            {onClose && (
              <Button onClick={onClose} variant="outline" className="mt-4">
                Close
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex flex-col items-center justify-center py-12">
            <User className="h-12 w-12 text-slate-500 mb-4" />
            <p className="text-slate-400">No result found</p>
            {onClose && (
              <Button onClick={onClose} variant="outline" className="mt-4">
                Close
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  const profileData = result.profile_data || {};
  const linkedinData = profileData.linkedin_data || {};
  const psychometric = profileData.psychometric_analysis || {};
  const creditCheck = profileData.credit_check || {};

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="flex items-center gap-3">
            <User className="h-6 w-6 text-emerald-400" />
            <div>
              <CardTitle className="text-slate-100">{result.person_name}</CardTitle>
              <p className="text-sm text-slate-400 mt-1">
                Profile ID: {profileId}
                {result.linkedin_url && ' • LinkedIn Profile Available'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onClose && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="text-slate-400 hover:text-slate-100"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            {result.linkedin_url && (
              <a
                href={result.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-emerald-400 hover:text-emerald-300"
              >
                <Linkedin className="h-5 w-5" />
                <span>View LinkedIn Profile</span>
              </a>
            )}
            <div className="text-sm text-slate-400">
              Updated: {new Date(result.updated_at).toLocaleString()}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="bg-slate-800 border-slate-700">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="psychometric">Psychometric</TabsTrigger>
          <TabsTrigger value="research">Research</TabsTrigger>
          <TabsTrigger value="credit">Credit Check</TabsTrigger>
          <TabsTrigger value="full">Full Report</TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-slate-100">Profile Data</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyReport}
                  disabled={!profileData.research_report}
                >
                  <Copy className="h-4 w-4 mr-2" />
                  Copy
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadReport}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {Object.keys(linkedinData).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(linkedinData).map(([key, value]) => (
                    <div key={key} className="p-4 bg-slate-900/50 rounded-lg">
                      <h4 className="font-medium text-slate-300 mb-2 capitalize">
                        {key.replace(/_/g, ' ')}
                      </h4>
                      <p className="text-slate-200">
                        {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <User className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No profile data available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Psychometric Analysis Tab */}
        <TabsContent value="psychometric" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100 flex items-center gap-2">
                <Brain className="h-5 w-5" />
                Psychometric Analysis
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Personality Traits */}
              {psychometric.personality_traits && psychometric.personality_traits.length > 0 && (
                <div>
                  <h4 className="font-medium text-slate-300 mb-3 flex items-center gap-2">
                    <Award className="h-4 w-4" />
                    Personality Traits
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {psychometric.personality_traits.map((trait, idx) => (
                      <Badge key={idx} variant="outline" className="text-slate-300">
                        {trait}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Risk Assessment */}
              {psychometric.risk_assessment && (
                <div>
                  <h4 className="font-medium text-slate-300 mb-3 flex items-center gap-2">
                    <Shield className="h-4 w-4" />
                    Risk Assessment
                  </h4>
                  <p className="text-slate-200 bg-slate-900/50 p-3 rounded-lg">
                    {psychometric.risk_assessment}
                  </p>
                </div>
              )}

              {/* Behavioral Insights */}
              {psychometric.behavioral_insights && psychometric.behavioral_insights.length > 0 && (
                <div>
                  <h4 className="font-medium text-slate-300 mb-3 flex items-center gap-2">
                    <Briefcase className="h-4 w-4" />
                    Behavioral Insights
                  </h4>
                  <div className="space-y-2">
                    {psychometric.behavioral_insights.map((insight, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-slate-900/50 rounded-lg border border-slate-700"
                      >
                        <p className="text-slate-200 text-sm">{insight}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!psychometric.personality_traits && !psychometric.risk_assessment && !psychometric.behavioral_insights && (
                <div className="text-center py-8 text-slate-400">
                  <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No psychometric analysis available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Research Tab */}
        <TabsContent value="research" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Web Research Summaries</CardTitle>
            </CardHeader>
            <CardContent>
              {profileData.web_summaries && profileData.web_summaries.length > 0 ? (
                <div className="space-y-4">
                  {profileData.web_summaries.map((summary, idx) => (
                    <div
                      key={idx}
                      className="p-4 bg-slate-900/50 rounded-lg border border-slate-700"
                    >
                      {summary.url && (
                        <a
                          href={summary.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-emerald-400 hover:text-emerald-300 mb-2"
                        >
                          <Globe className="h-4 w-4" />
                          <span className="text-sm truncate">{summary.url}</span>
                        </a>
                      )}
                      {summary.summary && (
                        <p className="text-slate-200 text-sm mb-2">{summary.summary}</p>
                      )}
                      {summary.key_points && summary.key_points.length > 0 && (
                        <div className="mt-2">
                          <h5 className="text-xs font-medium text-slate-400 mb-1">Key Points:</h5>
                          <ul className="list-disc list-inside text-slate-300 text-sm space-y-1">
                            {summary.key_points.map((point, pidx) => (
                              <li key={pidx}>{point}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <Globe className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No web research summaries available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Credit Check Tab */}
        <TabsContent value="credit" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100 flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Credit Check
              </CardTitle>
            </CardHeader>
            <CardContent>
              {creditCheck.risk_score !== undefined || creditCheck.credit_rating ? (
                <div className="space-y-4">
                  {creditCheck.risk_score !== undefined && (
                    <div className="p-4 bg-slate-900/50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-medium text-slate-300">Risk Score</label>
                        <Badge
                          className={
                            creditCheck.risk_score < 0.3
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : creditCheck.risk_score < 0.7
                              ? 'bg-amber-500/20 text-amber-400'
                              : 'bg-red-500/20 text-red-400'
                          }
                        >
                          {(creditCheck.risk_score * 100).toFixed(1)}%
                        </Badge>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2 mt-2">
                        <div
                          className={`h-2 rounded-full ${
                            creditCheck.risk_score < 0.3
                              ? 'bg-emerald-500'
                              : creditCheck.risk_score < 0.7
                              ? 'bg-amber-500'
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${creditCheck.risk_score * 100}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {creditCheck.credit_rating && (
                    <div className="p-4 bg-slate-900/50 rounded-lg">
                      <label className="text-sm font-medium text-slate-300 mb-1 block">
                        Credit Rating
                      </label>
                      <p className="text-slate-100 text-lg font-semibold">
                        {creditCheck.credit_rating}
                      </p>
                    </div>
                  )}

                  {creditCheck.flags && creditCheck.flags.length > 0 && (
                    <div className="p-4 bg-slate-900/50 rounded-lg">
                      <label className="text-sm font-medium text-slate-300 mb-2 block">
                        Flags
                      </label>
                      <div className="space-y-1">
                        {creditCheck.flags.map((flag, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-2 text-amber-400 text-sm"
                          >
                            <AlertCircle className="h-4 w-4" />
                            <span>{flag}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No credit check data available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Full Report Tab */}
        <TabsContent value="full" className="mt-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-slate-100">Full Research Report</CardTitle>
            </CardHeader>
            <CardContent>
              {profileData.research_report ? (
                <div className="prose prose-invert max-w-none">
                  <pre className="text-slate-200 whitespace-pre-wrap text-sm bg-slate-900/50 p-4 rounded-lg overflow-auto max-h-[600px]">
                    {profileData.research_report}
                  </pre>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No full report available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
