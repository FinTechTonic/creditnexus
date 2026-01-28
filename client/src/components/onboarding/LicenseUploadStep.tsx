import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Loader2, Upload, CheckCircle2, Shield, AlertCircle, FileText } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import type { UserRole } from '@/components/SignupFlow';

interface LicenseRequirement {
  type: string;
  category: string;
  label: string;
  description: string;
}

const ROLE_REQUIREMENTS: Record<string, LicenseRequirement[]> = {
  banker: [
    {
      type: 'professional_license',
      category: 'banking',
      label: 'Banking Practitioner License',
      description: 'Regulatory license for banking operations',
    }
  ],
  law_officer: [
    {
      type: 'professional_license',
      category: 'legal',
      label: 'Bar Admission / Legal License',
      description: 'Proof of admission to the bar or equivalent legal authority',
    }
  ],
  accountant: [
    {
      type: 'professional_license',
      category: 'accounting',
      label: 'CPA / Chartered Accountant Certification',
      description: 'Professional accounting certification',
    }
  ],
  applicant: [], // Usually no license required for basic applicant
  admin: [],
};

interface LicenseUploadStepProps {
  role: UserRole;
  onComplete: (data: any) => void;
}

export function LicenseUploadStep({ role, onComplete }: LicenseUploadStepProps) {
  const [requirements, setRequirements] = useState<LicenseRequirement[]>([]);
  const [uploading, setUploading] = useState<string | null>(null);
  const [licenses, setLicenses] = useState<Record<string, any>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRequirements(ROLE_REQUIREMENTS[role] || []);
  }, [role]);

  const handleFileUpload = async (requirement: LicenseRequirement, file: File) => {
    setUploading(requirement.category);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('license_type', requirement.type);
    formData.append('license_category', requirement.category);

    try {
      const response = await fetchWithAuth('/api/kyc/licenses/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setLicenses((prev) => ({
          ...prev,
          [requirement.category]: data.license,
        }));
      } else {
        const errData = await response.json();
        setError(errData.detail || 'Failed to upload license');
      }
    } catch (err) {
      console.error('License upload error:', err);
      setError('An error occurred during upload');
    } finally {
      setUploading(null);
    }
  };

  const isComplete = requirements.every((req) => !!licenses[req.category]);

  if (requirements.length === 0) {
    return (
      <div className="space-y-6 text-center py-8">
        <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
          <Shield className="h-8 w-8 text-emerald-500" />
        </div>
        <h3 className="text-xl font-semibold text-slate-100">No Licenses Required</h3>
        <p className="text-slate-400 max-w-md mx-auto">
          Based on your role as <span className="capitalize">{role.replace('_', ' ')}</span>, no additional professional licenses are required at this stage.
        </p>
        <Button onClick={() => onComplete({ skipped: true })} className="mt-4">
          Continue to Review
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <h3 className="text-xl font-semibold text-slate-100 mb-2">
          Professional Licenses
        </h3>
        <p className="text-slate-400">
          Upload required professional certifications for your role
        </p>
      </div>

      <div className="space-y-4">
        {requirements.map((req) => {
          const license = licenses[req.category];
          const isUploading = uploading === req.category;

          return (
            <Card key={req.category} className={license ? 'border-emerald-500/50 bg-emerald-500/5' : ''}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${license ? 'bg-emerald-500/20' : 'bg-slate-800'}`}>
                      <FileText className={`h-5 w-5 ${license ? 'text-emerald-500' : 'text-slate-400'}`} />
                    </div>
                    <div>
                      <CardTitle className="text-base">{req.label}</CardTitle>
                      <CardDescription>{req.description}</CardDescription>
                    </div>
                  </div>
                  {license && (
                    <Badge variant="outline" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/50">
                      <CheckCircle2 className="h-3 w-3 mr-1" /> Verified
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {!license ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-center border-2 border-dashed border-slate-700 rounded-lg p-8 hover:border-slate-500 transition-colors">
                      <div className="text-center">
                        <Upload className="h-8 w-8 text-slate-500 mx-auto mb-2" />
                        <p className="text-sm text-slate-400 mb-4">
                          Click to upload or drag and drop (PDF, PNG, JPG)
                        </p>
                        <input
                          type="file"
                          id={`file-${req.category}`}
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleFileUpload(req, file);
                          }}
                          accept=".pdf,.png,.jpg,.jpeg"
                        />
                        <Button
                          variant="outline"
                          onClick={() => document.getElementById(`file-${req.category}`)?.click()}
                          disabled={isUploading}
                        >
                          {isUploading ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin mr-2" />
                              Uploading...
                            </>
                          ) : (
                            'Select File'
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <FileText className="h-4 w-4 text-slate-400 flex-shrink-0" />
                      <span className="text-sm text-slate-300 truncate">
                        License Number: {license.license_number}
                      </span>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => {
                        const newLicenses = { ...licenses };
                        delete newLicenses[req.category];
                        setLicenses(newLicenses);
                      }}
                    >
                      Change
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      <Button
        className="w-full"
        onClick={() => onComplete(licenses)}
        disabled={!isComplete}
      >
        Continue to Review
      </Button>
    </div>
  );
}
