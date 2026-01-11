/**
 * Policy Template Selector - Template library browser for policies.
 * 
 * Features:
 * - Template library browser
 * - Filter by category (regulatory, credit_risk, esg, etc.)
 * - Preview template structure
 * - Clone template to new policy
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '../../context/AuthContext';
import { Search, Filter, Copy, Eye, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../../components/ui/dialog';

// Types
interface PolicyTemplate {
  id: number;
  name: string;
  category: string;
  description?: string;
  rules_yaml: string;
  metadata?: {
    rules_count?: number;
    rule_names?: string[];
    use_cases?: string[];
  };
}

interface PolicyTemplateSelectorProps {
  onTemplateSelect: (template: PolicyTemplate) => void;
  onClone?: (template: PolicyTemplate) => void;
  className?: string;
}

const CATEGORIES = [
  'regulatory',
  'credit_risk',
  'esg',
  'sanctions',
  'compliance',
  'basel_iii',
  'green_finance',
  'all'
];

export function PolicyTemplateSelector({ 
  onTemplateSelect, 
  onClone,
  className = '' 
}: PolicyTemplateSelectorProps) {
  const [templates, setTemplates] = useState<PolicyTemplate[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<PolicyTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [previewTemplate, setPreviewTemplate] = useState<PolicyTemplate | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  
  // Load templates from existing policies (for now, we'll use policies as templates)
  useEffect(() => {
    loadTemplates();
  }, []);
  
  // Filter templates based on search and category
  useEffect(() => {
    let filtered = templates;
    
    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(t => t.category === selectedCategory);
    }
    
    // Filter by search term
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(t => 
        t.name.toLowerCase().includes(term) ||
        t.description?.toLowerCase().includes(term) ||
        t.category.toLowerCase().includes(term)
      );
    }
    
    setFilteredTemplates(filtered);
  }, [templates, searchTerm, selectedCategory]);
  
  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Try to load from policy-templates endpoint first
      let templates: PolicyTemplate[] = [];
      
      try {
        const templateResponse = await fetchWithAuth('/api/policy-templates?limit=100');
        if (templateResponse.ok) {
          const templateData = await templateResponse.json();
          templates = (templateData.templates || []).map((template: any) => ({
            id: template.id,
            name: template.name,
            category: template.category || 'regulatory',
            description: template.description,
            rules_yaml: template.rules_yaml,
            metadata: {
              rules_count: template.metadata?.rules_count,
              rule_names: template.metadata?.rule_names,
              use_cases: template.metadata?.use_cases || [template.use_case].filter(Boolean)
            }
          }));
        }
      } catch (templateErr) {
        console.warn('Failed to load from policy-templates endpoint, trying policies:', templateErr);
      }
      
      // If no templates found, fall back to active policies
      if (templates.length === 0) {
        const policyResponse = await fetchWithAuth('/api/policies?status=active&limit=100');
        if (policyResponse.ok) {
          const policyData = await policyResponse.json();
          const policies = policyData.policies || [];
          
          // Convert policies to templates
          templates = policies.map((policy: any) => ({
            id: policy.id,
            name: policy.name,
            category: policy.category || 'regulatory',
            description: policy.description,
            rules_yaml: policy.rules_yaml,
            metadata: {
              rules_count: policy.metadata?.rules_count,
              rule_names: policy.metadata?.rule_names,
              use_cases: policy.metadata?.use_cases
            }
          }));
        }
      }
      
      setTemplates(templates);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setLoading(false);
    }
  };
  
  const handlePreview = (template: PolicyTemplate) => {
    setPreviewTemplate(template);
    setShowPreview(true);
  };
  
  const handleClone = (template: PolicyTemplate) => {
    if (onClone) {
      onClone(template);
    } else {
      onTemplateSelect(template);
    }
  };
  
  const parseRulesCount = (yaml: string): number => {
    try {
      // Simple count of rule entries (lines starting with "- name:")
      const matches = yaml.match(/^- name:/gm);
      return matches ? matches.length : 0;
    } catch {
      return 0;
    }
  };
  
  if (loading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }
  
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search and Filter */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search templates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 border rounded"
          >
            {CATEGORIES.map(cat => (
              <option key={cat} value={cat}>
                {cat === 'all' ? 'All Categories' : cat.charAt(0).toUpperCase() + cat.slice(1).replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      {/* Template Grid */}
      {filteredTemplates.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <p>No templates found.</p>
          {searchTerm || selectedCategory !== 'all' ? (
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => {
                setSearchTerm('');
                setSelectedCategory('all');
              }}
            >
              Clear Filters
            </Button>
          ) : null}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.map(template => (
            <Card key={template.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                    <CardDescription className="mt-1">
                      {template.description || 'No description'}
                    </CardDescription>
                  </div>
                  <Badge variant="outline">{template.category}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>
                      {template.metadata?.rules_count || parseRulesCount(template.rules_yaml)} rule(s)
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePreview(template)}
                      className="flex-1"
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      Preview
                    </Button>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => handleClone(template)}
                      className="flex-1"
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Clone
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      
      {/* Preview Dialog */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{previewTemplate?.name}</DialogTitle>
            <DialogDescription>
              {previewTemplate?.description || 'Template preview'}
            </DialogDescription>
          </DialogHeader>
          
          {previewTemplate && (
            <div className="space-y-4">
              <div>
                <Label>Category</Label>
                <Badge>{previewTemplate.category}</Badge>
              </div>
              
              <div>
                <Label>Rules YAML</Label>
                <pre className="mt-2 p-4 bg-muted rounded-lg overflow-x-auto text-sm">
                  {previewTemplate.rules_yaml}
                </pre>
              </div>
              
              {previewTemplate.metadata?.rule_names && previewTemplate.metadata.rule_names.length > 0 && (
                <div>
                  <Label>Rule Names</Label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {previewTemplate.metadata.rule_names.map((name, index) => (
                      <Badge key={index} variant="secondary">{name}</Badge>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowPreview(false)}
                >
                  Close
                </Button>
                <Button
                  onClick={() => {
                    handleClone(previewTemplate);
                    setShowPreview(false);
                  }}
                >
                  <Copy className="h-4 w-4 mr-2" />
                  Clone Template
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
