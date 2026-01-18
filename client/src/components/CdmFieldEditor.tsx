/**
 * CDM Field Editor Component
 * 
 * Allows editing nested CDM fields with a user-friendly interface.
 * Supports editing parties, facilities, dates, amounts, and other CDM fields.
 */

import { useState, useEffect } from 'react'; // useCallback removed - unused
import { fetchWithAuth } from '@/context/AuthContext';
import {
  Edit2,
  Save,
  X,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  FileText,
  Users,
  Briefcase
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
// import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'; // unused
import type { CreditAgreementData } from '@/context/FDC3Context';

interface CdmFieldEditorProps {
  documentId: number;
  cdmData: CreditAgreementData;
  onUpdate?: (updatedCdmData: CreditAgreementData) => void;
  className?: string;
}

// interface EditableField { // Commented out - unused
//   path: string;
//   label: string;
//   value: any;
//   type: 'string' | 'number' | 'date' | 'boolean' | 'object' | 'array';
//   editable: boolean;
// }

export function CdmFieldEditor({
  documentId,
  cdmData,
  onUpdate,
  className = '',
}: CdmFieldEditorProps) {
  const [localCdmData, setLocalCdmData] = useState<CreditAgreementData>(cdmData);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<any>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['parties', 'facilities']));

  useEffect(() => {
    setLocalCdmData(cdmData);
  }, [cdmData]);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const handleEdit = (path: string, currentValue: any) => {
    setEditingField(path);
    setEditValue(currentValue);
    setError(null);
    setSuccess(null);
  };

  const handleSave = async () => {
    if (editingField === null) return;

    try {
      setIsSaving(true);
      setError(null);
      setSuccess(null);

      const response = await fetchWithAuth(`/api/documents/${documentId}/cdm-fields`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          field_path: editingField,
          value: editValue,
          update_version: false,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.message || 'Failed to update field');
      }

      const data = await response.json();
      
      // Update local state
      setLocalCdmData(data.cdm_data as CreditAgreementData);
      
      // Notify parent
      if (onUpdate) {
        onUpdate(data.cdm_data as CreditAgreementData);
      }

      setSuccess(`Field updated successfully`);
      setEditingField(null);
      setEditValue(null);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update field');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setEditingField(null);
    setEditValue(null);
    setError(null);
  };

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    return String(value);
  };

  const renderField = (
    label: string,
    path: string,
    value: any,
    type: 'string' | 'number' | 'date' | 'boolean' | 'object' | 'array' = 'string'
  ) => {
    const isEditing = editingField === path;
    const displayValue = formatValue(value);

    return (
      <div key={path} className="flex items-center justify-between p-2 hover:bg-slate-700/30 rounded-lg group">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-slate-300">{label}</div>
          {isEditing ? (
            <div className="mt-1 space-y-2">
              {type === 'boolean' ? (
                <select
                  value={editValue ? 'true' : 'false'}
                  onChange={(e) => setEditValue(e.target.value === 'true')}
                  className="w-full px-2 py-1 bg-slate-900/50 border border-slate-700 rounded text-white text-sm"
                >
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              ) : type === 'date' ? (
                <Input
                  type="date"
                  value={editValue || ''}
                  onChange={(e) => setEditValue(e.target.value)}
                  className="bg-slate-900/50 border-slate-700 text-white"
                />
              ) : type === 'number' ? (
                <Input
                  type="number"
                  value={editValue || ''}
                  onChange={(e) => setEditValue(type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)}
                  className="bg-slate-900/50 border-slate-700 text-white"
                />
              ) : (
                <Input
                  value={editValue || ''}
                  onChange={(e) => setEditValue(e.target.value)}
                  className="bg-slate-900/50 border-slate-700 text-white"
                />
              )}
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={isSaving}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-3 w-3 mr-1" />
                      Save
                    </>
                  )}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleCancel}
                  className="text-slate-400 hover:text-white"
                >
                  <X className="h-3 w-3 mr-1" />
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-400 mt-0.5 truncate">{displayValue}</div>
          )}
        </div>
        {!isEditing && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEdit(path, value)}
            className="opacity-0 group-hover:opacity-100 transition-opacity h-7 w-7 p-0 text-slate-400 hover:text-emerald-400"
            title="Edit field"
          >
            <Edit2 className="h-3 w-3" />
          </Button>
        )}
      </div>
    );
  };

  return (
    <div className={className}>
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-lg font-medium text-white flex items-center gap-2">
            <FileText className="h-5 w-5 text-emerald-400" />
            Edit CDM Fields
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Status Messages */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}
          {success && (
            <div className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 text-sm">
              <CheckCircle2 className="h-4 w-4" />
              {success}
            </div>
          )}

          {/* Agreement-Level Fields */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Agreement Details
            </h3>
            {renderField('Agreement Date', 'agreement_date', localCdmData.agreement_date, 'date')}
            {renderField('Governing Law', 'governing_law', localCdmData.governing_law)}
            {renderField('Sustainability Linked', 'sustainability_linked', localCdmData.sustainability_linked, 'boolean')}
          </div>

          {/* Parties Section */}
          <div className="space-y-2">
            <button
              onClick={() => toggleSection('parties')}
              className="w-full flex items-center justify-between p-2 hover:bg-slate-700/30 rounded-lg"
            >
              <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <Users className="h-4 w-4" />
                Parties ({localCdmData.parties?.length || 0})
              </h3>
              {expandedSections.has('parties') ? (
                <ChevronDown className="h-4 w-4 text-slate-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-slate-400" />
              )}
            </button>
            {expandedSections.has('parties') && localCdmData.parties && (
              <div className="ml-4 space-y-2 border-l border-slate-700 pl-4">
                {localCdmData.parties.map((party, index) => (
                  <div key={index} className="space-y-1">
                    <div className="text-xs text-slate-500 font-medium">Party {index + 1}</div>
                    {renderField('Name', `parties[${index}].name`, party.name)}
                    {renderField('Role', `parties[${index}].role`, party.role)}
                    {renderField('LEI', `parties[${index}].lei`, party.lei)}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Facilities Section */}
          <div className="space-y-2">
            <button
              onClick={() => toggleSection('facilities')}
              className="w-full flex items-center justify-between p-2 hover:bg-slate-700/30 rounded-lg"
            >
              <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <Briefcase className="h-4 w-4" />
                Facilities ({localCdmData.facilities?.length || 0})
              </h3>
              {expandedSections.has('facilities') ? (
                <ChevronDown className="h-4 w-4 text-slate-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-slate-400" />
              )}
            </button>
            {expandedSections.has('facilities') && localCdmData.facilities && (
              <div className="ml-4 space-y-4 border-l border-slate-700 pl-4">
                {localCdmData.facilities.map((facility, index) => (
                  <div key={index} className="space-y-2">
                    <div className="text-xs text-slate-500 font-medium">Facility {index + 1}</div>
                    {renderField('Facility Name', `facilities[${index}].facility_name`, facility.facility_name)}
                    {renderField('Maturity Date', `facilities[${index}].maturity_date`, facility.maturity_date, 'date')}
                    {facility.commitment_amount && (
                      <>
                        {renderField('Commitment Amount', `facilities[${index}].commitment_amount.amount`, facility.commitment_amount.amount, 'number')}
                        {renderField('Currency', `facilities[${index}].commitment_amount.currency`, facility.commitment_amount.currency)}
                      </>
                    )}
                    {facility.interest_terms?.rate_option && (
                      <>
                        {renderField('Benchmark', `facilities[${index}].interest_terms.rate_option.benchmark`, facility.interest_terms.rate_option.benchmark)}
                        {renderField('Spread (bps)', `facilities[${index}].interest_terms.rate_option.spread_bps`, facility.interest_terms.rate_option.spread_bps, 'number')}
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
