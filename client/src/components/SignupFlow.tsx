import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ProfileEnrichment } from '@/components/ProfileEnrichment';
import { 
  ArrowLeft, 
  ArrowRight, 
  CheckCircle2, 
  User, 
  FileText, 
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
  
  // Step 2: Profile Enrichment (will be populated by ProfileEnrichment component)
  profileData: Record<string, any>;
  
  // Step 3: Documents
  documents: File[];
  
  // Step 4: Review (no additional data)
}

interface SignupFlowProps {
  onComplete?: () => void;
  onCancel?: () => void;
}

const STEPS = [
  { id: 1, title: 'Basic Information', description: 'Email, password, and role selection' },
  { id: 2, title: 'Profile Enrichment', description: 'Complete your profile information' },
  { id: 3, title: 'Document Upload', description: 'Upload supporting documents (optional)' },
  { id: 4, title: 'Review & Submit', description: 'Review your information and complete signup' },
];

export function SignupFlow({ onComplete, onCancel }: SignupFlowProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<SignupFormData>({
    email: '',
    password: '',
    confirmPassword: '',
    displayName: '',
    role: null,
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
    
    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 12) {
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
    
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    
    if (!formData.displayName) {
      newErrors.displayName = 'Display name is required';
    }
    
    if (!formData.role) {
      newErrors.role = 'Please select a role';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (currentStep === 1) {
      if (!validateStep1()) {
        return;
      }
    }
    
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
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

      case 3:
        return (
          <div className="space-y-6">
            <div className="text-center py-8">
              <p className="text-slate-400">
                Document upload will be implemented in the next task.
              </p>
              <p className="text-sm text-slate-500 mt-2">
                Upload business cards, resumes, or company documents to automatically extract profile data.
              </p>
            </div>
          </div>
        );

      case 4:
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

  const progress = ((currentStep - 1) / (STEPS.length - 1)) * 100;

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
              {STEPS.map((step, index) => (
                <div
                  key={step.id}
                  className={`flex items-center gap-2 ${
                    currentStep >= step.id ? 'text-emerald-400' : 'text-slate-500'
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
            {STEPS[currentStep - 1].description}
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {renderStepContent()}
          
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-slate-700">
            <Button
              type="button"
              variant="outline"
              onClick={handleBack}
              disabled={currentStep === 1}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            
            {currentStep < STEPS.length ? (
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
