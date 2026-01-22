import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { 
  Shield, 
  Search, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Clock,
  ExternalLink,
  Code
} from 'lucide-react';

interface PolicyDecision {
  id: number;
  transaction_id: string;
  decision: 'ALLOW' | 'BLOCK' | 'FLAG';
  rule_applied: string;
  matched_rules?: string[];
  evaluation_trace?: any[];
  cdm_events?: any[];
  created_at: string;
  document_id?: number;
}

export function PolicyDecisionsExplorer() {
  const [decisions, setDecisions] = useState<PolicyDecision[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDecision, setSelectedDecision] = useState<PolicyDecision | null>(null);

  useEffect(() => {
    const fetchDecisions = async () => {
      try {
        setLoading(true);
        // Assuming there's an endpoint for this, or we use audit logs filtered by policy
        const response = await fetchWithAuth('/api/policy/audit/decisions?limit=50');
        if (!response.ok) {
          throw new Error('Failed to fetch policy decisions');
        }
        const data = await response.json();
        setDecisions(data.decisions || []);
      } catch (err) {
        console.error('Failed to fetch policy decisions:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDecisions();
  }, []);

  const filteredDecisions = decisions.filter(d => 
    d.transaction_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.rule_applied.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'ALLOW': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'BLOCK': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'FLAG': return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default: return null;
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'ALLOW': return 'bg-green-900/20 text-green-400 border-green-500/30';
      case 'BLOCK': return 'bg-red-900/20 text-red-400 border-red-500/30';
      case 'FLAG': return 'bg-yellow-900/20 text-yellow-400 border-yellow-500/30';
      default: return 'bg-slate-900/20 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-2">
            <Shield className="h-8 w-8 text-blue-400" />
            Policy Decisions Explorer
          </h1>
          <p className="text-slate-400 mt-1">Review deterministic policy evaluations and rule traces</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List View */}
        <Card className="lg:col-span-1 bg-slate-800/50 border-slate-700 flex flex-col h-[700px]">
          <CardHeader className="pb-3">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search transaction ID or rule..."
                className="pl-8 bg-slate-900 border-slate-700 text-slate-100"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto pt-0">
            {loading ? (
              <div className="flex justify-center py-10">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              </div>
            ) : filteredDecisions.length === 0 ? (
              <p className="text-center py-10 text-slate-500">No decisions found</p>
            ) : (
              <div className="space-y-2">
                {filteredDecisions.map((decision) => (
                  <button
                    key={decision.id}
                    onClick={() => setSelectedDecision(decision)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      selectedDecision?.id === decision.id
                        ? 'bg-blue-900/20 border-blue-500/50'
                        : 'bg-slate-900/40 border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-xs font-mono text-slate-400 truncate max-w-[120px]">
                        {decision.transaction_id}
                      </span>
                      <div className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${getDecisionColor(decision.decision)}`}>
                        {decision.decision}
                      </div>
                    </div>
                    <p className="text-sm font-medium text-slate-200 truncate">
                      {decision.rule_applied.replace(/_/g, ' ')}
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-[10px] text-slate-500">
                      <Clock className="h-3 w-3" />
                      {new Date(decision.created_at).toLocaleString()}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Detail View */}
        <Card className="lg:col-span-2 bg-slate-800/50 border-slate-700 h-[700px] overflow-y-auto">
          {selectedDecision ? (
            <CardContent className="p-6 space-y-6">
              <div className="flex justify-between items-start border-b border-slate-700 pb-4">
                <div>
                  <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                    {getDecisionIcon(selectedDecision.decision)}
                    {selectedDecision.decision} Decision
                  </h2>
                  <p className="text-slate-400 text-sm mt-1 font-mono">
                    Transaction: {selectedDecision.transaction_id}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-500">Evaluation Timestamp</p>
                  <p className="text-sm text-slate-300">
                    {new Date(selectedDecision.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
                  <h3 className="text-sm font-semibold text-slate-300 mb-2">Primary Rule Applied</h3>
                  <p className="text-slate-100">{selectedDecision.rule_applied}</p>
                </div>
                {selectedDecision.document_id && (
                  <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
                    <h3 className="text-sm font-semibold text-slate-300 mb-2">Source Document</h3>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-100 text-sm">Doc #{selectedDecision.document_id}</span>
                      <Button variant="ghost" size="sm" className="h-7 text-blue-400 hover:text-blue-300">
                        <ExternalLink className="h-3 w-3 mr-1" /> View
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Matched Rules */}
              {selectedDecision.matched_rules && selectedDecision.matched_rules.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-slate-300">All Matched Rules</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedDecision.matched_rules.map((rule, idx) => (
                      <span key={idx} className="bg-slate-900 text-slate-300 px-2 py-1 rounded text-xs border border-slate-700">
                        {rule}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Evaluation Trace */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                  <Code className="h-4 w-4" />
                  Evaluation Trace (Machine-Executable)
                </h3>
                <div className="bg-slate-900 rounded-lg p-4 border border-slate-700 overflow-x-auto">
                  {selectedDecision.evaluation_trace ? (
                    <pre className="text-xs text-blue-300 font-mono">
                      {JSON.stringify(selectedDecision.evaluation_trace, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-sm text-slate-500 italic">No trace information available for this decision.</p>
                  )}
                </div>
              </div>

              {/* CDM Events */}
              {selectedDecision.cdm_events && selectedDecision.cdm_events.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Generated CDM Events
                  </h3>
                  <div className="space-y-2">
                    {selectedDecision.cdm_events.map((event, idx) => (
                      <div key={idx} className="p-3 bg-slate-900/30 rounded border border-slate-700 flex justify-between items-center">
                        <div className="flex items-center gap-3">
                          <div className="p-1.5 bg-emerald-900/20 rounded border border-emerald-500/30">
                            <CheckCircle className="h-3 w-3 text-emerald-400" />
                          </div>
                          <div>
                            <p className="text-sm text-slate-200 font-medium">{event.eventType || 'CDM Event'}</p>
                            <p className="text-[10px] text-slate-500 font-mono">{event.meta?.globalKey || 'No Global Key'}</p>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm" className="text-xs text-slate-400">
                          JSON
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-500">
              <Shield className="h-16 w-16 mb-4 opacity-20" />
              <p>Select a policy decision to view detailed evaluation trace</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
