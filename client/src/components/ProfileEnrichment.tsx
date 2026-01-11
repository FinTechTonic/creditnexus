import { useState, useCallback, useEffect } from 'react';
import { Upload, FileText, X, Loader2, CheckCircle2, AlertCircle, User, Building2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { SignupFormApplicant } from './SignupFormApplicant';
import type { ApplicantFormData } from './SignupFormApplicant';
import { SignupFormBanker } from './SignupFormBanker';
import type { BankerFormData } from './SignupFormBanker';
import { SignupFormLawOfficer } from './SignupFormLawOfficer';
import type { LawOfficerFormData } from './SignupFormLawOfficer';
import { SignupFormAccountant } from './SignupFormAccountant';
import type { AccountantFormData } from './SignupFormAccountant';
import { fetchWithAuth } from '@/context/AuthContext';
import type { UserRole } from './SignupFlow';

interface ProfileEnrichmentProps {
  role: UserRole;
  formData: Record<string, any>;
  onChange: (data: Record<string, any>) => void;
  errors?: Record<string, string>;
}

type ExtractionStatus = 'idle' | 'extracting' | 'success' | 'error';

export function ProfileEnrichment({ role, formData, onChange, errors = {} }: ProfileEnrichmentProps) {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [extractionStatus, setExtractionStatus] = useState<ExtractionStatus>('idle');
  const [extractionProgress, setExtractionProgress] = useState(0);
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const [extractedProfileData, setExtractedProfileData] = useState<Record<string, any> | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const [fileInputRef, setFileInputRef] = useState<HTMLInputElement | null>(null);

  // Merge extracted data with form data when extraction completes
  useEffect(() => {
    if (extractedProfileData && extractionStatus === 'success') {
      // Merge extracted data into form data
      const mergedData = { ...formData, ...extractedProfileData };
      onChange(mergedData);
    }
  }, [extractedProfileData, extractionStatus, formData, onChange]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    setExtractionError(null);

    const files = Array.from(e.dataTransfer.files);
    const validFiles = files.filter(file => {
      const isImage = file.type.startsWith('image/') || /\.(png|jpg|jpeg|webp|gif|bmp|tiff)$/i.test(file.name);
      const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
      return isImage || isPdf;
    });

    if (validFiles.length === 0) {
      setExtractionError('No valid files found. Supported formats: PDF, PNG, JPEG, WEBP, GIF, BMP, TIFF');
      return;
    }

    setUploadedFiles(prev => [...prev, ...validFiles]);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const validFiles = Array.from(files).filter(file => {
        const isImage = file.type.startsWith('image/') || /\.(png|jpg|jpeg|webp|gif|bmp|tiff)$/i.test(file.name);
        const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
        return isImage || isPdf;
      });

      if (validFiles.length === 0) {
        setExtractionError('No valid files found. Supported formats: PDF, PNG, JPEG, WEBP, GIF, BMP, TIFF');
        return;
      }

      setUploadedFiles(prev => [...prev, ...validFiles]);
      setExtractionError(null);
    }
    
    // Reset input
    if (e.target) {
      e.target.value = '';
    }
  }, []);

  const removeFile = useCallback((index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
    setExtractionError(null);
    setExtractedProfileData(null);
    setExtractionStatus('idle');
  }, []);

  const extractProfileFromDocuments = useCallback(async () => {
    if (uploadedFiles.length === 0) {
      setExtractionError('Please upload at least one document');
      return;
    }

    setExtractionStatus('extracting');
    setExtractionProgress(0);
    setExtractionError(null);

    try {
      // Create FormData for file upload
      const formDataToSend = new FormData();
      uploadedFiles.forEach((file, index) => {
        formDataToSend.append('files', file);
      });
      formDataToSend.append('role', role);
      
      // If we have existing form data, include it for merging
      if (Object.keys(formData).length > 0) {
        formDataToSend.append('existing_profile', JSON.stringify(formData));
      }

      setExtractionProgress(30);

      // Call profile extraction endpoint
      const response = await fetchWithAuth('/api/profile/extract', {
        method: 'POST',
        body: formDataToSend,
      });

      setExtractionProgress(70);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Profile extraction failed' }));
        throw new Error(errorData.detail?.message || errorData.detail || errorData.message || 'Profile extraction failed');
      }

      const result = await response.json();
      setExtractionProgress(100);

      if (result.profile_data) {
        setExtractedProfileData(result.profile_data);
        setExtractionStatus('success');
        
        // Auto-merge after a short delay to show success state
        setTimeout(() => {
          const mergedData = { ...formData, ...result.profile_data };
          onChange(mergedData);
        }, 500);
      } else {
        throw new Error('No profile data extracted');
      }
    } catch (error) {
      setExtractionStatus('error');
      setExtractionError(error instanceof Error ? error.message : 'Profile extraction failed');
      setExtractionProgress(0);
    }
  }, [uploadedFiles, role, formData, onChange]);

  const renderRoleSpecificForm = () => {
    const commonProps = {
      formData: formData as any,
      onChange: (data: any) => onChange({ ...formData, ...data }),
      errors,
    };

    switch (role) {
      case 'applicant':
        return <SignupFormApplicant {...commonProps} formData={formData as Partial<ApplicantFormData>} />;
      case 'banker':
        return <SignupFormBanker {...commonProps} formData={formData as Partial<BankerFormData>} />;
      case 'law_officer':
        return <SignupFormLawOfficer {...commonProps} formData={formData as Partial<LawOfficerFormData>} />;
      case 'accountant':
        return <SignupFormAccountant {...commonProps} formData={formData as Partial<AccountantFormData>} />;
      default:
        return (
          <div className="text-center py-8 text-slate-400">
            <p>Profile form for role "{role}" will be available soon.</p>
          </div>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Document Upload Section */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <FileText className="h-5 w-5" />
          <h3 className="font-semibold">Upload Documents (Optional)</h3>
        </div>
        <p className="text-sm text-slate-400">
          Upload business cards, resumes, company documents, or ID documents to automatically extract profile information.
        </p>

        {/* File Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
            isDragOver
              ? 'border-emerald-500 bg-emerald-500/10'
              : 'border-slate-600 hover:border-slate-500'
          }`}
        >
          <Upload className={`h-12 w-12 mx-auto mb-4 ${isDragOver ? 'text-emerald-400' : 'text-slate-400'}`} />
          <p className="text-slate-300 mb-2">
            Drag and drop files here, or{' '}
            <button
              type="button"
              onClick={() => fileInputRef?.click()}
              className="text-emerald-400 hover:text-emerald-300 underline"
            >
              browse
            </button>
          </p>
          <p className="text-xs text-slate-500">
            Supports PDF, PNG, JPEG, WEBP, GIF, BMP, TIFF
          </p>
          <input
            ref={setFileInputRef}
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.bmp,.tiff"
            onChange={handleFileInput}
            className="hidden"
          />
        </div>

        {/* Uploaded Files List */}
        {uploadedFiles.length > 0 && (
          <div className="space-y-2">
            {uploadedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-slate-800 rounded-lg border border-slate-700"
              >
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-slate-400" />
                  <div>
                    <p className="text-sm text-slate-200">{file.name}</p>
                    <p className="text-xs text-slate-500">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="text-slate-400 hover:text-red-400 transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Extract Profile Button */}
        {uploadedFiles.length > 0 && (
          <div className="space-y-3">
            <Button
              type="button"
              onClick={extractProfileFromDocuments}
              disabled={extractionStatus === 'extracting'}
              className="w-full"
            >
              {extractionStatus === 'extracting' ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Extracting Profile Data...
                </>
              ) : (
                <>
                  <User className="h-4 w-4 mr-2" />
                  Extract Profile from Documents
                </>
              )}
            </Button>

            {/* Extraction Progress */}
            {extractionStatus === 'extracting' && (
              <div className="space-y-2">
                <Progress value={extractionProgress} className="h-2" />
                <p className="text-xs text-center text-slate-400">
                  Processing documents... {extractionProgress}%
                </p>
              </div>
            )}

            {/* Extraction Success */}
            {extractionStatus === 'success' && (
              <div className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-emerald-400">Profile data extracted successfully!</p>
                  <p className="text-xs text-slate-400 mt-1">
                    The extracted information has been merged with your form. Please review and edit as needed.
                  </p>
                </div>
              </div>
            )}

            {/* Extraction Error */}
            {extractionStatus === 'error' && extractionError && (
              <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-400">Extraction Failed</p>
                  <p className="text-xs text-red-300 mt-1">{extractionError}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Role-Specific Form */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <Building2 className="h-5 w-5" />
          <h3 className="font-semibold">Profile Information</h3>
        </div>
        <p className="text-sm text-slate-400">
          Complete your profile information. Fields can be auto-filled from uploaded documents above.
        </p>
        {renderRoleSpecificForm()}
      </div>
    </div>
  );
}
