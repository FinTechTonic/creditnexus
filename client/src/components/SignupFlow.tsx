import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, fetchWithAuth } from '@/context/AuthContext';
import { resolveApiUrl } from '@/utils/apiBase';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ProfileEnrichment } from '@/components/ProfileEnrichment';
import { MultimodalInputTabs } from '@/apps/docu-digitizer/MultimodalInputTabs';
import { KYCVerificationStep } from '@/components/onboarding/KYCVerificationStep';
import { LicenseUploadStep } from '@/components/onboarding/LicenseUploadStep';
import { ConsentCollectionStep } from '@/components/onboarding/ConsentCollectionStep';
import { 
  ArrowLeft, 
  ArrowRight, 
  CheckCircle2, 
  // User, FileText removed - unused
  Eye,
  Loader2,
  AlertCircle
} from 'lucide-react';

export type UserRole = 'applicant' | 'banker' | 'law_officer' | 'accountant' | 'analyst' | 'admin';

interface SignupFormData {
  // Step 1: Basic Info
  email: string;
  password: string;
  confirmPassword: string;
  displayName: string;
  role: UserRole | null;
  organizationId: number | null;
  implementationIds: number[];

  // Profile Enrichment (will be populated by ProfileEnrichment component)
  profileData: Record<string, any>;

  // Documents
  documents: File[];
}

interface SignupFlowProps {
  onComplete?: () => void;
  onCancel?: () => void;
}

const STEPS = [
  { id: 0, title: 'AI Profile Extraction', description: 'Extract profile data using AI' },
  { id: 1, title: 'Basic Information', description: 'Email, password, and role selection' },
  { id: 2, title: 'Organization', description: 'Select your organization' },
  { id: 3, title: 'Implementations', description: 'Connect to services (optional)' },
  { id: 4, title: 'Profile Enrichment', description: 'Complete your profile information' },
  { id: 5, title: 'Identity Verification', description: 'Complete KYC requirements' },
  { id: 6, title: 'Professional Licenses', description: 'Upload role-specific certifications' },
  { id: 7, title: 'Privacy & Consent', description: 'Review privacy policy and provide consent' },
  { id: 8, title: 'Review & Submit', description: 'Review your information and complete signup' },
];

function OrganizationSelectionStep({
  formData,
  updateFormData,
}: {
  formData: SignupFormData;
  updateFormData: (u: Partial<SignupFormData>) => void;
}) {
  const [choices, setChoices] = useState<{ id: number; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [createNew, setCreateNew] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [creatingOrg, setCreatingOrg] = useState(false);
  
  useEffect(() => {
    fetch(resolveApiUrl('/api/organizations/signup-choices'))
      .then((r) => (r.ok ? r.json() : []))
      .then(setChoices)
      .catch(() => setChoices([]))
      .finally(() => setLoading(false));
  }, []);
  
  const filteredChoices = choices.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  const handleCreateOrganization = async () => {
    if (!newOrgName.trim()) {
      return;
    }
    
    setCreatingOrg(true);
    try {
      const response = await fetch(resolveApiUrl('/api/organizations/signup'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newOrgName.trim(), is_active: false }),
      });
      
      if (response.ok) {
        const org = await response.json();
        updateFormData({ organizationId: org.id });
        setCreateNew(false);
        setNewOrgName('');
      } else {
        const error = await response.json().catch(() => ({ detail: 'Failed to create organization' }));
        alert(error.detail || 'Failed to create organization');
      }
    } catch (err) {
      alert('Failed to create organization');
    } finally {
      setCreatingOrg(false);
    }
  };
  
  return (
    <div className="space-y-6">
      <p className="text-slate-400">Select your organization or create a new one (required).</p>
      
      <div className="flex gap-2 mb-4">
        <button
          type="button"
          onClick={() => {
            setCreateNew(false);
            updateFormData({ organizationId: null });
          }}
          className={`flex-1 px-4 py-2 rounded-lg border transition-colors ${
            !createNew
              ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
              : 'bg-slate-900 border-slate-600 text-slate-300 hover:border-slate-500'
          }`}
        >
          Select Existing
        </button>
        <button
          type="button"
          onClick={() => {
            setCreateNew(true);
            updateFormData({ organizationId: null });
          }}
          className={`flex-1 px-4 py-2 rounded-lg border transition-colors ${
            createNew
              ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
              : 'bg-slate-900 border-slate-600 text-slate-300 hover:border-slate-500'
          }`}
        >
          Create New
        </button>
      </div>
      
      {!createNew ? (
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Organization <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search organizations..."
            className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white mb-3 focus:outline-none focus:ring-2 focus:ring-emerald-500 placeholder-slate-500"
          />
          <select
            value={formData.organizationId ?? ''}
            onChange={(e) => updateFormData({ organizationId: e.target.value === '' ? null : Number(e.target.value) })}
            className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            disabled={loading}
            required
          >
            <option value="">Select an organization...</option>
            {filteredChoices.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          {!formData.organizationId && (
            <p className="mt-1 text-sm text-red-400">Organization selection is required</p>
          )}
        </div>
      ) : (
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Organization Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={newOrgName}
            onChange={(e) => setNewOrgName(e.target.value)}
            placeholder="Enter organization name..."
            className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white mb-3 focus:outline-none focus:ring-2 focus:ring-emerald-500 placeholder-slate-500"
            disabled={creatingOrg}
          />
          <button
            type="button"
            onClick={handleCreateOrganization}
            disabled={!newOrgName.trim() || creatingOrg}
            className="w-full px-4 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg text-white font-medium transition-colors"
          >
            {creatingOrg ? 'Creating...' : 'Create Organization'}
          </button>
          <p className="mt-2 text-xs text-slate-500">
            New organizations require admin approval before activation.
          </p>
        </div>
      )}
    </div>
  );
}

function ImplementationSelectionStep({
  formData,
  updateFormData,
}: {
  formData: SignupFormData;
  updateFormData: (u: Partial<SignupFormData>) => void;
}) {
  const [implementations, setImplementations] = useState<{
    id: number;
    name: string;
    display_name: string;
    category: string;
  }[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetch(resolveApiUrl('/api/implementations/signup-choices'))
      .then((r) => (r.ok ? r.json() : []))
      .then(setImplementations)
      .catch(() => setImplementations([]))
      .finally(() => setLoading(false));
  }, []);
  
  const toggleImplementation = (implId: number) => {
    const current = formData.implementationIds || [];
    const updated = current.includes(implId)
      ? current.filter(id => id !== implId)
      : [...current, implId];
    updateFormData({ implementationIds: updated });
  };
  
  return (
    <div className="space-y-6">
      <p className="text-slate-400">
        Optionally connect to verified implementations for enhanced features.
      </p>
      {loading ? (
        <div className="text-center py-8">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-slate-400" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {implementations.map((impl) => (
            <button
              key={impl.id}
              type="button"
              onClick={() => toggleImplementation(impl.id)}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                (formData.implementationIds || []).includes(impl.id)
                  ? 'border-emerald-500 bg-emerald-500/10'
                  : 'border-slate-600 hover:border-slate-500'
              }`}
            >
              <div className="font-medium text-slate-100">{impl.display_name}</div>
              <div className="text-xs text-slate-400 mt-1 capitalize">{impl.category}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function SignupFlow({ onComplete, onCancel }: SignupFlowProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<SignupFormData>({
    email: '',
    password: '',
    confirmPassword: '',
    displayName: '',
    role: null,
    organizationId: null,
    implementationIds: [],
    profileData: {},
    documents: [],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  
  const navigate = useNavigate();
  const { register, authError, clearError } = useAuth();

  const validateStep1 = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    // Only validate format, not presence - make validation optional
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }
    
    if (formData.password) {
      if (formData.password.length < 12) {
        newErrors.password = 'Password must be at least 12 characters';
      } else if (!/(?=.*[A-Z])/.test(formData.password)) {
        newErrors.password = 'Password must contain at least one uppercase letter';
      } else if (!/(?=.*[a-z])/.test(formData.password)) {
        newErrors.password = 'Password must contain at least one lowercase letter';
      } else if (!/(?=.*\d)/.test(formData.password)) {
        newErrors.password = 'Password must contain at least one number';
      } else if (!/(?=.*[!@#$%^&*(),.?":{}|<>])/.test(formData.password)) {
        newErrors.password = 'Password must contain at least one special character';
      }
    }
    
    if (formData.password && formData.confirmPassword && formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    
    // No required field validation - all fields are optional
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    // Remove validation requirement for navigation - allow navigation regardless
    // Only validate format if fields are filled
    if (currentStep === 1) {
      validateStep1(); // Validate format but don't block navigation
    }
    
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
      clearError();
    }
  };

  const handleStepClick = (stepId: number) => {
    // Allow clicking on any step to navigate
    if (stepId >= 0 && stepId < STEPS.length) {
      setCurrentStep(stepId);
      clearError();
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
      clearError();
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    clearError();
    
    try {
      // Register user with basic info
      const success = await register({
        email: formData.email,
        password: formData.password,
        display_name: formData.displayName,
        organization_id: formData.organizationId ?? undefined,
        implementation_ids: formData.implementationIds?.length ? formData.implementationIds : undefined,
      });
      
      if (success) {
        // TODO: In next tasks, we'll:
        // 1. Upload documents and extract profile data
        // 2. Update user profile with extracted data
        // 3. Index profile in ChromaDB
        
        if (onComplete) {
          onComplete();
        } else {
          navigate('/dashboard', { replace: true });
        }
      }
    } catch (error) {
      console.error('Signup error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateFormData = (updates: Partial<SignupFormData>) => {
    setFormData(prev => ({ ...prev, ...updates }));
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <h3 className="text-xl font-semibold text-slate-100 mb-2">
                Extract Your Profile Using AI
              </h3>
              <p className="text-slate-400">
                Use audio, images, documents, or text to automatically extract your profile information
              </p>
            </div>
            <MultimodalInputTabs
              onAudioComplete={async (result) => {
                if (result.transcription) {
                  try {
                    const response = await fetchWithAuth('/api/profile/extract', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        text: result.transcription,
                        role: formData.role || null,
                        source_type: 'audio',
                      }),
                    });
                    if (response.ok) {
                      const profileData = await response.json();
                      updateFormData({ profileData: profileData.profile || {} });
                    }
                  } catch (err) {
                    console.error('Profile extraction error:', err);
                  }
                }
              }}
              onImageComplete={async (result) => {
                if (result.ocr_text) {
                  try {
                    const response = await fetchWithAuth('/api/profile/extract', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        text: result.ocr_text,
                        role: formData.role || null,
                        source_type: 'image',
                      }),
                    });
                    if (response.ok) {
                      const profileData = await response.json();
                      updateFormData({ profileData: profileData.profile || {} });
                    }
                  } catch (err) {
                    console.error('Profile extraction error:', err);
                  }
                }
              }}
              onDocumentSelect={async (doc) => {
                if (doc.cdm_data) {
                  try {
                    const response = await fetchWithAuth('/api/profile/extract', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        text: JSON.stringify(doc.cdm_data),
                        role: formData.role || null,
                        source_type: 'document',
                      }),
                    });
                    if (response.ok) {
                      const profileData = await response.json();
                      updateFormData({ profileData: profileData.profile || {} });
                    }
                  } catch (err) {
                    console.error('Profile extraction error:', err);
                  }
                }
              }}
              onTextInput={async (text) => {
                if (text) {
                  try {
                    const response = await fetchWithAuth('/api/profile/extract', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        text: text,
                        role: formData.role || null,
                        source_type: 'text',
                      }),
                    });
                    if (response.ok) {
                      const profileData = await response.json();
                      updateFormData({ profileData: profileData.profile || {} });
                    }
                  } catch (err) {
                    console.error('Profile extraction error:', err);
                  }
                }
              }}
              onError={(error) => {
                setErrors({ aiExtraction: error });
              }}
            />
            {errors.aiExtraction && (
              <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg">
                <p className="text-sm text-red-400">{errors.aiExtraction}</p>
              </div>
            )}
          </div>
        );
      case 1:
        return (
          <div className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
                Email Address *
              </label>
              <input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => updateFormData({ email: e.target.value })}
                className={`w-full px-4 py-3 bg-slate-900 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
                  errors.email ? 'border-red-500' : 'border-slate-600'
                }`}
                placeholder="you@example.com"
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-400">{errors.email}</p>
              )}
            </div>

            <div>
              <label htmlFor="displayName" className="block text-sm font-medium text-slate-300 mb-2">
                Display Name *
              </label>
              <input
                id="displayName"
                type="text"
                value={formData.displayName}
                onChange={(e) => updateFormData({ displayName: e.target.value })}
                className={`w-full px-4 py-3 bg-slate-900 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
                  errors.displayName ? 'border-red-500' : 'border-slate-600'
                }`}
                placeholder="John Smith"
              />
              {errors.displayName && (
                <p className="mt-1 text-sm text-red-400">{errors.displayName}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
                Password *
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => updateFormData({ password: e.target.value })}
                  className={`w-full px-4 py-3 bg-slate-900 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 pr-10 ${
                    errors.password ? 'border-red-500' : 'border-slate-600'
                  }`}
                  placeholder="Enter a strong password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-300"
                >
                  <Eye className="h-5 w-5" />
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-sm text-red-400">{errors.password}</p>
              )}
              <p className="mt-1 text-xs text-slate-400">
                Must be at least 12 characters with uppercase, lowercase, number, and special character
              </p>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-2">
                Confirm Password *
              </label>
              <input
                id="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                value={formData.confirmPassword}
                onChange={(e) => updateFormData({ confirmPassword: e.target.value })}
                className={`w-full px-4 py-3 bg-slate-900 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
                  errors.confirmPassword ? 'border-red-500' : 'border-slate-600'
                }`}
                placeholder="Confirm your password"
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-red-400">{errors.confirmPassword}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Select Your Role *
              </label>
              <div className="grid grid-cols-2 gap-3">
                {(['applicant', 'banker', 'law_officer', 'accountant'] as UserRole[]).map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => updateFormData({ role })}
                    className={`p-4 border-2 rounded-lg text-left transition-all ${
                      formData.role === role
                        ? 'border-emerald-500 bg-emerald-500/10'
                        : 'border-slate-600 hover:border-slate-500'
                    }`}
                  >
                    <div className="font-medium text-slate-100 capitalize">
                      {role.replace('_', ' ')}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      {role === 'applicant' && 'Apply for loans and credit facilities'}
                      {role === 'banker' && 'Manage loans and credit agreements'}
                      {role === 'law_officer' && 'Legal review and compliance'}
                      {role === 'accountant' && 'Financial analysis and auditing'}
                    </div>
                  </button>
                ))}
              </div>
              {errors.role && (
                <p className="mt-1 text-sm text-red-400">{errors.role}</p>
              )}
            </div>
          </div>
        );

      case 2:
        return <OrganizationSelectionStep formData={formData} updateFormData={updateFormData} />;

      case 3:
        return <ImplementationSelectionStep formData={formData} updateFormData={updateFormData} />;

      case 4:
        return (
          <div className="space-y-6">
            {formData.role ? (
              <ProfileEnrichment
                role={formData.role}
                formData={formData.profileData || {}}
                onChange={(data) => updateFormData({ profileData: data })}
                errors={errors}
              />
            ) : (
              <div className="text-center py-8">
                <p className="text-slate-400">Please select a role in Step 1 first.</p>
              </div>
            )}
          </div>
        );

      case 5:
        return (
          <KYCVerificationStep
            role={formData.role || 'applicant'}
            onComplete={(data) => {
              console.log('KYC Completed:', data);
              handleNext();
            }}
          />
        );

      case 6:
        return (
          <LicenseUploadStep
            role={formData.role || 'applicant'}
            onComplete={(data) => {
              console.log('Licenses Completed:', data);
              handleNext();
            }}
          />
        );

      case 7:
        return (
          <ConsentCollectionStep
            onConsentChange={async (consents) => {
              // Record consents via API
              try {
                for (const [consentType, given] of Object.entries(consents)) {
                  if (consentType !== 'essential') {
                    const consentConfig = {
                      essential: { purpose: 'Required for account functionality', basis: 'contract' },
                      analytics: { purpose: 'Improving application performance and UX', basis: 'consent' },
                      marketing: { purpose: 'Sending newsletters and product updates', basis: 'consent' },
                      third_party: { purpose: 'Sharing non-essential data with partners', basis: 'consent' }
                    };
                    
                    const config = consentConfig[consentType as keyof typeof consentConfig];
                    if (config) {
                      await fetchWithAuth('/api/gdpr/consents', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          consent_type: consentType,
                          consent_purpose: config.purpose,
                          legal_basis: config.basis,
                          consent_given: given,
                          consent_source: 'signup'
                        })
                      });
                    }
                  }
                }
                handleNext();
              } catch (e) {
                console.error('Failed to record consents:', e);
                // Non-blocking - continue anyway
                handleNext();
              }
            }}
          />
        );

      case 8:
        return (
          <div className="space-y-6">
            <div className="bg-slate-800/50 rounded-lg p-6 space-y-4">
              <h3 className="text-lg font-semibold text-slate-100 mb-4">Review Your Information</h3>
              
              <div className="space-y-3">
                <div>
                  <span className="text-sm text-slate-400">Email:</span>
                  <p className="text-slate-100">{formData.email}</p>
                </div>
                <div>
                  <span className="text-sm text-slate-400">Display Name:</span>
                  <p className="text-slate-100">{formData.displayName}</p>
                </div>
                <div>
                  <span className="text-sm text-slate-400">Role:</span>
                  <p className="text-slate-100 capitalize">{formData.role?.replace('_', ' ')}</p>
                </div>
                {formData.organizationId && (
                  <div>
                    <span className="text-sm text-slate-400">Organization:</span>
                    <p className="text-slate-100">Selected (ID: {formData.organizationId})</p>
                  </div>
                )}
                {formData.implementationIds && formData.implementationIds.length > 0 && (
                  <div>
                    <span className="text-sm text-slate-400">Implementations:</span>
                    <p className="text-slate-100">{formData.implementationIds.length} selected</p>
                  </div>
                )}
              </div>
            </div>
            
            {authError && (
              <div className="bg-red-500/10 border border-red-500 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-400">Error</p>
                  <p className="text-sm text-red-300 mt-1">{authError}</p>
                </div>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  const progress = (currentStep / (STEPS.length - 1)) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center py-12 px-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <div className="flex items-center justify-between mb-4">
            <CardTitle className="text-2xl">Create Your Account</CardTitle>
            {onCancel && (
              <button
                onClick={onCancel}
                className="text-slate-400 hover:text-slate-300"
              >
                Cancel
              </button>
            )}
          </div>
          
          <div className="space-y-4">
            <Progress value={progress} className="h-2" />
            <div className="flex items-center justify-between text-sm">
              {STEPS.map((step, _index) => ( // Prefix with _ - unused
                <div
                  key={step.id}
                  onClick={() => handleStepClick(step.id)}
                  className={`flex items-center gap-2 cursor-pointer transition-colors ${
                    currentStep >= step.id ? 'text-emerald-400 hover:text-emerald-300' : 'text-slate-500 hover:text-slate-400'
                  }`}
                >
                  {currentStep > step.id ? (
                    <CheckCircle2 className="h-5 w-5" />
                  ) : (
                    <div
                      className={`h-5 w-5 rounded-full border-2 flex items-center justify-center ${
                        currentStep === step.id
                          ? 'border-emerald-500 bg-emerald-500'
                          : currentStep > step.id
                          ? 'border-emerald-500 bg-emerald-500'
                          : 'border-slate-600'
                      }`}
                    >
                      {currentStep === step.id && (
                        <div className="h-2 w-2 rounded-full bg-white" />
                      )}
                    </div>
                  )}
                  <span className="hidden sm:inline">{step.title}</span>
                </div>
              ))}
            </div>
          </div>
          
          <CardDescription className="mt-2">
            {STEPS[currentStep].description}
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {renderStepContent()}
          
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-slate-700">
            <Button
              type="button"
              variant="outline"
              onClick={handleBack}
              disabled={currentStep === 0}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            
            {currentStep < STEPS.length - 1 ? (
              <Button
                type="button"
                onClick={handleNext}
                className="flex items-center gap-2"
              >
                Next
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating Account...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4" />
                    Complete Signup
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
