/**
 * Rule Builder - Visual rule creation form component.
 * 
 * Features:
 * - Visual rule creation form
 * - Condition builder with nested any/all support
 * - Field selector with autocomplete
 * - Operator selector (eq, gt, lt, in, contains, etc.)
 * - Value input with type validation
 * - Support for nested any/all conditions
 */

import { useState, useCallback } from 'react';
import { Plus, X, GripVertical, ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Card, CardContent, CardHeader } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';

// Types
export interface Condition {
  field?: string;
  op?: string;
  value?: any;
  any?: Condition[];
  all?: Condition[];
}

export interface Rule {
  name: string;
  when: Condition;
  action: 'allow' | 'block' | 'flag';
  priority: number;
  description?: string;
  category?: string;
}

interface RuleBuilderProps {
  rule: Rule;
  onRuleChange: (rule: Rule) => void;
  onDelete?: () => void;
}

// Available operators
const OPERATORS = [
  { value: 'eq', label: 'Equals (==)' },
  { value: 'ne', label: 'Not Equals (!=)' },
  { value: 'gt', label: 'Greater Than (>)' },
  { value: 'gte', label: 'Greater Than or Equal (>=)' },
  { value: 'lt', label: 'Less Than (<)' },
  { value: 'lte', label: 'Less Than or Equal (<=)' },
  { value: 'in', label: 'In (array contains)' },
  { value: 'not_in', label: 'Not In (array does not contain)' },
  { value: 'contains', label: 'Contains (string)' },
  { value: 'not_contains', label: 'Not Contains (string)' },
];

// Common field suggestions
const FIELD_SUGGESTIONS = [
  'transaction_id',
  'transaction_type',
  'originator.lei',
  'originator.name',
  'originator.jurisdiction',
  'amount',
  'currency',
  'facility_name',
  'facility_type',
  'sustainability_linked',
  'governing_law',
  'regulatory_framework',
  'risk_weighted_assets',
  'calculated_capital_requirement',
  'probability_of_default',
  'loss_given_default',
  'exposure_at_default',
  'available_tier1_capital',
  'tier1_capital_ratio',
  'sector_concentration',
];

export function RuleBuilder({ rule, onRuleChange, onDelete }: RuleBuilderProps) {
  const [expandedConditions, setExpandedConditions] = useState<Set<string>>(new Set(['root']));
  
  const toggleCondition = (path: string) => {
    const newExpanded = new Set(expandedConditions);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedConditions(newExpanded);
  };
  
  const updateRule = (updates: Partial<Rule>) => {
    onRuleChange({ ...rule, ...updates });
  };
  
  const updateCondition = (path: string, condition: Condition) => {
    const updateConditionAtPath = (cond: Condition, pathParts: string[]): Condition => {
      if (pathParts.length === 0) {
        return condition;
      }
      
      const [first, ...rest] = pathParts;
      
      if (first === 'any' && cond.any) {
        const index = parseInt(rest[0]);
        return {
          ...cond,
          any: cond.any.map((c, i) => i === index ? updateConditionAtPath(c, rest.slice(1)) : c)
        };
      }
      
      if (first === 'all' && cond.all) {
        const index = parseInt(rest[0]);
        return {
          ...cond,
          all: cond.all.map((c, i) => i === index ? updateConditionAtPath(c, rest.slice(1)) : c)
        };
      }
      
      return cond;
    };
    
    const pathParts = path.split('.').filter(p => p !== 'root');
    const updatedWhen = updateConditionAtPath(rule.when, pathParts);
    updateRule({ when: updatedWhen });
  };
  
  const addCondition = (path: string, type: 'any' | 'all' | 'field') => {
    const newCondition: Condition = type === 'field' 
      ? { field: '', op: 'eq', value: '' }
      : type === 'any'
      ? { any: [] }
      : { all: [] };
    
    const addConditionAtPath = (cond: Condition, pathParts: string[]): Condition => {
      if (pathParts.length === 0) {
        if (type === 'any' && cond.any) {
          return { ...cond, any: [...cond.any, newCondition] };
        }
        if (type === 'all' && cond.all) {
          return { ...cond, all: [...cond.all, newCondition] };
        }
        if (type === 'any') {
          return { any: [newCondition] };
        }
        if (type === 'all') {
          return { all: [newCondition] };
        }
        return newCondition;
      }
      
      const [first, ...rest] = pathParts;
      
      if (first === 'any' && cond.any) {
        const index = parseInt(rest[0]);
        return {
          ...cond,
          any: cond.any.map((c, i) => i === index ? addConditionAtPath(c, rest.slice(1)) : c)
        };
      }
      
      if (first === 'all' && cond.all) {
        const index = parseInt(rest[0]);
        return {
          ...cond,
          all: cond.all.map((c, i) => i === index ? addConditionAtPath(c, rest.slice(1)) : c)
        };
      }
      
      return cond;
    };
    
    const pathParts = path.split('.').filter(p => p !== 'root');
    const updatedWhen = addConditionAtPath(rule.when, pathParts);
    updateRule({ when: updatedWhen });
  };
  
  const deleteCondition = (path: string) => {
    const deleteConditionAtPath = (cond: Condition, pathParts: string[]): Condition | null => {
      if (pathParts.length === 0) {
        return null; // Delete this condition
      }
      
      const [first, ...rest] = pathParts;
      
      if (first === 'any' && cond.any) {
        const index = parseInt(rest[0]);
        if (rest.length === 1) {
          // Delete from array
          return {
            ...cond,
            any: cond.any.filter((_, i) => i !== index)
          };
        }
        return {
          ...cond,
          any: cond.any.map((c, i) => {
            const updated = deleteConditionAtPath(c, rest.slice(1));
            return updated !== null ? updated : c;
          }).filter(c => c !== null) as Condition[]
        };
      }
      
      if (first === 'all' && cond.all) {
        const index = parseInt(rest[0]);
        if (rest.length === 1) {
          // Delete from array
          return {
            ...cond,
            all: cond.all.filter((_, i) => i !== index)
          };
        }
        return {
          ...cond,
          all: cond.all.map((c, i) => {
            const updated = deleteConditionAtPath(c, rest.slice(1));
            return updated !== null ? updated : c;
          }).filter(c => c !== null) as Condition[]
        };
      }
      
      return cond;
    };
    
    const pathParts = path.split('.').filter(p => p !== 'root');
    const updatedWhen = deleteConditionAtPath(rule.when, pathParts);
    if (updatedWhen !== null) {
      updateRule({ when: updatedWhen });
    } else {
      // Root condition deleted, reset to empty
      updateRule({ when: {} });
    }
  };
  
  const renderCondition = (condition: Condition, path: string, depth: number = 0): React.ReactElement => {
    const isExpanded = expandedConditions.has(path);
    const hasChildren = (condition.any && condition.any.length > 0) || (condition.all && condition.all.length > 0);
    
    if (condition.any && condition.any.length >= 0) {
      return (
        <div className={`ml-${depth * 4} border-l-2 border-blue-300 pl-4 py-2`}>
          <div className="flex items-center gap-2 mb-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => toggleCondition(path)}
            >
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
            <Badge variant="outline" className="bg-blue-50">
              ANY ({condition.any.length})
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => addCondition(path, 'field')}
            >
              <Plus className="h-3 w-3 mr-1" />
              Add Field
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => addCondition(path, 'all')}
            >
              <Plus className="h-3 w-3 mr-1" />
              Add ALL
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-destructive"
              onClick={() => deleteCondition(path)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          {isExpanded && (
            <div className="space-y-2">
              {condition.any.map((c, index) => (
                <div key={index}>
                  {renderCondition(c, `${path}.any.${index}`, depth + 1)}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }
    
    if (condition.all && condition.all.length >= 0) {
      return (
        <div className={`ml-${depth * 4} border-l-2 border-green-300 pl-4 py-2`}>
          <div className="flex items-center gap-2 mb-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => toggleCondition(path)}
            >
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
            <Badge variant="outline" className="bg-green-50">
              ALL ({condition.all.length})
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => addCondition(path, 'field')}
            >
              <Plus className="h-3 w-3 mr-1" />
              Add Field
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => addCondition(path, 'any')}
            >
              <Plus className="h-3 w-3 mr-1" />
              Add ANY
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-destructive"
              onClick={() => deleteCondition(path)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          {isExpanded && (
            <div className="space-y-2">
              {condition.all.map((c, index) => (
                <div key={index}>
                  {renderCondition(c, `${path}.all.${index}`, depth + 1)}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }
    
    // Field condition
    return (
      <Card className={`ml-${depth * 4} border-2`}>
        <CardContent className="p-4">
          <div className="flex items-start gap-2">
            <GripVertical className="h-5 w-5 text-muted-foreground mt-2" />
            <div className="flex-1 grid grid-cols-12 gap-2">
              <div className="col-span-4">
                <Label>Field</Label>
                <Input
                  list={`field-suggestions-${path}`}
                  value={condition.field || ''}
                  onChange={(e) => updateCondition(path, { ...condition, field: e.target.value })}
                  placeholder="e.g., originator.lei"
                />
                <datalist id={`field-suggestions-${path}`}>
                  {FIELD_SUGGESTIONS.map(field => (
                    <option key={field} value={field} />
                  ))}
                </datalist>
              </div>
              <div className="col-span-3">
                <Label>Operator</Label>
                <select
                  value={condition.op || 'eq'}
                  onChange={(e) => updateCondition(path, { ...condition, op: e.target.value })}
                  className="w-full p-2 border rounded"
                >
                  {OPERATORS.map(op => (
                    <option key={op.value} value={op.value}>
                      {op.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-span-4">
                <Label>Value</Label>
                <Input
                  value={condition.value !== undefined ? String(condition.value) : ''}
                  onChange={(e) => {
                    let value: any = e.target.value;
                    // Try to parse as number or JSON
                    if (!isNaN(Number(value)) && value.trim() !== '') {
                      value = Number(value);
                    } else if (value.startsWith('[') || value.startsWith('{')) {
                      try {
                        value = JSON.parse(value);
                      } catch {
                        // Keep as string
                      }
                    }
                    updateCondition(path, { ...condition, value });
                  }}
                  placeholder="Value or JSON"
                />
              </div>
              <div className="col-span-1 flex items-end">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive"
                  onClick={() => deleteCondition(path)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };
  
  return (
    <Card className="border-2">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <Input
              value={rule.name}
              onChange={(e) => updateRule({ name: e.target.value })}
              placeholder="Rule name"
              className="font-semibold text-lg"
            />
          </div>
          {onDelete && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onDelete}
              className="text-destructive"
            >
              <X className="h-5 w-5" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Action and Priority */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Action</Label>
            <select
              value={rule.action}
              onChange={(e) => updateRule({ action: e.target.value as any })}
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
              onChange={(e) => updateRule({ priority: parseInt(e.target.value) || 0 })}
              min="0"
              max="100"
            />
          </div>
        </div>
        
        {/* Description */}
        <div>
          <Label>Description</Label>
          <Textarea
            value={rule.description || ''}
            onChange={(e) => updateRule({ description: e.target.value })}
            placeholder="Describe what this rule does..."
            rows={2}
          />
        </div>
        
        {/* Condition Builder */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label>Condition</Label>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => addCondition('root', 'any')}
              >
                <Plus className="h-3 w-3 mr-1" />
                Add ANY
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => addCondition('root', 'all')}
              >
                <Plus className="h-3 w-3 mr-1" />
                Add ALL
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => addCondition('root', 'field')}
              >
                <Plus className="h-3 w-3 mr-1" />
                Add Field
              </Button>
            </div>
          </div>
          
          <div className="border rounded-lg p-4 bg-muted/50 min-h-[200px]">
            {(!rule.when || (Object.keys(rule.when).length === 0 && !rule.when.any && !rule.when.all)) ? (
              <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                <p className="text-sm">No conditions yet. Add a condition to get started.</p>
              </div>
            ) : (
              renderCondition(rule.when, 'root', 0)
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}