import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
// Textarea removed - unused
import { Badge } from '@/components/ui/badge';
import {
  FileText,
  ExternalLink,
  Loader2,
  CheckCircle,
  AlertCircle,
  // Calendar, Building2, DollarSign removed - unused
  // Globe removed - unused
} from 'lucide-react';

interface FilingFormField {
  field_name: string;
  field_value: any;
  field_type: string;
  required: boolean;
  validation_rules?: Record<string, any>;
  help_text?: string;
}

interface FilingFormData {
  jurisdiction: string;
  authority: string;
  form_type: string;
  fields: FilingFormField[];
  document_references: string[];
  submission_url?: string;
  instructions?: string;
  language: string;
}

interface ManualFilingFormProps {
  filingId: number;
  onSubmitted?: (filingReference: string) => void;
}

export function ManualFilingForm({ filingId, onSubmitted }: ManualFilingFormProps) {
  const [formData, setFormData] = useState<FilingFormData | null>(null);
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filingReference, setFilingReference] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [touchedFields, setTouchedFields] = useState<Set<string>>(new Set());
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  useEffect(() => {
    fetchFormData();
  }, [filingId]);

  const fetchFormData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth(`/api/filings/${filingId}/prepare`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error('Failed to prepare filing form');
      }

      const data = await response.json();
      const filing = data.filing;
      
      // Extract form data from filing payload
      if (filing.filing_payload) {
        setFormData(filing.filing_payload as FilingFormData);
        
        // Initialize form values from pre-filled data
        const initialValues: Record<string, any> = {};
        if (filing.filing_payload.fields) {
          filing.filing_payload.fields.forEach((field: FilingFormField) => {
            initialValues[field.field_name] = field.field_value || '';
          });
        }
        setFormValues(initialValues);
      } else {
        throw new Error('No form data available');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load form data');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldName: string, value: any) => {
    setFormValues((prev) => ({
      ...prev,
      [fieldName]: value
    }));

    // Mark field as touched
    setTouchedFields((prev) => new Set(prev).add(fieldName));

    // Validate field in real-time if touched
    if (formData) {
      const field = formData.fields.find((f) => f.field_name === fieldName);
      if (field) {
        const fieldError = validateField(field, value);
        setFieldErrors((prev) => {
          const newErrors = { ...prev };
          if (fieldError) {
            newErrors[fieldName] = fieldError;
          } else {
            delete newErrors[fieldName];
          }
          return newErrors;
        });
      }
    }

    // Clear general error when user starts typing
    if (error) {
      setError(null);
    }
  };

  const validateField = (field: FilingFormField, value: any): string | null => {
    // Check required
    if (field.required && (!value || (typeof value === 'string' && value.trim() === ''))) {
      return `${field.field_name} is required`;
    }

    if (!value || (typeof value === 'string' && value.trim() === '')) {
      return null; // Empty optional fields are valid
    }

    // Apply validation rules
    if (field.validation_rules) {
      const stringValue = String(value);
      
      if (field.validation_rules.min_length && stringValue.length < field.validation_rules.min_length) {
        return `Must be at least ${field.validation_rules.min_length} characters`;
      }
      
      if (field.validation_rules.max_length && stringValue.length > field.validation_rules.max_length) {
        return `Must be no more than ${field.validation_rules.max_length} characters`;
      }
      
      if (field.validation_rules.pattern) {
        try {
          const regex = new RegExp(field.validation_rules.pattern);
          if (!regex.test(stringValue)) {
            return field.validation_rules.pattern_message || 'Format is invalid';
          }
        } catch (e) {
          console.error('Invalid regex pattern:', field.validation_rules.pattern);
        }
      }

      if (field.validation_rules.min !== undefined && Number(value) < field.validation_rules.min) {
        return `Must be at least ${field.validation_rules.min}`;
      }

      if (field.validation_rules.max !== undefined && Number(value) > field.validation_rules.max) {
        return `Must be no more than ${field.validation_rules.max}`;
      }

      if (field.validation_rules.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(stringValue)) {
        return 'Must be a valid email address';
      }

      if (field.validation_rules.url && !/^https?:\/\/.+/.test(stringValue)) {
        return 'Must be a valid URL';
      }
    }

    return null;
  };

  const validateForm = (): boolean => {
    if (!formData) return false;

    const errors: Record<string, string> = {};
    const validationErrorsList: string[] = [];

    for (const field of formData.fields) {
      const value = formValues[field.field_name];
      const fieldError = validateField(field, value);
      
      if (fieldError) {
        errors[field.field_name] = fieldError;
        validationErrorsList.push(`${field.field_name}: ${fieldError}`);
      }
    }

    setFieldErrors(errors);
    setValidationErrors(validationErrorsList);

    if (Object.keys(errors).length > 0) {
      setError(`Please fix ${Object.keys(errors).length} error${Object.keys(errors).length !== 1 ? 's' : ''} before submitting`);
      return false;
    }

    setError(null);
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    // For manual filings, user submits via external portal
    // We just track the submission reference
    const reference = prompt('Enter the filing reference number from the submission portal:');
    
    if (!reference) {
      setError('Filing reference is required');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetchWithAuth(`/api/filings/${filingId}/submit-manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filing_reference: reference,
          submission_notes: `Submitted via ${formData?.authority} portal`
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail?.message || errorData.message || errorData.detail || 'Failed to update filing status';
        
        // Handle field-level errors from API
        if (errorData.detail?.field_errors) {
          setFieldErrors(errorData.detail.field_errors);
        }
        
        // Handle validation errors
        if (errorData.detail?.validation_errors) {
          setValidationErrors(errorData.detail.validation_errors);
        }
        
        throw new Error(errorMessage);
      }

      setFilingReference(reference);
      setFieldErrors({});
      setValidationErrors([]);
      if (onSubmitted) {
        onSubmitted(reference);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to submit filing';
      setError(errorMessage);
      
      // Try to extract more details from error
      if (err instanceof Error && err.message.includes('validation')) {
        setValidationErrors([errorMessage]);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field: FilingFormField) => {
    const value = formValues[field.field_name] || '';
    const fieldId = `field-${field.field_name}`;
    const hasError = fieldErrors[field.field_name];
    const isTouched = touchedFields.has(field.field_name);
    const showError = hasError && isTouched;

    const baseInputClasses = `bg-slate-900 border text-slate-100 ${
      showError
        ? 'border-red-500 focus:border-red-400 focus:ring-red-500/20'
        : 'border-slate-700 focus:border-emerald-500 focus:ring-emerald-500/20'
    }`;

    switch (field.field_type) {
      case 'date':
        return (
          <div key={field.field_name} className="space-y-2">
            <Label htmlFor={fieldId} className="text-slate-300">
              {field.field_name}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            <Input
              id={fieldId}
              type="date"
              value={value}
              onChange={(e) => handleFieldChange(field.field_name, e.target.value)}
              onBlur={() => setTouchedFields((prev) => new Set(prev).add(field.field_name))}
              required={field.required}
              className={baseInputClasses}
            />
            {showError && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {fieldErrors[field.field_name]}
              </p>
            )}
            {!showError && field.help_text && (
              <p className="text-xs text-slate-400">{field.help_text}</p>
            )}
          </div>
        );

      case 'number':
        return (
          <div key={field.field_name} className="space-y-2">
            <Label htmlFor={fieldId} className="text-slate-300">
              {field.field_name}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            <Input
              id={fieldId}
              type="number"
              value={value}
              onChange={(e) => handleFieldChange(field.field_name, parseFloat(e.target.value) || 0)}
              onBlur={() => setTouchedFields((prev) => new Set(prev).add(field.field_name))}
              required={field.required}
              className={baseInputClasses}
            />
            {showError && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {fieldErrors[field.field_name]}
              </p>
            )}
            {!showError && field.help_text && (
              <p className="text-xs text-slate-400">{field.help_text}</p>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={field.field_name} className="space-y-2">
            <Label htmlFor={fieldId} className="text-slate-300">
              {field.field_name}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            <select
              id={fieldId}
              value={value}
              onChange={(e) => handleFieldChange(field.field_name, e.target.value)}
              onBlur={() => setTouchedFields((prev) => new Set(prev).add(field.field_name))}
              required={field.required}
              className={`w-full bg-slate-900 border rounded-md px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 ${
                showError
                  ? 'border-red-500 focus:border-red-400 focus:ring-red-500/20'
                  : 'border-slate-700 focus:border-emerald-500 focus:ring-emerald-500/20'
              }`}
            >
              <option value="">Select...</option>
              {field.validation_rules?.options?.map((opt: string) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            {showError && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {fieldErrors[field.field_name]}
              </p>
            )}
            {!showError && field.help_text && (
              <p className="text-xs text-slate-400">{field.help_text}</p>
            )}
          </div>
        );

      case 'file':
        return (
          <div key={field.field_name} className="space-y-2">
            <Label htmlFor={fieldId} className="text-slate-300">
              {field.field_name}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            <Input
              id={fieldId}
              type="file"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  handleFieldChange(field.field_name, file.name);
                }
              }}
              required={field.required}
              className="bg-slate-900 border-slate-700 text-slate-100"
            />
            {field.help_text && (
              <p className="text-xs text-slate-400">{field.help_text}</p>
            )}
          </div>
        );

      default:
        return (
          <div key={field.field_name} className="space-y-2">
            <Label htmlFor={fieldId} className="text-slate-300">
              {field.field_name}
              {field.required && <span className="text-red-400 ml-1">*</span>}
            </Label>
            <Input
              id={fieldId}
              type="text"
              value={value}
              onChange={(e) => handleFieldChange(field.field_name, e.target.value)}
              onBlur={() => setTouchedFields((prev) => new Set(prev).add(field.field_name))}
              required={field.required}
              className={baseInputClasses}
            />
            {showError && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {fieldErrors[field.field_name]}
              </p>
            )}
            {!showError && field.help_text && (
              <p className="text-xs text-slate-400">{field.help_text}</p>
            )}
          </div>
        );
    }
  };

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !formData) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!formData) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6 text-center text-slate-400">
          No form data available
        </CardContent>
      </Card>
    );
  }

  if (filingReference) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-emerald-400 mb-4">
            <CheckCircle className="h-5 w-5" />
            <span className="font-semibold">Filing Submitted Successfully</span>
          </div>
          <p className="text-slate-300 mb-2">
            Filing Reference: <span className="font-mono text-emerald-400">{filingReference}</span>
          </p>
          <p className="text-sm text-slate-400">
            Your filing has been tracked. You can view its status in the filing requirements panel.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-slate-100 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {formData.form_type} - {formData.authority}
            </CardTitle>
            <p className="text-sm text-slate-400 mt-1">
              {formData.jurisdiction} • Language: {formData.language}
            </p>
          </div>
          {formData.submission_url && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(formData.submission_url, '_blank')}
              className="text-slate-400 hover:text-slate-100"
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Open Portal
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/50 rounded-lg">
            <div className="flex items-center gap-2 text-red-400 mb-2">
              <AlertCircle className="h-4 w-4" />
              <span className="text-sm font-medium">{error}</span>
            </div>
            {validationErrors.length > 0 && (
              <ul className="list-disc list-inside text-xs text-red-300 mt-2 space-y-1">
                {validationErrors.map((err, idx) => (
                  <li key={idx}>{err}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {formData.instructions && (
          <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/50 rounded-lg">
            <p className="text-sm text-blue-400">{formData.instructions}</p>
          </div>
        )}

        <form className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {formData.fields.map((field) => renderField(field))}
          </div>

          {formData.document_references.length > 0 && (
            <div className="space-y-2">
              <Label className="text-slate-300">Attached Documents</Label>
              <div className="flex flex-wrap gap-2">
                {formData.document_references.map((docId, idx) => (
                  <Badge key={idx} variant="outline" className="text-slate-400">
                    Document {docId}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center gap-4 pt-4 border-t border-slate-700">
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark as Submitted
                </>
              )}
            </Button>
            <p className="text-xs text-slate-400">
              Note: This form is pre-filled. Submit via the official portal, then enter the reference number.
            </p>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
