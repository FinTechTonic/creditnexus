/**
 * CDM Accordion Editor Component
 * 
 * Provides an accordion-based interface for editing CDM data with:
 * - Adaptive form fields based on data type
 * - Live JSON preview
 * - Direct JSON editing
 * - Split view (form + JSON)
 */

import { useState, useEffect } from 'react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
// import { Card, CardContent } from '@/components/ui/card'; // unused
import type { CreditAgreementData } from '@/context/FDC3Context';
import { Edit2, Save, X, AlertCircle } from 'lucide-react';
import { AiCdmOperations } from '@/components/AiCdmOperations';

interface CdmAccordionEditorProps {
  cdmData: CreditAgreementData;
  onUpdate: (updatedData: CreditAgreementData) => void;
  documentId?: number;
  className?: string;
  multimodalSources?: {
    audio?: { text?: string; cdm?: Record<string, unknown> };
    image?: { text?: string; cdm?: Record<string, unknown> };
    document?: { cdm?: Record<string, unknown>; documentId?: number };
    text?: { text: string; cdm?: Record<string, unknown> };
  };
}

interface AccordionSection {
  id: string;
  title: string;
  fields: EditableField[];
  expanded: boolean;
}

interface EditableField {
  path: string;
  label: string;
  type: 'string' | 'number' | 'date' | 'boolean' | 'array' | 'object';
  value: any;
}

// Utility function to get nested value from object using dot notation path
function getNestedValue(obj: any, path: string): any {
  const keys = path.split('.');
  let current = obj;
  for (const key of keys) {
    if (current === null || current === undefined) return undefined;
    // Handle array indices like "parties[0].name"
    const arrayMatch = key.match(/^(\w+)\[(\d+)\]$/);
    if (arrayMatch) {
      const [, arrayKey, index] = arrayMatch;
      current = current[arrayKey]?.[parseInt(index)];
    } else {
      current = current[key];
    }
  }
  return current;
}

// Utility function to set nested value in object using dot notation path
function setNestedValue(obj: any, path: string, value: any): any {
  const keys = path.split('.');
  const result = JSON.parse(JSON.stringify(obj)); // Deep clone
  let current = result;
  
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    const arrayMatch = key.match(/^(\w+)\[(\d+)\]$/);
    
    if (arrayMatch) {
      const [, arrayKey, index] = arrayMatch;
      if (!current[arrayKey]) current[arrayKey] = [];
      if (!current[arrayKey][parseInt(index)]) current[arrayKey][parseInt(index)] = {};
      current = current[arrayKey][parseInt(index)];
    } else {
      if (!current[key]) current[key] = {};
      current = current[key];
    }
  }
  
  const lastKey = keys[keys.length - 1];
  const lastArrayMatch = lastKey.match(/^(\w+)\[(\d+)\]$/);
  if (lastArrayMatch) {
    const [, arrayKey, index] = lastArrayMatch;
    if (!current[arrayKey]) current[arrayKey] = [];
    current[arrayKey][parseInt(index)] = value;
  } else {
    current[lastKey] = value;
  }
  
  return result;
}

export function CdmAccordionEditor({
  cdmData,
  onUpdate,
  documentId,
  className = '',
  multimodalSources
}: CdmAccordionEditorProps) {
  const [localCdmData, setLocalCdmData] = useState<CreditAgreementData>(cdmData);
  const [isEditingJson, setIsEditingJson] = useState(false);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [jsonEditValue, setJsonEditValue] = useState('');

  // Sync local data when prop changes
  useEffect(() => {
    setLocalCdmData(cdmData);
  }, [cdmData]);

  // Generate sections from CDM data structure
  const sections: AccordionSection[] = [
    {
      id: 'basic',
      title: 'Basic Information',
      fields: [
        { path: 'agreement_date', label: 'Agreement Date', type: 'date', value: localCdmData.agreement_date },
        { path: 'governing_law', label: 'Governing Law', type: 'string', value: localCdmData.governing_law },
        { path: 'deal_id', label: 'Deal ID', type: 'string', value: localCdmData.deal_id },
        { path: 'loan_identification_number', label: 'Loan Identification Number', type: 'string', value: localCdmData.loan_identification_number },
        { path: 'sustainability_linked', label: 'Sustainability Linked', type: 'boolean', value: localCdmData.sustainability_linked },
      ],
      expanded: true
    },
    {
      id: 'parties',
      title: 'Parties',
      fields: localCdmData.parties?.map((party, idx) => ({
        path: `parties[${idx}].name`,
        label: `${party.role} - Name`,
        type: 'string',
        value: party.name
      })) || [],
      expanded: false
    },
    {
      id: 'facilities',
      title: 'Facilities',
      fields: localCdmData.facilities?.flatMap((facility, idx) => [
        { path: `facilities[${idx}].facility_name`, label: 'Facility Name', type: 'string', value: facility.facility_name },
        { path: `facilities[${idx}].commitment_amount.amount`, label: 'Commitment Amount', type: 'number', value: facility.commitment_amount?.amount },
        { path: `facilities[${idx}].commitment_amount.currency`, label: 'Currency', type: 'string', value: facility.commitment_amount?.currency },
        { path: `facilities[${idx}].maturity_date`, label: 'Maturity Date', type: 'date', value: facility.maturity_date },
      ]) || [],
      expanded: false
    },
    {
      id: 'esg',
      title: 'ESG KPI Targets',
      fields: localCdmData.esg_kpi_targets?.map((kpi, idx) => ({
        path: `esg_kpi_targets[${idx}].kpi_type`,
        label: 'KPI Type',
        type: 'string',
        value: kpi.kpi_type
      })) || [],
      expanded: false
    }
  ];

  const handleFieldChange = (path: string, value: any) => {
    const updated = setNestedValue(localCdmData, path, value);
    setLocalCdmData(updated);
    onUpdate(updated);
  };

  const handleJsonEdit = () => {
    setJsonEditValue(JSON.stringify(localCdmData, null, 2));
    setIsEditingJson(true);
    setJsonError(null);
  };

  const handleJsonSave = () => {
    try {
      const parsed = JSON.parse(jsonEditValue);
      setLocalCdmData(parsed);
      onUpdate(parsed);
      setJsonError(null);
      setIsEditingJson(false);
    } catch (err) {
      setJsonError('Invalid JSON: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  const handleJsonCancel = () => {
    setIsEditingJson(false);
    setJsonError(null);
    setJsonEditValue('');
  };

  const renderField = (field: EditableField) => {
    const currentValue = getNestedValue(localCdmData, field.path);
    
    switch (field.type) {
      case 'string':
        return (
          <div key={field.path} className="space-y-1">
            <label className="text-sm text-slate-300">{field.label}</label>
            <Input
              value={currentValue || ''}
              onChange={(e) => handleFieldChange(field.path, e.target.value)}
              className="bg-slate-900 border-slate-600 text-white"
            />
          </div>
        );
      case 'number':
        return (
          <div key={field.path} className="space-y-1">
            <label className="text-sm text-slate-300">{field.label}</label>
            <Input
              type="number"
              value={currentValue || ''}
              onChange={(e) => handleFieldChange(field.path, parseFloat(e.target.value) || 0)}
              className="bg-slate-900 border-slate-600 text-white"
            />
          </div>
        );
      case 'date':
        return (
          <div key={field.path} className="space-y-1">
            <label className="text-sm text-slate-300">{field.label}</label>
            <Input
              type="date"
              value={currentValue || ''}
              onChange={(e) => handleFieldChange(field.path, e.target.value)}
              className="bg-slate-900 border-slate-600 text-white"
            />
          </div>
        );
      case 'boolean':
        return (
          <div key={field.path} className="flex items-center space-x-2">
            <Checkbox
              checked={currentValue || false}
              onCheckedChange={(checked) => handleFieldChange(field.path, checked)}
            />
            <label className="text-sm text-slate-300">{field.label}</label>
          </div>
        );
      default:
        return (
          <div key={field.path} className="space-y-1">
            <label className="text-sm text-slate-300">{field.label}</label>
            <Input
              value={JSON.stringify(currentValue) || ''}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  handleFieldChange(field.path, parsed);
                } catch {
                  // Invalid JSON, skip update
                }
              }}
              className="bg-slate-900 border-slate-600 text-white"
            />
          </div>
        );
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {multimodalSources && Object.keys(multimodalSources).length > 0 && (
        <div className="mb-4">
          <AiCdmOperations
            cdmData={localCdmData}
            multimodalSources={multimodalSources}
            onUpdate={(updated) => {
              setLocalCdmData(updated);
              onUpdate(updated);
            }}
            documentId={documentId}
          />
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        {/* Form Fields */}
        <div className="space-y-4">
          <Accordion type="multiple" className="w-full">
            {sections.map(section => (
              <AccordionItem key={section.id} value={section.id}>
                <AccordionTrigger className="text-slate-200">{section.title}</AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4 pt-2">
                    {section.fields.length > 0 ? (
                      section.fields.map(field => renderField(field))
                    ) : (
                      <p className="text-sm text-slate-400">No fields available</p>
                    )}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>

        {/* JSON View */}
        <div className="border-l border-slate-700 pl-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-slate-200">Raw JSON</h3>
            {!isEditingJson ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleJsonEdit}
                className="text-slate-400 hover:text-slate-200"
              >
                <Edit2 className="h-4 w-4 mr-1" />
                Edit
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleJsonSave}
                  className="text-emerald-400 hover:text-emerald-300"
                >
                  <Save className="h-4 w-4 mr-1" />
                  Save
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleJsonCancel}
                  className="text-slate-400 hover:text-slate-200"
                >
                  <X className="h-4 w-4 mr-1" />
                  Cancel
                </Button>
              </div>
            )}
          </div>
          
          {isEditingJson ? (
            <div className="space-y-2">
              <textarea
                value={jsonEditValue}
                onChange={(e) => setJsonEditValue(e.target.value)}
                className="w-full h-96 px-3 py-2 text-xs font-mono bg-slate-900 border border-slate-600 rounded-lg text-slate-300 resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500"
                spellCheck={false}
              />
              {jsonError && (
                <div className="flex items-center gap-2 text-sm text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  <span>{jsonError}</span>
                </div>
              )}
            </div>
          ) : (
            <pre className="text-xs font-mono bg-slate-900 p-4 rounded-lg overflow-auto max-h-96 text-slate-300 border border-slate-700">
              {JSON.stringify(localCdmData, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
