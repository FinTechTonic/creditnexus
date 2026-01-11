/**
 * Policy Template Library - Browse and manage policy templates.
 * 
 * Features:
 * - Browse all policy templates
 * - Filter by category and use case
 * - Search templates
 * - Preview template structure
 * - Clone templates to create new policies
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '../../context/AuthContext';
import { 
  Search, 
  Filter, 
  FileText, 
  Copy,
  Eye,
  Loader2,
  Tag,
  Building2,
  AlertCircle
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';

// Types
interface PolicyTemplate {
  id: number;
  name: string;
  category: string;
  description?: string;
  rules_yaml: string;
  use_case?: string;
  metadata?: Record<string, any>;
  is_system_template: boolean;
  created_by?: number;
  created_at: string;
}

interface PolicyTemplateLibraryProps {
  onTemplateSelect?: (template: PolicyTemplate) => void;
  onClone?: (template: PolicyTemplate) => void;
  onPreview?: (template: PolicyTemplate) => void;
  className?: string;
}

export function PolicyTemplateLibrary({
  onTemplateSelect,
  onClone,
  onPreview,
  className = ''
}: PolicyTemplateLibraryProps) {
  const [templates, setTemplates] = useState<PolicyTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [useCaseFilter, setUseCaseFilter] = useState<string>('all');
  const [systemOnly, setSystemOnly] = useState(false);
  
  // Load templates
  useEffect(() => {
    loadTemplates();
  }, [categoryFilter, useCaseFilter, systemOnly]);
  
  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (categoryFilter !== 'all') {
        params.append('category', categoryFilter);
      }
      if (useCaseFilter !== 'all') {
        params.append('use_case', useCaseFilter);
      }
      if (systemOnly) {
        params.append('is_system_template', 'true');
      }
      
      const response = await fetchWithAuth(`/api/policy-templates?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Failed to load templates');
      }
      
      const data = await response.json();
      setTemplates(data.templates || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setLoading(false);
    }
  };
  
  const handleClone = (template: PolicyTemplate, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onClone) {
      onClone(template);
    }
  };
  
  const handlePreview = (template: PolicyTemplate, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onPreview) {
      onPreview(template);
    }
  };
  
  const handleSelect = (template: PolicyTemplate) => {
    if (onTemplateSelect) {
      onTemplateSelect(template);
    }
  };
  
  const filteredTemplates = templates.filter(template => {
    const matchesSearch = searchTerm === '' || 
      template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      template.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      template.use_case?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });
  
  const categories = Array.from(new Set(templates.map(t => t.category)));
  const useCases = Array.from(new Set(templates.map(t => t.use_case).filter(Boolean)));
  
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <FileText className="h-6 w-6" />
          Policy Template Library
        </h2>
        <p className="text-muted-foreground">
          Browse and clone pre-built policy templates
        </p>
      </div>
      
      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search templates..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="w-48">
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="all">All Categories</option>
                {categories.map(cat => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
            <div className="w-48">
              <select
                value={useCaseFilter}
                onChange={(e) => setUseCaseFilter(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="all">All Use Cases</option>
                {useCases.map(uc => (
                  <option key={uc} value={uc}>
                    {uc}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="system-only"
                checked={systemOnly}
                onChange={(e) => setSystemOnly(e.target.checked)}
                className="h-4 w-4"
              />
              <label htmlFor="system-only" className="text-sm">
                System Templates Only
              </label>
            </div>
            <Button
              variant="outline"
              onClick={loadTemplates}
            >
              <Filter className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      )}
      
      {/* Empty State */}
      {!loading && filteredTemplates.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">No Templates Found</h3>
            <p className="text-muted-foreground">
              {templates.length === 0 
                ? "No policy templates available. Create one to get started."
                : "No templates match your search criteria."}
            </p>
          </CardContent>
        </Card>
      )}
      
      {/* Template Grid */}
      {!loading && filteredTemplates.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.map(template => (
            <Card
              key={template.id}
              className="cursor-pointer hover:bg-muted transition-colors"
              onClick={() => handleSelect(template)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg mb-2">{template.name}</CardTitle>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline">{template.category}</Badge>
                      {template.use_case && (
                        <Badge variant="secondary">
                          <Tag className="h-3 w-3 mr-1" />
                          {template.use_case}
                        </Badge>
                      )}
                      {template.is_system_template && (
                        <Badge variant="default">System</Badge>
                      )}
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {template.description && (
                  <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                    {template.description}
                  </p>
                )}
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => handlePreview(template, e)}
                  >
                    <Eye className="h-4 w-4 mr-1" />
                    Preview
                  </Button>
                  <Button
                    size="sm"
                    variant="default"
                    onClick={(e) => handleClone(template, e)}
                  >
                    <Copy className="h-4 w-4 mr-1" />
                    Clone
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      
      {/* Summary */}
      {!loading && filteredTemplates.length > 0 && (
        <div className="text-sm text-muted-foreground text-center">
          Showing {filteredTemplates.length} of {templates.length} template{templates.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}
