/**
 * Template Library Component
 * 
 * Browse and explore available LMA templates with:
 * - Category filters
 * - Metadata display
 * - Template details
 * - Quick actions
 */

import { useState, useEffect, useMemo } from 'react';
import { fetchWithAuth } from '../context/AuthContext';
import { Search, Filter, FileText, Sparkles, Info, Loader2, AlertCircle } from 'lucide-react';

interface LMATemplate {
  id: number;
  template_code: string;
  name: string;
  category: string;
  subcategory?: string;
  governing_law?: string;
  version: string;
  required_fields?: string[];
  optional_fields?: string[];
  ai_generated_sections?: string[];
  estimated_generation_time_seconds?: number;
}

interface TemplateLibraryProps {
  onSelectTemplate?: (templateId: number) => void;
}

export function TemplateLibrary({ onSelectTemplate }: TemplateLibraryProps) {
  const [templates, setTemplates] = useState<LMATemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [selectedTemplate, setSelectedTemplate] = useState<LMATemplate | null>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetchWithAuth('/api/templates');
      if (response.ok) {
        const data = await response.json();
        setTemplates(data.templates || []);
      } else {
        throw new Error('Failed to load templates');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  // Extract unique categories
  const categories = useMemo(() => {
    const cats = new Set(templates.map(t => t.category));
    return Array.from(cats).sort();
  }, [templates]);

  // Filter templates
  const filteredTemplates = useMemo(() => {
    return templates.filter(template => {
      const matchesSearch = 
        searchQuery === '' ||
        template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        template.template_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (template.subcategory && template.subcategory.toLowerCase().includes(searchQuery.toLowerCase()));
      
      const matchesCategory = 
        categoryFilter === 'all' || 
        template.category === categoryFilter;
      
      return matchesSearch && matchesCategory;
    });
  }, [templates, searchQuery, categoryFilter]);

  const handleSelectTemplate = async (templateId: number) => {
    try {
      const response = await fetchWithAuth(`/api/templates/${templateId}`);
      if (response.ok) {
        const template = await response.json();
        setSelectedTemplate(template);
        if (onSelectTemplate) {
          onSelectTemplate(templateId);
        }
      }
    } catch (err) {
      console.error('Failed to load template details:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-l-4 border-red-400 p-4">
        <div className="flex items-center">
          <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-blue-600" />
          LMA Template Library
        </h2>
        <p className="text-sm text-gray-600 mt-1">
          Browse and explore available LMA document templates
        </p>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm appearance-none bg-white"
            >
              <option value="all">All Categories</option>
              {categories.map(category => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTemplates.map((template) => (
          <div
            key={template.id}
            className={`bg-white rounded-lg border-2 p-4 cursor-pointer transition-all hover:shadow-md ${
              selectedTemplate?.id === template.id
                ? 'border-blue-600 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => handleSelectTemplate(template.id)}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <Sparkles className={`h-5 w-5 ${
                  selectedTemplate?.id === template.id ? 'text-blue-600' : 'text-gray-400'
                }`} />
                <h3 className="font-semibold text-gray-900">{template.name}</h3>
              </div>
              <span className="text-xs text-gray-400">v{template.version}</span>
            </div>
            
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-gray-600">
                <span className="font-medium">Category:</span>
                <span>{template.category}</span>
              </div>
              {template.subcategory && (
                <div className="flex items-center gap-2 text-gray-600">
                  <span className="font-medium">Subcategory:</span>
                  <span>{template.subcategory}</span>
                </div>
              )}
              {template.governing_law && (
                <div className="flex items-center gap-2 text-gray-600">
                  <span className="font-medium">Governing Law:</span>
                  <span>{template.governing_law}</span>
                </div>
              )}
              {template.estimated_generation_time_seconds && (
                <div className="flex items-center gap-2 text-gray-600">
                  <span className="font-medium">Est. Time:</span>
                  <span>{template.estimated_generation_time_seconds}s</span>
                </div>
              )}
            </div>

            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <FileText className="h-3 w-3" />
                <span className="font-mono">{template.template_code}</span>
              </div>
              {template.required_fields && template.required_fields.length > 0 && (
                <div className="mt-2 text-xs text-gray-500">
                  {template.required_fields.length} required field(s)
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {filteredTemplates.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <FileText className="w-16 h-16 mx-auto mb-4 text-gray-400 opacity-50" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No templates found</h3>
          <p className="text-sm text-gray-600">
            {searchQuery || categoryFilter !== 'all'
              ? 'Try adjusting your search or filter criteria'
              : 'No templates are available'}
          </p>
        </div>
      )}

      {/* Selected Template Details */}
      {selectedTemplate && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Info className="h-5 w-5 text-blue-600" />
              Template Details
            </h3>
            <button
              onClick={() => setSelectedTemplate(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          </div>
          
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">{selectedTemplate.name}</h4>
              <div className="text-sm text-gray-600 space-y-1">
                <div><span className="font-medium">Code:</span> <code className="bg-gray-100 px-2 py-0.5 rounded">{selectedTemplate.template_code}</code></div>
                <div><span className="font-medium">Category:</span> {selectedTemplate.category}</div>
                {selectedTemplate.subcategory && (
                  <div><span className="font-medium">Subcategory:</span> {selectedTemplate.subcategory}</div>
                )}
                {selectedTemplate.governing_law && (
                  <div><span className="font-medium">Governing Law:</span> {selectedTemplate.governing_law}</div>
                )}
                <div><span className="font-medium">Version:</span> {selectedTemplate.version}</div>
              </div>
            </div>

            {selectedTemplate.required_fields && selectedTemplate.required_fields.length > 0 && (
              <div>
                <h5 className="font-medium text-gray-900 mb-2">Required Fields</h5>
                <ul className="text-sm text-gray-600 space-y-1">
                  {selectedTemplate.required_fields.map((field, idx) => (
                    <li key={idx} className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
                      <code className="text-xs bg-gray-100 px-2 py-0.5 rounded">{field}</code>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {selectedTemplate.ai_generated_sections && selectedTemplate.ai_generated_sections.length > 0 && (
              <div>
                <h5 className="font-medium text-gray-900 mb-2">AI-Generated Sections</h5>
                <ul className="text-sm text-gray-600 space-y-1">
                  {selectedTemplate.ai_generated_sections.map((section, idx) => (
                    <li key={idx} className="flex items-center gap-2">
                      <Sparkles className="h-3 w-3 text-purple-500" />
                      <span>{section}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Results Count */}
      {filteredTemplates.length > 0 && (
        <div className="text-sm text-gray-600 text-center">
          Showing {filteredTemplates.length} of {templates.length} templates
        </div>
      )}
    </div>
  );
}
















