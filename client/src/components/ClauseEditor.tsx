/**
 * Clause Editor Component
 * 
 * Displays and manages cached AI-generated clauses.
 * Allows users to view, edit, and delete cached clauses.
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { 
  FileText, 
  Edit2, 
  Trash2, 
  Search, 
  ChevronDown, 
  ChevronUp,
  Loader2,
  AlertCircle,
  Save,
  Copy,
  // ExternalLink removed - unused
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Clause {
  id: number;
  template_id: number;
  field_name: string;
  clause_content: string;
  context_hash: string | null;
  context_summary: {
    borrower_name?: string;
    facility_amount?: string;
    currency?: string;
    governing_law?: string;
  } | null;
  usage_count: number;
  last_used_at: string | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
  template?: {
    id: number;
    code: string;
    name: string;
  };
}

interface ClauseEditorProps {
  className?: string;
}

export function ClauseEditor({ className = '' }: ClauseEditorProps) {
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [selectedFieldName, _setSelectedFieldName] = useState<string | null>(null); // Prefix setter with _ - unused
  const [isExpanded, setIsExpanded] = useState(false);
  const [editingClause, setEditingClause] = useState<Clause | null>(null);
  const [editContent, setEditContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [templates, setTemplates] = useState<Array<{ id: number; code: string; name: string }>>([]);

  // Load templates for filter
  useEffect(() => {
    fetchWithAuth('/api/templates')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setTemplates(data);
        } else if (data.templates) {
          setTemplates(data.templates);
        }
      })
      .catch(() => {
        // Ignore errors loading templates
      });
  }, []);

  const loadClauses = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (selectedTemplateId) {
        params.append('template_id', selectedTemplateId.toString());
      }
      if (selectedFieldName) {
        params.append('field_name', selectedFieldName);
      }
      params.append('limit', '50');

      const response = await fetchWithAuth(`/api/clauses?${params.toString()}`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to load clauses');
      }

      const data = await response.json();
      setClauses(data.clauses || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load clauses');
    } finally {
      setIsLoading(false);
    }
  }, [selectedTemplateId, selectedFieldName]);

  useEffect(() => {
    if (isExpanded) {
      loadClauses();
    }
  }, [isExpanded, loadClauses]);

  const handleEdit = (clause: Clause) => {
    setEditingClause(clause);
    setEditContent(clause.clause_content);
  };

  const handleSave = async () => {
    if (!editingClause) return;

    try {
      setIsSaving(true);
      const response = await fetchWithAuth(`/api/clauses/${editingClause.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          clause_content: editContent,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to update clause');
      }

      // Reload clauses
      await loadClauses();
      setEditingClause(null);
      setEditContent('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save clause');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (clauseId: number) => {
    if (!confirm('Are you sure you want to delete this clause? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetchWithAuth(`/api/clauses/${clauseId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to delete clause');
      }

      // Reload clauses
      await loadClauses();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete clause');
    }
  };

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    // Could show a toast notification here
  };

  // Filter clauses by search term
  const filteredClauses = clauses.filter(clause => {
    if (!searchTerm) return true;
    const search = searchTerm.toLowerCase();
    return (
      clause.field_name.toLowerCase().includes(search) ||
      clause.clause_content.toLowerCase().includes(search) ||
      clause.template?.name.toLowerCase().includes(search) ||
      clause.template?.code.toLowerCase().includes(search)
    );
  });

  return (
    <div className={className}>
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-medium text-white flex items-center gap-2">
              <FileText className="h-5 w-5 text-emerald-400" />
              Clause Cache Editor
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-slate-400 hover:text-white"
            >
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </CardHeader>

        {isExpanded && (
          <CardContent className="space-y-4">
            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search clauses..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 bg-slate-900/50 border-slate-700 text-white"
                />
              </div>
              <select
                value={selectedTemplateId || ''}
                onChange={(e) => setSelectedTemplateId(e.target.value ? parseInt(e.target.value) : null)}
                className="px-3 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-white text-sm"
              >
                <option value="">All Templates</option>
                {templates.map(template => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Error Message */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}

            {/* Loading State */}
            {isLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-emerald-400" />
              </div>
            )}

            {/* Clauses List */}
            {!isLoading && filteredClauses.length === 0 && (
              <div className="text-center py-8 text-slate-400">
                <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No cached clauses found</p>
                {searchTerm && <p className="text-sm mt-1">Try adjusting your search or filters</p>}
              </div>
            )}

            {!isLoading && filteredClauses.length > 0 && (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredClauses.map((clause) => (
                  <div
                    key={clause.id}
                    className="p-3 bg-slate-900/50 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-white text-sm">{clause.field_name}</span>
                          {clause.template && (
                            <span className="text-xs text-slate-400">
                              ({clause.template.name})
                            </span>
                          )}
                        </div>
                        {clause.context_summary && (
                          <div className="text-xs text-slate-500 space-x-2">
                            {clause.context_summary.borrower_name && (
                              <span>Borrower: {clause.context_summary.borrower_name}</span>
                            )}
                            {clause.context_summary.facility_amount && (
                              <span>Amount: {clause.context_summary.facility_amount} {clause.context_summary.currency}</span>
                            )}
                          </div>
                        )}
                        <div className="text-xs text-slate-500 mt-1">
                          Used {clause.usage_count} time{clause.usage_count !== 1 ? 's' : ''}
                          {clause.last_used_at && (
                            <span> • Last used: {new Date(clause.last_used_at).toLocaleDateString()}</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopy(clause.clause_content)}
                          className="h-7 w-7 p-0 text-slate-400 hover:text-white"
                          title="Copy clause"
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(clause)}
                          className="h-7 w-7 p-0 text-slate-400 hover:text-emerald-400"
                          title="Edit clause"
                        >
                          <Edit2 className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(clause.id)}
                          className="h-7 w-7 p-0 text-slate-400 hover:text-red-400"
                          title="Delete clause"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    <div className="text-sm text-slate-300 line-clamp-2">
                      {clause.clause_content.substring(0, 150)}
                      {clause.clause_content.length > 150 && '...'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        )}
      </Card>

      {/* Edit Dialog */}
      <Dialog open={!!editingClause} onOpenChange={(open) => !open && setEditingClause(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] bg-slate-800 border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-white">Edit Clause: {editingClause?.field_name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Clause Content
              </label>
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-64 p-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white font-mono text-sm resize-none"
                placeholder="Enter clause content..."
              />
            </div>
            <div className="flex items-center justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => setEditingClause(null)}
                className="text-slate-400 hover:text-white"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={isSaving}
                className="bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
