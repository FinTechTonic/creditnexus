/**
 * Policy Editor - Main component for policy creation and editing.
 * 
 * Features:
 * - Split-pane layout: rule builder on left, YAML preview on right
 * - Real-time YAML generation from visual builder
 * - Real-time validation feedback
 * - Save draft functionality
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchWithAuth, useAuth } from '../../context/AuthContext';
import { RuleBuilder } from './RuleBuilder';
import { PolicyTemplateSelector } from './PolicyTemplateSelector';
import { 
  Save, 
  FileText, 
  AlertCircle, 
  CheckCircle2, 
  Loader2,
  ArrowLeft,
  Play,
  Eye,
  Code,
  Settings,
  History,
  CheckSquare,
  XSquare,
  List,
  Plus,
  Edit
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';

// Types
interface Policy {
  id: number;
  name: string;
  category: string;
  description?: string;
  rules_yaml: string;
  status: string;
  version: number;
  created_by: number;
  approved_by?: number;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  metadata?: Record<string, any>;
}

interface Rule {
  name: string;
  when: any;
  action: 'allow' | 'block' | 'flag';
  priority: number;
  description?: string;
  category?: string;
}

export function PolicyEditor() {
  const { policyId } = useParams<{ policyId?: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  
  // State
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [yamlPreview, setYamlPreview] = useState<string>('');
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingPolicies, setLoadingPolicies] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'builder' | 'yaml'>('builder');
  const [showTemplateSelector, setShowTemplateSelector] = useState(false);
  const [showPolicyList, setShowPolicyList] = useState(!policyId);
  const [policyName, setPolicyName] = useState('');
  const [policyCategory, setPolicyCategory] = useState('regulatory');
  const [policyDescription, setPolicyDescription] = useState('');
  
  // Load policies list on mount or when auth state changes
  useEffect(() => {
    if (!policyId && isAuthenticated) {
      loadPolicies();
    }
  }, [isAuthenticated, policyId]);

  // Load policy if editing
  useEffect(() => {
    if (policyId) {
      loadPolicy(parseInt(policyId));
      setShowPolicyList(false);
    } else {
      // New policy - initialize with empty rule
      setRules([{
        name: 'new_rule',
        when: {},
        action: 'allow',
        priority: 50,
        description: ''
      }]);
      generateYamlFromRules([{
        name: 'new_rule',
        when: {},
        action: 'allow',
        priority: 50,
        description: ''
      }]);
    }
  }, [policyId]);

  const loadPolicies = async () => {
    // Only load if authenticated
    if (!isAuthenticated) {
      setPolicies([]);
      return;
    }
    
    try {
      setLoadingPolicies(true);
      setError(null);
      
      const response = await fetchWithAuth('/api/policies?limit=100');
      
      if (!response.ok) {
        if (response.status === 401) {
          // Not authenticated - clear policies
          setPolicies([]);
          return;
        }
        throw new Error('Failed to load policies');
      }
      
      const data = await response.json();
      setPolicies(data.policies || []);
    } catch (err) {
      // Only set error if it's not an auth issue
      if (err instanceof Error && !err.message.includes('401')) {
        setError(err.message);
      }
      setPolicies([]);
    } finally {
      setLoadingPolicies(false);
    }
  };
  
  // Real-time YAML generation
  useEffect(() => {
    if (rules.length > 0) {
      const yaml = generateYamlFromRules(rules);
      setYamlPreview(yaml);
      
      // Validate in real-time (only if authenticated)
      if (isAuthenticated) {
        validateYaml(yaml);
      }
    }
  }, [rules, isAuthenticated]);
  
  const loadPolicy = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetchWithAuth(`/api/policies/${id}`);
      if (!response.ok) {
        throw new Error('Failed to load policy');
      }
      
      const data = await response.json();
      const loadedPolicy = data.policy;
      
      setPolicy(loadedPolicy);
      setPolicyName(loadedPolicy.name);
      setPolicyCategory(loadedPolicy.category || 'regulatory');
      setPolicyDescription(loadedPolicy.description || '');
      
      // Parse YAML to rules
      const parsedRules = parseYamlToRules(loadedPolicy.rules_yaml);
      setRules(parsedRules);
      setYamlPreview(loadedPolicy.rules_yaml);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load policy');
    } finally {
      setLoading(false);
    }
  };
  
  const generateYamlFromRules = (rulesToGenerate: Rule[]): string => {
    // Simple YAML generation (in production, use a proper YAML library)
    let yaml = '';
    
    for (const rule of rulesToGenerate) {
      yaml += `- name: ${rule.name}\n`;
      yaml += `  when:\n`;
      yaml += `    ${JSON.stringify(rule.when).replace(/"/g, '').replace(/,/g, ',\n    ')}\n`;
      yaml += `  action: ${rule.action}\n`;
      yaml += `  priority: ${rule.priority}\n`;
      if (rule.description) {
        yaml += `  description: ${rule.description}\n`;
      }
      if (rule.category) {
        yaml += `  category: ${rule.category}\n`;
      }
      yaml += '\n';
    }
    
    return yaml;
  };
  
  const parseYamlToRules = (yaml: string): Rule[] => {
    // Simple YAML parsing (in production, use a proper YAML library)
    try {
      // For now, return empty array - will be enhanced with proper YAML parsing
      return [];
    } catch (err) {
      console.error('Failed to parse YAML:', err);
      return [];
    }
  };
  
  const validateYaml = async (yaml: string) => {
    // Skip validation if no YAML content or user not authenticated
    if (!yaml || !yaml.trim() || !isAuthenticated) {
      return;
    }
    
    try {
      const endpoint = policyId 
        ? `/api/policies/${policyId}/validate`
        : '/api/policies/validate';
      
      const response = await fetchWithAuth(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules_yaml: yaml })
      });
      
      if (response.ok) {
        const data = await response.json();
        setValidationResult(data);
      } else if (response.status === 401) {
        // User not authenticated - silently skip validation
        return;
      } else {
        // Don't show error for validation failures - just log
        console.warn('Validation request failed:', response.status);
      }
    } catch (err) {
      // Silently handle validation errors
      console.debug('Validation error:', err);
    }
  };
  
  const handleSaveDraft = async () => {
    try {
      setSaving(true);
      setError(null);
      
      if (!policyName.trim()) {
        setError('Policy name is required');
        return;
      }
      
      const payload = {
        name: policyName,
        category: policyCategory,
        description: policyDescription,
        rules_yaml: yamlPreview,
        metadata: {}
      };
      
      let response;
      if (policyId) {
        // Update existing policy
        response = await fetchWithAuth(`/api/policies/${policyId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        // Create new policy
        response = await fetchWithAuth('/api/policies', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save policy');
      }
      
      const data = await response.json();
      const savedPolicy = data.policy;
      
      // Navigate to edit mode if new policy
      if (!policyId && savedPolicy.id) {
        navigate(`/app/policy-editor/${savedPolicy.id}`);
      }
      
      setPolicy(savedPolicy);
      setShowPolicyList(false);
      
      // Reload policies list
      await loadPolicies();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save policy');
    } finally {
      setSaving(false);
    }
  };

  const handleTemplateSelect = (template: any) => {
    setPolicyName(template.name);
    setPolicyCategory(template.category || 'regulatory');
    setPolicyDescription(template.description || '');
    setYamlPreview(template.rules_yaml);
    // Try to parse YAML to rules
    const parsedRules = parseYamlToRules(template.rules_yaml);
    if (parsedRules.length > 0) {
      setRules(parsedRules);
    }
    setShowTemplateSelector(false);
  };

  const handleCreateNew = () => {
    setShowPolicyList(false);
    setShowTemplateSelector(false);
    setPolicy(null);
    setPolicyName('');
    setPolicyCategory('regulatory');
    setPolicyDescription('');
    setRules([{
      name: 'new_rule',
      when: {},
      action: 'allow',
      priority: 50,
      description: ''
    }]);
    generateYamlFromRules([{
      name: 'new_rule',
      when: {},
      action: 'allow',
      priority: 50,
      description: ''
    }]);
  };
  
  const handleAddRule = () => {
    const newRule: Rule = {
      name: `rule_${rules.length + 1}`,
      when: {},
      action: 'allow',
      priority: 50,
      description: ''
    };
    setRules([...rules, newRule]);
  };
  
  const handleUpdateRule = (index: number, updatedRule: Partial<Rule>) => {
    const updatedRules = [...rules];
    updatedRules[index] = { ...updatedRules[index], ...updatedRule };
    setRules(updatedRules);
  };
  
  const handleDeleteRule = (index: number) => {
    const updatedRules = rules.filter((_, i) => i !== index);
    setRules(updatedRules);
  };

  // Show policy list if no policyId and showPolicyList is true
  if (showPolicyList && !policyId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Policy Editor</h1>
            <p className="text-muted-foreground">Manage and create policy rules</p>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => setShowTemplateSelector(true)} variant="outline">
              <FileText className="h-4 w-4 mr-2" />
              Use Template
            </Button>
            <Button onClick={handleCreateNew}>
              <Plus className="h-4 w-4 mr-2" />
              Create New Policy
            </Button>
          </div>
        </div>

        {loadingPolicies ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {policies.length === 0 ? (
              <div className="col-span-full text-center p-8 text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No policies found. Create your first policy to get started.</p>
              </div>
            ) : (
              policies.map((p) => (
                <Card key={p.id} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => navigate(`/app/policy-editor/${p.id}`)}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-lg">{p.name}</CardTitle>
                      <Badge variant="outline">{p.status}</Badge>
                    </div>
                    <CardDescription>{p.category}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {p.description && (
                      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{p.description}</p>
                    )}
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>Version {p.version}</span>
                      <span>{new Date(p.updated_at).toLocaleDateString()}</span>
                    </div>
                    <Button 
                      className="w-full mt-4" 
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/app/policy-editor/${p.id}`);
                      }}
                    >
                      <Edit className="h-4 w-4 mr-2" />
                      Edit Policy
                    </Button>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}
      </div>
    );
  }

  // Show template selector
  if (showTemplateSelector) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Select Template</h1>
            <p className="text-muted-foreground">Choose a template to start from</p>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => setShowTemplateSelector(false)} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <Button onClick={handleCreateNew}>
              <Plus className="h-4 w-4 mr-2" />
              Start from Scratch
            </Button>
          </div>
        </div>
        <PolicyTemplateSelector
          onTemplateSelect={handleTemplateSelect}
          onClone={handleTemplateSelect}
        />
      </div>
    );
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }
  
  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/dashboard')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">
              {policyId ? 'Edit Policy' : 'Create Policy'}
            </h1>
            <p className="text-muted-foreground">
              {policyId ? `Policy ID: ${policyId}` : 'Create a new policy rule set'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {validationResult && (
            <Badge variant={validationResult.valid ? "default" : "destructive"}>
              {validationResult.valid ? (
                <>
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Valid
                </>
              ) : (
                <>
                  <AlertCircle className="h-3 w-3 mr-1" />
                  {validationResult.errors.length} error(s)
                </>
              )}
            </Badge>
          )}
          <Button
            onClick={handleSaveDraft}
            disabled={saving || !validationResult?.valid}
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Draft
              </>
            )}
          </Button>
        </div>
      </div>
      
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      {/* Policy Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Policy Information</CardTitle>
          <CardDescription>Basic information about this policy</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="policy-name">Policy Name *</Label>
              <Input
                id="policy-name"
                value={policyName}
                onChange={(e) => setPolicyName(e.target.value)}
                placeholder="e.g., Block Sanctioned Parties"
              />
            </div>
            <div>
              <Label htmlFor="policy-category">Category *</Label>
              <Input
                id="policy-category"
                value={policyCategory}
                onChange={(e) => setPolicyCategory(e.target.value)}
                placeholder="e.g., regulatory, credit_risk, esg"
              />
            </div>
          </div>
          <div>
            <Label htmlFor="policy-description">Description</Label>
            <Textarea
              id="policy-description"
              value={policyDescription}
              onChange={(e) => setPolicyDescription(e.target.value)}
              placeholder="Describe what this policy does..."
              rows={3}
            />
          </div>
        </CardContent>
      </Card>
      
      {/* Main Editor - Split Pane */}
      <div className="grid grid-cols-2 gap-6 h-[600px]">
        {/* Left: Rule Builder */}
        <Card className="overflow-hidden">
          <CardHeader className="border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Rule Builder
              </CardTitle>
              <Button size="sm" onClick={handleAddRule}>
                Add Rule
              </Button>
            </div>
          </CardHeader>
          <CardContent className="overflow-y-auto h-[calc(100%-80px)] p-4">
            {rules.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <FileText className="h-12 w-12 mb-4 opacity-50" />
                <p>No rules yet. Click "Add Rule" to get started.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {rules.map((rule, index) => (
                  <Card key={index} className="border-2">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <Input
                          value={rule.name}
                          onChange={(e) => handleUpdateRule(index, { name: e.target.value })}
                          placeholder="Rule name"
                          className="font-semibold"
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteRule(index)}
                        >
                          <XSquare className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div>
                        <Label>Action</Label>
                        <select
                          value={rule.action}
                          onChange={(e) => handleUpdateRule(index, { action: e.target.value as any })}
                          className="w-full p-2 border rounded"
                        >
                          <option value="allow">Allow</option>
                          <option value="block">Block</option>
                          <option value="flag">Flag</option>
                        </select>
                      </div>
                      <div>
                        <Label>Priority</Label>
                        <Input
                          type="number"
                          value={rule.priority}
                          onChange={(e) => handleUpdateRule(index, { priority: parseInt(e.target.value) || 0 })}
                          min="0"
                          max="100"
                        />
                      </div>
                      <div>
                        <Label>Description</Label>
                        <Textarea
                          value={rule.description || ''}
                          onChange={(e) => handleUpdateRule(index, { description: e.target.value })}
                          placeholder="Rule description..."
                          rows={2}
                        />
                      </div>
                      <div>
                        <Label>Condition (JSON)</Label>
                        <Textarea
                          value={JSON.stringify(rule.when, null, 2)}
                          onChange={(e) => {
                            try {
                              const when = JSON.parse(e.target.value);
                              handleUpdateRule(index, { when });
                            } catch (err) {
                              // Invalid JSON - ignore for now
                            }
                          }}
                          placeholder='{"field": "originator.lei", "op": "in", "value": ["SANCTIONED_LIST"]}'
                          rows={4}
                          className="font-mono text-sm"
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        
        {/* Right: YAML Preview */}
        <Card className="overflow-hidden">
          <CardHeader className="border-b">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5" />
                YAML Preview
              </CardTitle>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => validateYaml(yamlPreview)}
                >
                  <CheckSquare className="h-4 w-4 mr-2" />
                  Validate
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0 h-[calc(100%-80px)]">
            <Textarea
              value={yamlPreview}
              onChange={(e) => {
                setYamlPreview(e.target.value);
                // Try to parse and update rules
                try {
                  const parsedRules = parseYamlToRules(e.target.value);
                  if (parsedRules.length > 0) {
                    setRules(parsedRules);
                  }
                } catch (err) {
                  // Invalid YAML - keep current rules
                }
              }}
              className="h-full font-mono text-sm resize-none border-0"
              placeholder="YAML will be generated from rules..."
            />
          </CardContent>
        </Card>
      </div>
      
      {/* Validation Results */}
      {validationResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckSquare className="h-5 w-5" />
              Validation Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            {validationResult.valid ? (
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertDescription>
                  Policy YAML is valid. {validationResult.metadata?.rules_count || 0} rule(s) found.
                </AlertDescription>
              </Alert>
            ) : (
              <div className="space-y-2">
                {validationResult.errors.map((error, index) => (
                  <Alert key={index} variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                ))}
              </div>
            )}
            {validationResult.warnings.length > 0 && (
              <div className="mt-4 space-y-2">
                {validationResult.warnings.map((warning, index) => (
                  <Alert key={index}>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{warning}</AlertDescription>
                  </Alert>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
