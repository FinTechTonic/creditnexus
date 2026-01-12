/**
 * Field Editor Modal Component
 * 
 * Displays missing required fields from template and allows manual entry
 * before document generation. Supports nested CDM fields.
 */

import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AlertCircle, CheckCircle2, Loader2, X, AlertTriangle } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import type { CreditAgreementData } from '@/context/FDC3Context';

interface FieldEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (fieldOverrides: Record<string, any>) => void;
  templateId: number | null;
  cdmData: CreditAgreementData;
  missingFields?: string[];
  showAllFields?: boolean; // If true, show all fields not just missing ones
}

interface FieldDefinition {
  path: string;
  label: string;
  type: 'string' | 'number' | 'date' | 'boolean';
  value: any;
  required: boolean;
  description?: string;
}

export function FieldEditorModal({
  isOpen,
  onClose,
  onSave,
  templateId,
  cdmData,
  missingFields = [],
  showAllFields = false,
}: FieldEditorModalProps) {
  const [fields, setFields] = useState<FieldDefinition[]>([]);
  const [fieldValues, setFieldValues] = useState<Record<string, any>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Load template requirements when modal opens
  useEffect(() => {
    if (isOpen && templateId) {
      loadTemplateRequirements();
    }
  }, [isOpen, templateId]);

  const loadTemplateRequirements = useCallback(async () => {
    if (!templateId) return;

    try {
      setIsLoading(true);
      setError(null);

      const response = await fetchWithAuth(`/api/templates/${templateId}/requirements`);
      if (!response.ok) {
        throw new Error('Failed to load template requirements');
      }

      const data = await response.json();
      const requiredFields = data.required_fields || [];
      
      // Parse field paths and create field definitions
      const fieldDefs: FieldDefinition[] = requiredFields.map((fieldPath: string) => {
        const value = getNestedValue(cdmData, fieldPath);
        return {
          path: fieldPath,
          label: formatFieldLabel(fieldPath),
          type: inferFieldType(fieldPath, value),
          value: value,
          required: true,
          description: getFieldDescription(fieldPath),
        };
      });

      // Filter fields based on showAllFields prop
      const fieldsToShow = showAllFields 
        ? fieldDefs 
        : fieldDefs.filter(f => f.value === null || f.value === undefined || f.value === '');

      setFields(fieldsToShow);
      
      // Initialize field values
      const initialValues: Record<string, any> = {};
      fieldsToShow.forEach(field => {
        initialValues[field.path] = field.value ?? '';
      });
      setFieldValues(initialValues);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load template requirements');
    } finally {
      setIsLoading(false);
    }
  }, [templateId, cdmData]);

  const getNestedValue = (obj: any, path: string): any => {
    const parts = path.split('.');
    let current = obj;
    
    for (const part of parts) {
      // Handle array access like parties[0] or parties[role='Borrower']
      if (part.includes('[')) {
        const [key, indexStr] = part.split('[');
        const indexMatch = indexStr.match(/^(\d+)\]$/);
        const roleMatch = indexStr.match(/^role=['"](.+)['"]\]$/);
        
        if (!current || !current[key]) return null;
        
        if (indexMatch) {
          // Array index access: parties[0]
          const index = parseInt(indexMatch[1], 10);
          current = current[key][index];
        } else if (roleMatch) {
          // Role-based access: parties[role='Borrower']
          const role = roleMatch[1];
          current = current[key].find((item: any) => item.role === role);
        } else {
          return null;
        }
      } else {
        current = current?.[part];
      }
      
      if (current === undefined || current === null) return null;
    }
    
    return current;
  };

  const formatFieldLabel = (path: string): string => {
    // Convert path like "parties[role='Borrower'].lei" to "Borrower LEI"
    const parts = path.split('.');
    const lastPart = parts[parts.length - 1];
    
    // Extract role if present
    const roleMatch = path.match(/role=['"](.+)['"]/);
    if (roleMatch) {
      return `${roleMatch[1]} ${lastPart.toUpperCase()}`;
    }
    
    // Format field name
    return lastPart
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  };

  const inferFieldType = (path: string, value: any): 'string' | 'number' | 'date' | 'boolean' => {
    if (value !== null && value !== undefined) {
      if (typeof value === 'boolean') return 'boolean';
      if (typeof value === 'number') return 'number';
      if (value instanceof Date || /^\d{4}-\d{2}-\d{2}/.test(String(value))) return 'date';
    }
    
    // Infer from field name
    const lowerPath = path.toLowerCase();
    if (lowerPath.includes('date')) return 'date';
    // Currency fields should be string, not number
    if (lowerPath.includes('currency')) return 'string';
    if (lowerPath.includes('amount') || lowerPath.includes('bps') || lowerPath.includes('spread')) return 'number';
    if (lowerPath.includes('lei') || lowerPath.includes('id')) return 'string';
    
    return 'string';
  };

  const getFieldDescription = (path: string): string => {
    const descriptions: Record<string, string> = {
      'lei': 'Legal Entity Identifier (20-character alphanumeric code)',
      'agreement_date': 'Date when the agreement was signed (YYYY-MM-DD)',
      'governing_law': 'Jurisdiction governing the agreement (e.g., "English", "New York")',
      'spread_bps': 'Interest rate spread in basis points (e.g., 350 for 3.5%)',
      'benchmark': 'Interest rate benchmark (e.g., "SOFR", "LIBOR")',
      'amount': 'Monetary amount (numeric value)',
      'currency': 'Currency code (e.g., "USD", "EUR", "GBP")',
      'maturity_date': 'Facility maturity date (YYYY-MM-DD)',
      'esg_kpi_targets': 'ESG KPI targets for sustainability-linked loans',
    };
    
    const lowerPath = path.toLowerCase();
    for (const [key, desc] of Object.entries(descriptions)) {
      if (lowerPath.includes(key)) return desc;
    }
    
    return '';
  };

  const handleFieldChange = (path: string, value: any) => {
    setFieldValues(prev => ({ ...prev, [path]: value }));
    
    // Clear validation error for this field
    if (validationErrors[path]) {
      setValidationErrors(prev => {
        const next = { ...prev };
        delete next[path];
        return next;
      });
    }
  };

  const validateField = (field: FieldDefinition, value: any): string | null => {
    if (field.required && (value === null || value === undefined || value === '')) {
      return 'This field is required';
    }

    if (value === null || value === undefined || value === '') {
      return null; // Optional fields can be empty
    }

    switch (field.type) {
      case 'number':
        if (isNaN(Number(value))) return 'Must be a valid number';
        if (field.path.includes('bps') && Number(value) < 0) return 'Basis points must be non-negative';
        break;
      case 'date':
        if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
          return 'Date must be in YYYY-MM-DD format';
        }
        break;
      case 'string':
        if (field.path.includes('lei') && String(value).length !== 20) {
          return 'LEI must be exactly 20 characters';
        }
        break;
    }

    return null;
  };

  const handleSave = () => {
    // Validate all fields
    const errors: Record<string, string> = {};
    fields.forEach(field => {
      const value = fieldValues[field.path];
      const error = validateField(field, value);
      if (error) {
        errors[field.path] = error;
      }
    });

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    // Convert field values to nested structure
    const fieldOverrides: Record<string, any> = {};
    fields.forEach(field => {
      const value = fieldValues[field.path];
      if (value !== null && value !== undefined && value !== '') {
        try {
          setNestedValue(fieldOverrides, field.path, value);
        } catch (err) {
          throw err;
        }
      }
    });

    setIsSaving(true);
    try {
      onSave(fieldOverrides);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save fields');
    } finally {
      setIsSaving(false);
    }
  };

  const setNestedValue = (obj: Record<string, any>, path: string, value: any) => {
    const parts = path.split('.');
    let current = obj;

    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      
      // Handle array access
      if (part.includes('[')) {
        const [key, indexStr] = part.split('[');
        const indexMatch = indexStr.match(/^(\d+)\]$/);
        const roleMatch = indexStr.match(/^role=['"](.+)['"]\]$/);
        
        if (!current[key]) {
          current[key] = [];
        }
        
        if (indexMatch) {
          const index = parseInt(indexMatch[1], 10);
          if (!current[key][index]) {
            current[key][index] = {};
          }
          current = current[key][index];
        } else if (roleMatch) {
          const role = roleMatch[1];
          let item = current[key].find((item: any) => item.role === role);
          if (!item) {
            item = { role };
            current[key].push(item);
          }
          current = item;
        }
      } else {
        if (!current[part]) {
          current[part] = {};
        }
        current = current[part];
      }
    }

    const lastPart = parts[parts.length - 1];
    current[lastPart] = value;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-slate-100">
            <AlertCircle className={`w-5 h-5 ${showAllFields ? 'text-emerald-400' : 'text-yellow-400'}`} />
            {showAllFields ? 'Edit CDM Fields' : 'Fill Missing Required Fields'}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
          </div>
        ) : error ? (
          <div className="p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
            {error}
          </div>
        ) : fields.length === 0 ? (
          <div className="p-4 bg-emerald-900/30 border border-emerald-700 rounded-lg text-emerald-300 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5" />
            <span>All required fields are present. You can proceed with generation.</span>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-3 bg-yellow-900/30 border border-yellow-700 rounded-lg">
              <p className="text-sm text-yellow-300">
                <strong>{fields.length}</strong> required field{fields.length !== 1 ? 's' : ''} missing. 
                Please fill them out before generating the document.
              </p>
            </div>

            <div className="space-y-4">
              {fields.map((field) => (
                <div key={field.path} className="space-y-2">
                  <Label htmlFor={field.path} className="flex items-center gap-2 text-slate-200">
                    {field.label}
                    {field.required && <span className="text-red-400">*</span>}
                  </Label>
                  
                  {field.description && (
                    <p className="text-xs text-slate-400">{field.description}</p>
                  )}

                  {field.type === 'date' ? (
                    <Input
                      id={field.path}
                      type="date"
                      value={fieldValues[field.path] || ''}
                      onChange={(e) => handleFieldChange(field.path, e.target.value)}
                      className={validationErrors[field.path] ? 'border-red-500' : ''}
                    />
                  ) : field.type === 'number' ? (
                    <Input
                      id={field.path}
                      type="number"
                      step={field.path.includes('bps') ? '1' : '0.01'}
                      value={fieldValues[field.path] || ''}
                      onChange={(e) => handleFieldChange(field.path, e.target.value ? parseFloat(e.target.value) : '')}
                      className={validationErrors[field.path] ? 'border-red-500' : ''}
                      placeholder={field.path.includes('bps') ? 'e.g., 350 for 3.5%' : 'Enter number'}
                    />
                  ) : field.type === 'boolean' ? (
                    <select
                      id={field.path}
                      value={fieldValues[field.path] === true ? 'true' : fieldValues[field.path] === false ? 'false' : ''}
                      onChange={(e) => handleFieldChange(field.path, e.target.value === 'true' ? true : e.target.value === 'false' ? false : null)}
                      className={`w-full px-3 py-2 border rounded-md ${validationErrors[field.path] ? 'border-red-500' : ''}`}
                    >
                      <option value="">Select...</option>
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                  ) : (
                    <Input
                      id={field.path}
                      type="text"
                      value={fieldValues[field.path] || ''}
                      onChange={(e) => handleFieldChange(field.path, e.target.value)}
                      className={validationErrors[field.path] ? 'border-red-500' : ''}
                      placeholder={field.description || `Enter ${field.label.toLowerCase()}`}
                      maxLength={field.path.includes('lei') ? 20 : undefined}
                    />
                  )}

                  {validationErrors[field.path] && (
                    <p className="text-xs text-red-500 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      {validationErrors[field.path]}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isSaving} className="border-slate-600 text-slate-200 hover:bg-slate-700">
            Cancel
          </Button>
          <Button 
            onClick={handleSave} 
            disabled={isSaving || fields.length === 0}
            className="bg-emerald-600 hover:bg-emerald-500"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              'Save & Continue'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
