import { useState, useEffect } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  FileText,
  ExternalLink,
  Loader2,
  CheckCircle,
  AlertCircle,
  Calendar,
  Building2,
  DollarSign,
  Globe
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
  };

  const validateForm = (): boolean => {
    if (!formData) return false;

    for (const field of formData.fields) {
      if (field.required && !formValues[field.field_name]) {
        setError(`Field "${field.field_name}" is required`);
        return false;
      }

      // Apply validation rules
      if (field.validation_rules) {
        const value = formValues[field.field_name];
        
        if (field.validation_rules.min_length && value.length < field.validation_rules.min_length) {
          setError(`Field "${field.field_name}" must be at least ${field.validation_rules.min_length} characters`);
          return false;
        }
        
        if (field.validation_rules.max_length && value.length > field.validation_rules.max_length) {
          setError(`Field "${field.field_name}" must be no more than ${field.validation_rules.max_length} characters`);
          return false;
        }
        
        if (field.validation_rules.pattern) {
          const regex = new RegExp(field.validation_rules.pattern);
          if (!regex.test(value)) {
            setError(`Field "${field.field_name}" format is invalid`);
            return false;
          }
        }
      }
    }

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
        throw new Error('Failed to update filing status');
      }

      setFilingReference(reference);
      if (onSubmitted) {
        onSubmitted(reference);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit filing');
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field: FilingFormField) => {
    const value = formValues[field.field_name] || '';
    const fieldId = `field-${field.field_name}`;

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
              required={field.required}
              className="bg-slate-900 border-slate-700 text-slate-100"
            />
            {field.help_text && (
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
              required={field.required}
              className="bg-slate-900 border-slate-700 text-slate-100"
            />
            {field.help_text && (
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
              required={field.required}
              className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">Select...</option>
              {field.validation_rules?.options?.map((opt: string) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            {field.help_text && (
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
              required={field.required}
              className="bg-slate-900 border-slate-700 text-slate-100"
            />
            {field.help_text && (
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
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-400">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">{error}</span>
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
