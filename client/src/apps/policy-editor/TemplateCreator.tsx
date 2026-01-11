/**
 * Template Creator - Create new policy templates from scratch or existing policies.
 * 
 * Features:
 * - Create template from scratch
 * - Create template from existing policy
 * - Set template metadata
 * - Mark as system template
 */

import { useState, useEffect } from 'react';
import { fetchWithAuth } from '../../context/AuthContext';
import { 
  Save, 
  FileText, 
  Loader2,
  AlertCircle,
  CheckCircle2,
  X
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../../components/ui/dialog';

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
}

interface Policy {
  id: number;
  name: string;
  category: string;
  description?: string;
  rules_yaml: string;
}

interface TemplateCreatorProps {
  isOpen: boolean;
  onClose: () => void;
  sourcePolicy?: Policy | null;
  onTemplateCreated?: (template: PolicyTemplate) => void;
}

export function TemplateCreator({
  isOpen,
  onClose,
  sourcePolicy,
  onTemplateCreated
}: TemplateCreatorProps) {
  const [name, setName] = useState('');
  const [category, setCategory] = useState('regulatory');
  const [description, setDescription] = useState('');
  const [rulesYaml, setRulesYaml] = useState('');
  const [useCase, setUseCase] = useState('');
  const [isSystemTemplate, setIsSystemTemplate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Populate from source policy if provided
  useEffect(() => {
    if (sourcePolicy) {
      setName(sourcePolicy.name);
      setCategory(sourcePolicy.category || 'regulatory');
      setDescription(sourcePolicy.description || '');
      setRulesYaml(sourcePolicy.rules_yaml);
    } else {
      // Reset form
      setName('');
      setCategory('regulatory');
      setDescription('');
      setRulesYaml('');
      setUseCase('');
      setIsSystemTemplate(false);
    }
    setError(null);
    setSuccess(null);
  }, [sourcePolicy, isOpen]);
  
  const handleSave = async () => {
    if (!name.trim() || !rulesYaml.trim()) {
      setError('Name and YAML rules are required');
      return;
    }
    
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      const response = await fetchWithAuth('/api/policy-templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          category: category,
          description: description.trim() || undefined,
          rules_yaml: rulesYaml.trim(),
          use_case: useCase.trim() || undefined,
          is_system_template: isSystemTemplate,
          metadata: {}
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create template');
      }
      
      const data = await response.json();
      setSuccess('Template created successfully');
      
      if (onTemplateCreated) {
        onTemplateCreated(data.template);
      }
      
      // Close after a short delay
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create template');
    } finally {
      setSaving(false);
    }
  };
  
  const categories = [
    'regulatory',
    'credit_risk',
    'esg',
    'compliance',
    'operational',
    'other'
  ];
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {sourcePolicy ? 'Create Template from Policy' : 'Create Policy Template'}
          </DialogTitle>
          <DialogDescription>
            {sourcePolicy 
              ? 'Create a reusable template from this policy'
              : 'Create a new policy template from scratch'}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Success/Error Alerts */}
          {success && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          {/* Template Name */}
          <div>
            <Label htmlFor="template-name">Template Name *</Label>
            <Input
              id="template-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Basel III Capital Requirements"
              required
            />
          </div>
          
          {/* Category */}
          <div>
            <Label htmlFor="template-category">Category *</Label>
            <select
              id="template-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {categories.map(cat => (
                <option key={cat} value={cat}>
                  {cat.charAt(0).toUpperCase() + cat.slice(1).replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>
          
          {/* Use Case */}
          <div>
            <Label htmlFor="template-use-case">Use Case (Optional)</Label>
            <Input
              id="template-use-case"
              value={useCase}
              onChange={(e) => setUseCase(e.target.value)}
              placeholder="e.g., basel_iii_capital, sanctions_screening"
            />
          </div>
          
          {/* Description */}
          <div>
            <Label htmlFor="template-description">Description (Optional)</Label>
            <Textarea
              id="template-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this template is used for..."
              rows={3}
            />
          </div>
          
          {/* YAML Rules */}
          <div>
            <Label htmlFor="template-yaml">YAML Rules *</Label>
            <Textarea
              id="template-yaml"
              value={rulesYaml}
              onChange={(e) => setRulesYaml(e.target.value)}
              placeholder="Enter YAML policy rules..."
              className="font-mono text-sm"
              rows={15}
              required
            />
          </div>
          
          {/* System Template Checkbox */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="system-template"
              checked={isSystemTemplate}
              onChange={(e) => setIsSystemTemplate(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="system-template" className="text-sm">
              Mark as system template (available to all users)
            </label>
          </div>
          
          {/* Actions */}
          <div className="flex items-center justify-end gap-2">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving || !name.trim() || !rulesYaml.trim()}
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Create Template
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
