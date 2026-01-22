/**
 * Template Selector Component
 * 
 * Displays a list of LMA templates with search and category filtering.
 */

import { useState, useMemo } from 'react';
import { Search, Filter, FileText, Sparkles } from 'lucide-react';

interface LMATemplate {
  id: number;
  template_code: string;
  name: string;
  category: string;
  subcategory?: string;
  governing_law?: string;
  version: string;
}

interface TemplateSelectorProps {
  templates: LMATemplate[];
  selectedTemplateId: number | null;
  onSelect: (templateId: number) => void;
  loading?: boolean;
}

export function TemplateSelector({
  templates,
  selectedTemplateId,
  onSelect,
  loading = false,
}: TemplateSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  // Extract unique categories from templates
  const categories = useMemo(() => {
    const cats = new Set(templates.map(t => t.category));
    return Array.from(cats).sort();
  }, [templates]);

  // Filter templates based on search and category
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search and Filter */}
      <div className="space-y-3">
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

      {/* Template List */}
      {filteredTemplates.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No templates found</p>
          {searchQuery && (
            <p className="text-xs mt-1">Try adjusting your search or filter</p>
          )}
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {filteredTemplates.map((template) => (
            <button
              key={template.id}
              onClick={() => onSelect(template.id)}
              className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
                selectedTemplateId === template.id
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Sparkles className={`h-4 w-4 ${
                      selectedTemplateId === template.id ? 'text-blue-600' : 'text-gray-400'
                    }`} />
                    <div className="font-medium text-gray-900">{template.name}</div>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {template.category}
                    {template.subcategory && ` • ${template.subcategory}`}
                  </div>
                  {template.governing_law && (
                    <div className="text-xs text-gray-400 mt-1">
                      {template.governing_law} Law
                    </div>
                  )}
                </div>
                <div className="text-xs text-gray-400 ml-2">
                  v{template.version}
                </div>
              </div>
              <div className="text-xs text-gray-400 mt-2 font-mono">
                {template.template_code}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Results count */}
      {filteredTemplates.length > 0 && (
        <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-200">
          Showing {filteredTemplates.length} of {templates.length} templates
        </div>
      )}
    </div>
  );
}
















