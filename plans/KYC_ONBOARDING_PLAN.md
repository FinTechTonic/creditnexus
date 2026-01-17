# KYC-Compliant Onboarding & PeopleHub Integration Plan
## Complete User Verification Flow with License Attachments and PeopleHub Intelligence

**Status**: Comprehensive Enhancement Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 6-8 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This plan transforms the user onboarding process into a comprehensive KYC-compliant flow that:
1. **Requires KYC Completion**: All users must complete KYC verification before account approval
2. **License Attachments**: Role-specific license/document upload and verification
3. **PeopleHub Integration**: PeopleHub bot available throughout onboarding for identity verification
4. **Automated KYC Checks**: Automatic KYC compliance evaluation using policy engine
5. **Document Verification**: Automated verification of uploaded licenses and documents
6. **Admin Review Dashboard**: Enhanced admin interface for reviewing KYC submissions

---

## Current State Analysis

### Existing Onboarding System

**Components**:
- `client/src/components/SignupFlow.tsx` - Multi-step signup flow
- `app/auth/jwt_auth.py` - Signup endpoints (`/signup/step1`, `/signup/step2`)
- `app/db/models.py` - User model with `signup_status` field
- `app/policies/compliance/kyc_compliance.yaml` - KYC policy rules
- `app/services/policy_service.py` - `evaluate_kyc_compliance()` method

**Current Flow**:
1. Step 0: AI Profile Extraction (multimodal input)
2. Step 1: Basic Information (email, password, role)
3. Step 2: Profile Enrichment (ProfileEnrichment component)
4. Step 3: Document Upload (placeholder - not implemented)
5. Step 4: Review & Submit
6. Admin approval required (`signup_status: "pending"`)

**Limitations**:
- No KYC compliance check during signup
- Document upload step not implemented
- No license verification
- PeopleHub not integrated into onboarding
- No automated KYC evaluation
- Admin review lacks KYC context

---

## Project 1: KYC Status & License Models

### Activity 1.1: Database Models

**File**: `app/db/models.py` (UPDATE)

#### Task 1.1.1: Add KYC and License Models
**Lines**: ~3500-3700

**Subtasks**:
1. **Line 3500-3600**: KYC verification model
   ```python
   class KYCVerification(Base):
       """KYC verification record for users."""
       __tablename__ = "kyc_verifications"
       
       id = Column(Integer, primary_key=True)
       user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
       kyc_status = Column(String(20), default="pending", nullable=False, index=True)  # pending, in_progress, completed, rejected, expired
       kyc_level = Column(String(20), nullable=True)  # basic, standard, enhanced
       verification_method = Column(String(50), nullable=True)  # automated, manual, hybrid
       
       # KYC data
       identity_verified = Column(Boolean, default=False, nullable=False)
       address_verified = Column(Boolean, default=False, nullable=False)
       document_verified = Column(Boolean, default=False, nullable=False)
       license_verified = Column(Boolean, default=False, nullable=False)
       sanctions_check_passed = Column(Boolean, default=False, nullable=False)
       pep_check_passed = Column(Boolean, default=False, nullable=False)  # Politically Exposed Person
       
       # Verification metadata
       verification_metadata = Column(JSONB, nullable=True)  # Detailed verification results
       policy_evaluation_result = Column(JSONB, nullable=True)  # Policy engine evaluation
       peoplehub_profile_id = Column(Integer, ForeignKey("individual_profiles.id"), nullable=True)
       
       # Timestamps
       submitted_at = Column(DateTime, nullable=True)
       completed_at = Column(DateTime, nullable=True)
       expires_at = Column(DateTime, nullable=True)  # KYC expiration (typically 1-3 years)
       reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
       reviewed_at = Column(DateTime, nullable=True)
       rejection_reason = Column(Text, nullable=True)
       
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       user = relationship("User", back_populates="kyc_verification", foreign_keys=[user_id])
       reviewer = relationship("User", foreign_keys=[reviewed_by])
       peoplehub_profile = relationship("IndividualProfile", back_populates="kyc_verifications")
       licenses = relationship("UserLicense", back_populates="kyc_verification")
       documents = relationship("KYCDocument", back_populates="kyc_verification")
   
   class UserLicense(Base):
       """User license/professional certification."""
       __tablename__ = "user_licenses"
       
       id = Column(Integer, primary_key=True)
       user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
       kyc_verification_id = Column(Integer, ForeignKey("kyc_verifications.id", ondelete="CASCADE"), nullable=True, index=True)
       
       license_type = Column(String(100), nullable=False)  # professional_license, certification, registration
       license_number = Column(EncryptedString(255), nullable=True)  # Encrypted PII
       issuing_authority = Column(String(255), nullable=True)
       issue_date = Column(Date, nullable=True)
       expiration_date = Column(Date, nullable=True)
       license_category = Column(String(100), nullable=True)  # banking, legal, accounting, etc.
       
       # Document storage
       document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # Link to uploaded document
       document_url = Column(String(500), nullable=True)  # URL to license document
       
       # Verification status
       verification_status = Column(String(20), default="pending", nullable=False)  # pending, verified, rejected, expired
       verified_at = Column(DateTime, nullable=True)
       verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
       verification_notes = Column(Text, nullable=True)
       
       # Metadata
       metadata = Column(JSONB, nullable=True)  # Additional license information
       
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       user = relationship("User", back_populates="licenses")
       kyc_verification = relationship("KYCVerification", back_populates="licenses")
       document = relationship("Document")
       verifier = relationship("User", foreign_keys=[verified_by])
   
   class KYCDocument(Base):
       """KYC document (ID, proof of address, etc.)."""
       __tablename__ = "kyc_documents"
       
       id = Column(Integer, primary_key=True)
       user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
       kyc_verification_id = Column(Integer, ForeignKey("kyc_verifications.id", ondelete="CASCADE"), nullable=True, index=True)
       
       document_type = Column(String(50), nullable=False)  # id_document, proof_of_address, bank_statement, tax_document
       document_category = Column(String(50), nullable=True)  # passport, driver_license, utility_bill, etc.
       
       # Document storage
       document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
       document_url = Column(String(500), nullable=True)
       
       # Verification status
       verification_status = Column(String(20), default="pending", nullable=False)
       verified_at = Column(DateTime, nullable=True)
       verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
       verification_notes = Column(Text, nullable=True)
       
       # OCR/Extraction data
       extracted_data = Column(JSONB, nullable=True)  # OCR-extracted data
       ocr_confidence = Column(Float, nullable=True)
       
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       user = relationship("User", back_populates="kyc_documents")
       kyc_verification = relationship("KYCVerification", back_populates="documents")
       document = relationship("Document")
       verifier = relationship("User", foreign_keys=[verified_by])
   ```

2. **Line 3601-3700**: Update User model
   ```python
   # In User model, add relationships:
   kyc_verification = relationship("KYCVerification", back_populates="user", uselist=False)
   licenses = relationship("UserLicense", back_populates="user")
   kyc_documents = relationship("KYCDocument", back_populates="user")
   
   # Add KYC status helper method
   def get_kyc_status(self) -> str:
       """Get current KYC status."""
       if self.kyc_verification:
           return self.kyc_verification.kyc_status
       return "not_started"
   
   def is_kyc_complete(self) -> bool:
       """Check if KYC is complete."""
       if not self.kyc_verification:
           return False
       return self.kyc_verification.kyc_status == "completed"
   ```

---

## Project 2: Enhanced Signup Flow with KYC

### Activity 2.1: KYC Step in Signup Flow

**File**: `client/src/components/SignupFlow.tsx` (UPDATE)

#### Task 2.1.1: Add KYC Step
**Lines**: ~44-50 (STEPS array), ~400-500 (renderStepContent)

**Subtasks**:
1. **Line 44-50**: Update STEPS array
   ```typescript
   const STEPS = [
     { id: 0, title: 'AI Profile Extraction', description: 'Extract profile data using AI' },
     { id: 1, title: 'Basic Information', description: 'Email, password, and role selection' },
     { id: 2, title: 'Profile Enrichment', description: 'Complete your profile information' },
     { id: 3, title: 'KYC Verification', description: 'Complete KYC compliance and upload documents' },  // NEW
     { id: 4, title: 'License Upload', description: 'Upload required licenses (role-specific)' },  // NEW
     { id: 5, title: 'Review & Submit', description: 'Review your information and complete signup' },
   ];
   ```

2. **Line 400-500**: Add KYC step rendering
   ```typescript
   case 3:
     return (
       <div className="space-y-6">
         <KYCVerificationStep
           role={formData.role}
           profileData={formData.profileData}
           onComplete={(kycData) => {
             updateFormData({ kycData });
             handleNext();
           }}
           onPeopleHubLaunch={(personName) => {
             // Launch PeopleHub for identity verification
             launchPeopleHub(personName);
           }}
         />
       </div>
     );
   
   case 4:
     return (
       <div className="space-y-6">
         <LicenseUploadStep
           role={formData.role}
           onUpload={(licenses) => {
             updateFormData({ licenses });
             handleNext();
           }}
         />
       </div>
     );
   ```

### Activity 2.2: KYC Verification Step Component

**File**: `client/src/components/onboarding/KYCVerificationStep.tsx` (NEW)

#### Task 2.2.1: Create KYC Step Component
**Lines**: 1-500

**Subtasks**:
1. **Line 1-150**: Component setup with PeopleHub integration
   ```typescript
   import { useState, useEffect } from 'react';
   import { FileUpload, User, Shield, CheckCircle2, AlertCircle, Bot } from 'lucide-react';
   import { fetchWithAuth } from '@/context/AuthContext';
   import { PeopleHubBot } from '@/components/onboarding/PeopleHubBot';
   import { Button } from '@/components/ui/button';
   import { Card } from '@/components/ui/card';
   
   interface KYCVerificationStepProps {
     role: string | null;
     profileData: Record<string, unknown>;
     onComplete: (kycData: KYCData) => void;
     onPeopleHubLaunch: (personName: string) => void;
   }
   
   interface KYCData {
     identity_verified: boolean;
     address_verified: boolean;
     documents: KYCDocument[];
     peoplehub_profile_id?: number;
   }
   
   export function KYCVerificationStep({
     role,
     profileData,
     onComplete,
     onPeopleHubLaunch
   }: KYCVerificationStepProps) {
     const [kycData, setKycData] = useState<KYCData>({
       identity_verified: false,
       address_verified: false,
       documents: []
     });
     const [showPeopleHub, setShowPeopleHub] = useState(false);
     const [peoplehubResult, setPeoplehubResult] = useState<any>(null);
     const [kycEvaluation, setKycEvaluation] = useState<any>(null);
     const [loading, setLoading] = useState(false);
     
     // Auto-launch PeopleHub on mount if name available
     useEffect(() => {
       const personName = profileData.name || profileData.display_name;
       if (personName && !peoplehubResult) {
         setShowPeopleHub(true);
       }
     }, [profileData]);
   ```

2. **Line 151-300**: PeopleHub integration
   ```typescript
     const handlePeopleHubComplete = async (result: any) => {
       setPeoplehubResult(result);
       setShowPeopleHub(false);
       
       // Evaluate KYC compliance with PeopleHub results
       setLoading(true);
       try {
         const response = await fetchWithAuth('/api/kyc/evaluate', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({
             profile_type: 'individual',
             profile_id: result.profile_id,
             profile: result.profile_data
           })
         });
         
         if (response.ok) {
           const evaluation = await response.json();
           setKycEvaluation(evaluation);
           
           // Update KYC data based on evaluation
           setKycData(prev => ({
             ...prev,
             identity_verified: evaluation.decision === 'ALLOW' && 
                               evaluation.verification_results?.identity_verified === true,
             peoplehub_profile_id: result.profile_id
           }));
         }
       } catch (error) {
         console.error('KYC evaluation error:', error);
       } finally {
         setLoading(false);
       }
     };
   ```

3. **Line 301-500**: Document upload and rendering
   ```typescript
     const handleDocumentUpload = async (file: File, documentType: string) => {
       setLoading(true);
       try {
         const formData = new FormData();
         formData.append('file', file);
         formData.append('document_type', documentType);
         
         const response = await fetchWithAuth('/api/kyc/documents/upload', {
           method: 'POST',
           body: formData
         });
         
         if (response.ok) {
           const result = await response.json();
           setKycData(prev => ({
             ...prev,
             documents: [...prev.documents, result.document]
           }));
         }
       } catch (error) {
         console.error('Document upload error:', error);
       } finally {
         setLoading(false);
       }
     };
     
     return (
       <div className="space-y-6">
         <div className="text-center mb-6">
           <h3 className="text-xl font-semibold text-slate-100 mb-2">
             KYC Verification
           </h3>
           <p className="text-slate-400">
             Complete identity verification and upload required documents
           </p>
         </div>
         
         {/* PeopleHub Bot */}
         <Card className="p-4">
           <div className="flex items-center justify-between mb-4">
             <div className="flex items-center gap-2">
               <Bot className="h-5 w-5 text-emerald-400" />
               <h4 className="font-semibold text-slate-100">Identity Verification</h4>
             </div>
             <Button
               variant="outline"
               size="sm"
               onClick={() => setShowPeopleHub(!showPeopleHub)}
             >
               {showPeopleHub ? 'Hide' : 'Open'} PeopleHub
             </Button>
           </div>
           
           {showPeopleHub && (
             <PeopleHubBot
               personName={profileData.name || profileData.display_name || ''}
               onComplete={handlePeopleHubComplete}
               onLaunch={onPeopleHubLaunch}
             />
           )}
           
           {peoplehubResult && (
             <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/50 rounded-lg">
               <div className="flex items-center gap-2 text-emerald-400">
                 <CheckCircle2 className="h-4 w-4" />
                 <span className="text-sm">Identity verification completed</span>
               </div>
             </div>
           )}
         </Card>
         
         {/* KYC Evaluation Results */}
         {kycEvaluation && (
           <Card className="p-4">
             <h4 className="font-semibold text-slate-100 mb-3">KYC Compliance Status</h4>
             <div className="space-y-2">
               <div className={`flex items-center gap-2 ${
                 kycEvaluation.decision === 'ALLOW' ? 'text-emerald-400' : 
                 kycEvaluation.decision === 'FLAG' ? 'text-yellow-400' : 'text-red-400'
               }`}>
                 {kycEvaluation.decision === 'ALLOW' ? (
                   <CheckCircle2 className="h-4 w-4" />
                 ) : (
                   <AlertCircle className="h-4 w-4" />
                 )}
                 <span className="text-sm font-medium">
                   Status: {kycEvaluation.decision}
                 </span>
               </div>
               {kycEvaluation.issues && kycEvaluation.issues.length > 0 && (
                 <div className="mt-2 space-y-1">
                   {kycEvaluation.issues.map((issue: any, idx: number) => (
                     <div key={idx} className="text-sm text-slate-400">
                       • {issue.message}
                     </div>
                   ))}
                 </div>
               )}
             </div>
           </Card>
         )}
         
         {/* Document Upload */}
         <Card className="p-4">
           <h4 className="font-semibold text-slate-100 mb-3">Required Documents</h4>
           <div className="space-y-4">
             <DocumentUploadField
               label="ID Document"
               documentType="id_document"
               onUpload={(file) => handleDocumentUpload(file, 'id_document')}
               required
             />
             <DocumentUploadField
               label="Proof of Address"
               documentType="proof_of_address"
               onUpload={(file) => handleDocumentUpload(file, 'proof_of_address')}
               required
             />
           </div>
         </Card>
         
         <Button
           onClick={() => onComplete(kycData)}
           disabled={!kycData.identity_verified || kycData.documents.length < 2}
           className="w-full"
         >
           Continue to License Upload
         </Button>
       </div>
     );
   }
   ```

### Activity 2.3: License Upload Step Component

**File**: `client/src/components/onboarding/LicenseUploadStep.tsx` (NEW)

#### Task 2.3.1: Create License Upload Component
**Lines**: 1-300

**Subtasks**:
1. **Line 1-150**: Component with role-specific requirements
   ```typescript
   interface LicenseUploadStepProps {
     role: string | null;
     onUpload: (licenses: LicenseData[]) => void;
   }
   
   interface LicenseData {
     license_type: string;
     license_number?: string;
     issuing_authority?: string;
     document_id?: number;
   }
   
   const ROLE_LICENSE_REQUIREMENTS: Record<string, string[]> = {
     banker: ['banking_license', 'financial_services_registration'],
     law_officer: ['bar_admission', 'legal_practice_certificate'],
     accountant: ['cpa_certification', 'accounting_license'],
     applicant: []  // No license required for applicants
   };
   
   export function LicenseUploadStep({ role, onUpload }: LicenseUploadStepProps) {
     const [licenses, setLicenses] = useState<LicenseData[]>([]);
     const [loading, setLoading] = useState(false);
     
     const requiredLicenses = role ? ROLE_LICENSE_REQUIREMENTS[role] || [] : [];
   ```

2. **Line 151-300**: License upload handling
   ```typescript
     const handleLicenseUpload = async (file: File, licenseType: string) => {
       setLoading(true);
       try {
         const formData = new FormData();
         formData.append('file', file);
         formData.append('license_type', licenseType);
         
         const response = await fetchWithAuth('/api/kyc/licenses/upload', {
           method: 'POST',
           body: formData
         });
         
         if (response.ok) {
           const result = await response.json();
           setLicenses(prev => [...prev, result.license]);
         }
       } catch (error) {
         console.error('License upload error:', error);
       } finally {
         setLoading(false);
       }
     };
     
     return (
       <div className="space-y-6">
         <div className="text-center mb-6">
           <h3 className="text-xl font-semibold text-slate-100 mb-2">
             License & Certification Upload
           </h3>
           <p className="text-slate-400">
             {role ? `Upload required licenses for ${role}` : 'Upload your professional licenses'}
           </p>
         </div>
         
         {requiredLicenses.length > 0 ? (
           <div className="space-y-4">
             {requiredLicenses.map(licenseType => (
               <LicenseUploadField
                 key={licenseType}
                 label={formatLicenseLabel(licenseType)}
                 licenseType={licenseType}
                 onUpload={(file) => handleLicenseUpload(file, licenseType)}
                 required
               />
             ))}
           </div>
         ) : (
           <div className="text-center py-8">
             <p className="text-slate-400">
               No licenses required for your role. You can optionally upload certifications.
             </p>
           </div>
         )}
         
         <Button
           onClick={() => onUpload(licenses)}
           disabled={requiredLicenses.length > 0 && licenses.length < requiredLicenses.length}
           className="w-full"
         >
           Continue to Review
         </Button>
       </div>
     );
   }
   ```

---

## Project 3: PeopleHub Bot for Onboarding

### Activity 3.1: PeopleHub Bot Component

**File**: `client/src/components/onboarding/PeopleHubBot.tsx` (NEW)

#### Task 3.1.1: Create PeopleHub Bot Component
**Lines**: 1-400

**Subtasks**:
1. **Line 1-150**: Component setup
   ```typescript
   import { useState, useEffect, useCallback } from 'react';
   import { Bot, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
   import { fetchWithAuth } from '@/context/AuthContext';
   import { Card } from '@/components/ui/card';
   import { Button } from '@/components/ui/button';
   
   interface PeopleHubBotProps {
     personName: string;
     onComplete: (result: any) => void;
     onLaunch?: (personName: string) => void;
   }
   
   export function PeopleHubBot({
     personName,
     onComplete,
     onLaunch
   }: PeopleHubBotProps) {
     const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
     const [result, setResult] = useState<any>(null);
     const [error, setError] = useState<string | null>(null);
     const [progress, setProgress] = useState(0);
     
     // Auto-launch on mount
     useEffect(() => {
       if (personName && status === 'idle') {
         launchPeopleHub();
       }
     }, [personName]);
   ```

2. **Line 151-300**: PeopleHub launch and polling
   ```typescript
     const launchPeopleHub = useCallback(async () => {
       if (!personName) return;
       
       setStatus('running');
       setError(null);
       setProgress(10);
       
       if (onLaunch) {
         onLaunch(personName);
       }
       
       try {
         // Launch PeopleHub research
         const response = await fetchWithAuth('/api/person-research', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({
             person_name: personName,
             linkedin_url: null,  // Will be discovered
             deal_id: null
           })
         });
         
         if (!response.ok) {
           throw new Error('Failed to launch PeopleHub');
         }
         
         const data = await response.json();
         const researchId = data.research_id;
         
         setProgress(30);
         
         // Poll for results
         pollPeopleHubResults(researchId);
       } catch (err) {
         setError(err instanceof Error ? err.message : 'PeopleHub launch failed');
         setStatus('failed');
       }
     }, [personName, onLaunch]);
     
     const pollPeopleHubResults = async (researchId: string) => {
       const maxAttempts = 60; // 5 minutes max
       let attempts = 0;
       
       const poll = setInterval(async () => {
         attempts++;
         setProgress(30 + (attempts / maxAttempts) * 60);
         
         try {
           const response = await fetchWithAuth(`/api/person-research/${researchId}`);
           if (response.ok) {
             const data = await response.json();
             
             if (data.status === 'completed') {
               clearInterval(poll);
               setResult(data);
               setStatus('completed');
               setProgress(100);
               onComplete(data);
             } else if (data.status === 'failed') {
               clearInterval(poll);
               setError(data.error || 'PeopleHub research failed');
               setStatus('failed');
             }
           }
         } catch (err) {
           console.error('Poll error:', err);
         }
         
         if (attempts >= maxAttempts) {
           clearInterval(poll);
           setError('PeopleHub research timed out');
           setStatus('failed');
         }
       }, 5000); // Poll every 5 seconds
     };
   ```

3. **Line 301-400**: Render component
   ```typescript
     return (
       <Card className="p-4">
         <div className="space-y-4">
           <div className="flex items-center gap-2">
             <Bot className="h-5 w-5 text-emerald-400" />
             <h4 className="font-semibold text-slate-100">PeopleHub Identity Verification</h4>
           </div>
           
           {status === 'idle' && (
             <Button onClick={launchPeopleHub} className="w-full">
               Start Identity Verification
             </Button>
           )}
           
           {status === 'running' && (
             <div className="space-y-2">
               <div className="flex items-center gap-2 text-slate-400">
                 <Loader2 className="h-4 w-4 animate-spin" />
                 <span className="text-sm">Verifying identity via PeopleHub...</span>
               </div>
               <div className="w-full bg-slate-700 rounded-full h-2">
                 <div
                   className="bg-emerald-500 h-2 rounded-full transition-all"
                   style={{ width: `${progress}%` }}
                 />
               </div>
             </div>
           )}
           
           {status === 'completed' && result && (
             <div className="space-y-2">
               <div className="flex items-center gap-2 text-emerald-400">
                 <CheckCircle2 className="h-4 w-4" />
                 <span className="text-sm font-medium">Identity verification completed</span>
               </div>
               <div className="text-xs text-slate-400">
                 LinkedIn: {result.has_linkedin ? 'Verified' : 'Not found'} | 
                 Web Research: {result.has_web_research ? 'Found' : 'Not found'} |
                 Profile Data: {result.has_profile_data ? 'Complete' : 'Incomplete'}
               </div>
             </div>
           )}
           
           {status === 'failed' && (
             <div className="flex items-center gap-2 text-red-400">
               <AlertCircle className="h-4 w-4" />
               <span className="text-sm">{error || 'Verification failed'}</span>
             </div>
           )}
         </div>
       </Card>
     );
   }
   ```

---

## Project 4: KYC Service & API Endpoints

### Activity 4.1: KYC Service

**File**: `app/services/kyc_service.py` (NEW)

#### Task 4.1.1: Create KYC Service
**Lines**: 1-500

**Subtasks**:
1. **Line 1-150**: Service class
   ```python
   class KYCService:
       """Service for managing KYC verification workflows."""
       
       def __init__(self, db: Session):
           self.db = db
           self.policy_service = PolicyService(self.db)
       
       async def initiate_kyc_verification(
           self,
           user_id: int,
           profile_data: Optional[Dict[str, Any]] = None
       ) -> KYCVerification:
           """Initiate KYC verification for a user."""
           # Check if KYC already exists
           existing = self.db.query(KYCVerification).filter(
               KYCVerification.user_id == user_id
           ).first()
           
           if existing:
               return existing
           
           # Create KYC verification record
           kyc = KYCVerification(
               user_id=user_id,
               kyc_status="pending",
               submitted_at=datetime.utcnow(),
               expires_at=datetime.utcnow() + timedelta(days=1095)  # 3 years
           )
           self.db.add(kyc)
           self.db.commit()
           self.db.refresh(kyc)
           
           return kyc
       
       async def evaluate_kyc_compliance(
           self,
           user_id: int,
           peoplehub_profile_id: Optional[int] = None
       ) -> Dict[str, Any]:
           """Evaluate KYC compliance for a user."""
           user = self.db.query(User).filter(User.id == user_id).first()
           if not user:
               raise ValueError(f"User {user_id} not found")
           
           kyc = self.db.query(KYCVerification).filter(
               KYCVerification.user_id == user_id
           ).first()
           
           if not kyc:
               raise ValueError(f"KYC verification not found for user {user_id}")
           
           # Get PeopleHub profile if available
           profile_data = None
           if peoplehub_profile_id:
               from app.db.models import IndividualProfile
               profile = self.db.query(IndividualProfile).filter(
                   IndividualProfile.id == peoplehub_profile_id
               ).first()
               if profile:
                   profile_data = profile.to_dict()
           elif user.profile_data:
               profile_data = user.profile_data
           
           if not profile_data:
               return {
                   "decision": "BLOCK",
                   "reason": "No profile data available for KYC evaluation"
               }
           
           # Evaluate using policy service
           policy_result = self.policy_service.evaluate_kyc_compliance(
               profile=profile_data,
               profile_type="individual",
               individual_profile_id=peoplehub_profile_id
           )
           
           # Update KYC verification
           kyc.policy_evaluation_result = {
               "decision": policy_result.decision,
               "rule_applied": policy_result.rule_applied,
               "trace_id": policy_result.trace_id
           }
           
           # Update verification flags based on policy result
           if policy_result.decision == "ALLOW":
               kyc.identity_verified = True
               if profile_data.get("has_address"):
                   kyc.address_verified = True
           
           # Check document verification
           documents = self.db.query(KYCDocument).filter(
               KYCDocument.user_id == user_id,
               KYCDocument.verification_status == "verified"
           ).all()
           kyc.document_verified = len(documents) >= 2  # At least ID and proof of address
           
           # Check license verification
           licenses = self.db.query(UserLicense).filter(
               UserLicense.user_id == user_id,
               UserLicense.verification_status == "verified"
           ).all()
           kyc.license_verified = len(licenses) > 0
           
           # Determine KYC status
           if (kyc.identity_verified and kyc.document_verified and 
               (not user.role in ['banker', 'law_officer', 'accountant'] or kyc.license_verified)):
               kyc.kyc_status = "completed"
               kyc.completed_at = datetime.utcnow()
           else:
               kyc.kyc_status = "in_progress"
           
           self.db.commit()
           self.db.refresh(kyc)
           
           return {
               "decision": policy_result.decision,
               "kyc_status": kyc.kyc_status,
               "verification_results": {
                   "identity_verified": kyc.identity_verified,
                   "address_verified": kyc.address_verified,
                   "document_verified": kyc.document_verified,
                   "license_verified": kyc.license_verified
               },
               "policy_result": policy_result
           }
   ```

### Activity 4.2: API Endpoints

**File**: `app/api/routes.py` (UPDATE)

#### Task 4.2.1: Add KYC Endpoints
**Lines**: ~12300-12500

**Subtasks**:
1. **Line 12300-12400**: KYC endpoints
   ```python
   @router.post("/kyc/initiate")
   async def initiate_kyc(
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       """Initiate KYC verification for current user."""
       from app.services.kyc_service import KYCService
       
       service = KYCService(db)
       kyc = await service.initiate_kyc_verification(
           user_id=current_user.id,
           profile_data=current_user.profile_data
       )
       
       return {
           "kyc_id": kyc.id,
           "kyc_status": kyc.kyc_status,
           "required_documents": ["id_document", "proof_of_address"],
           "required_licenses": get_required_licenses_for_role(current_user.role)
       }
   
   @router.post("/kyc/documents/upload")
   async def upload_kyc_document(
       file: UploadFile = File(...),
       document_type: str = Form(...),
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       """Upload KYC document."""
       from app.services.kyc_service import KYCService
       from app.services.file_storage_service import FileStorageService
       
       service = KYCService(db)
       file_storage = FileStorageService()
       
       # Store document
       document_url = await file_storage.store_user_document(
           user_id=current_user.id,
           filename=file.filename,
           content=await file.read(),
           category="kyc"
       )
       
       # Create KYC document record
       kyc_doc = KYCDocument(
           user_id=current_user.id,
           document_type=document_type,
           document_url=document_url,
           verification_status="pending"
       )
       db.add(kyc_doc)
       db.commit()
       db.refresh(kyc_doc)
       
       # Trigger automatic verification
       # (OCR extraction, validation, etc.)
       
       return {
           "document_id": kyc_doc.id,
           "document": kyc_doc.to_dict()
       }
   
   @router.post("/kyc/licenses/upload")
   async def upload_license(
       file: UploadFile = File(...),
       license_type: str = Form(...),
       license_number: Optional[str] = Form(None),
       issuing_authority: Optional[str] = Form(None),
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       """Upload professional license."""
       from app.services.kyc_service import KYCService
       from app.services.file_storage_service import FileStorageService
       
       service = KYCService(db)
       file_storage = FileStorageService()
       
       # Store license document
       document_url = await file_storage.store_user_document(
           user_id=current_user.id,
           filename=file.filename,
           content=await file.read(),
           category="license"
       )
       
       # Create license record
       license = UserLicense(
           user_id=current_user.id,
           license_type=license_type,
           license_number=license_number,
           issuing_authority=issuing_authority,
           document_url=document_url,
           verification_status="pending"
       )
       db.add(license)
       db.commit()
       db.refresh(license)
       
       # Trigger automatic verification
       # (OCR extraction, license number validation, etc.)
       
       return {
           "license_id": license.id,
           "license": license.to_dict()
       }
   ```

---

## Project 5: Admin KYC Review Dashboard

### Activity 5.1: Enhanced Admin Signup Dashboard

**File**: `client/src/components/AdminSignupDashboard.tsx` (UPDATE)

#### Task 5.1.1: Add KYC Review Section
**Lines**: ~200-400

**Subtasks**:
1. **Line 200-300**: KYC review section
   ```typescript
   const KYCReviewSection = ({ user }: { user: any }) => {
     const [kycData, setKycData] = useState<any>(null);
     
     useEffect(() => {
       // Load KYC data
       fetchWithAuth(`/api/users/${user.id}/kyc`)
         .then(res => res.json())
         .then(data => setKycData(data));
     }, [user.id]);
     
     if (!kycData) return <div>Loading KYC data...</div>;
     
     return (
       <Card className="p-4">
         <h4 className="font-semibold mb-3">KYC Verification Status</h4>
         <div className="space-y-2">
           <div className="flex items-center justify-between">
             <span className="text-sm text-slate-400">Status:</span>
             <Badge variant={kycData.kyc_status === 'completed' ? 'success' : 'warning'}>
               {kycData.kyc_status}
             </Badge>
           </div>
           <div className="flex items-center justify-between">
             <span className="text-sm text-slate-400">Identity Verified:</span>
             {kycData.identity_verified ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <X className="h-4 w-4 text-red-400" />}
           </div>
           <div className="flex items-center justify-between">
             <span className="text-sm text-slate-400">Documents Verified:</span>
             {kycData.document_verified ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <X className="h-4 w-4 text-red-400" />}
           </div>
           <div className="flex items-center justify-between">
             <span className="text-sm text-slate-400">License Verified:</span>
             {kycData.license_verified ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <X className="h-4 w-4 text-red-400" />}
           </div>
           
           {kycData.policy_evaluation_result && (
             <div className="mt-3 p-2 bg-slate-800 rounded">
               <div className="text-xs text-slate-400">Policy Decision:</div>
               <div className="text-sm font-medium">
                 {kycData.policy_evaluation_result.decision}
               </div>
               {kycData.policy_evaluation_result.rule_applied && (
                 <div className="text-xs text-slate-500 mt-1">
                   Rule: {kycData.policy_evaluation_result.rule_applied}
                 </div>
               )}
             </div>
           )}
           
           {kycData.peoplehub_profile_id && (
             <Button
               variant="outline"
               size="sm"
               onClick={() => window.open(`/agent-dashboard?profile_id=${kycData.peoplehub_profile_id}`, '_blank')}
               className="mt-2 w-full"
             >
               View PeopleHub Profile
             </Button>
           )}
         </div>
       </Card>
     );
   };
   ```

---

## Implementation Checklist

### Phase 1: Database Models (Week 1)
- [ ] Create KYCVerification model
- [ ] Create UserLicense model
- [ ] Create KYCDocument model
- [ ] Update User model with relationships
- [ ] Create Alembic migration

### Phase 2: KYC Service (Week 2)
- [ ] Create KYCService
- [ ] Implement KYC evaluation logic
- [ ] Integrate with PolicyService
- [ ] Add document verification logic
- [ ] Add license verification logic

### Phase 3: Signup Flow Updates (Week 3-4)
- [ ] Add KYC step to SignupFlow
- [ ] Create KYCVerificationStep component
- [ ] Create LicenseUploadStep component
- [ ] Integrate PeopleHub bot
- [ ] Update signup submission to include KYC data

### Phase 4: PeopleHub Integration (Week 5)
- [ ] Create PeopleHubBot component
- [ ] Integrate into KYC step
- [ ] Add auto-launch functionality
- [ ] Add result polling
- [ ] Connect to KYC evaluation

### Phase 5: API Endpoints (Week 6)
- [ ] Add /api/kyc/initiate endpoint
- [ ] Add /api/kyc/documents/upload endpoint
- [ ] Add /api/kyc/licenses/upload endpoint
- [ ] Add /api/kyc/evaluate endpoint (enhance existing)
- [ ] Add document verification endpoints

### Phase 6: Admin Dashboard (Week 7)
- [ ] Update AdminSignupDashboard with KYC section
- [ ] Add KYC review interface
- [ ] Add PeopleHub profile links
- [ ] Add document viewer
- [ ] Add license viewer

### Phase 7: Testing & Refinement (Week 8)
- [ ] Test complete KYC flow
- [ ] Test PeopleHub integration
- [ ] Test license verification
- [ ] Test admin review process
- [ ] Performance optimization

---

## Success Criteria

1. ✅ All users must complete KYC before account approval
2. ✅ PeopleHub bot available throughout onboarding
3. ✅ Role-specific license requirements enforced
4. ✅ Automatic KYC compliance evaluation
5. ✅ Document and license verification automated
6. ✅ Admin dashboard shows complete KYC context
7. ✅ KYC status tracked and displayed
8. ✅ Policy engine integration for compliance checks

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
