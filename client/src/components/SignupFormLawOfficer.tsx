import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Scale, Briefcase, Award, Building2 } from 'lucide-react';

export interface LawOfficerFormData {
  // Personal Information
  firstName: string;
  lastName: string;
  phone: string;
  
  // Professional Information
  jobTitle: string;
  department: string;
  yearsOfExperience: string;
  barAdmission: string; // Comma-separated jurisdictions
  certifications: string; // Comma-separated
  licenses: string; // Comma-separated
  practiceAreas: string; // Comma-separated
  jurisdictions: string; // Comma-separated
  
  // Law Firm Information
  firmName: string;
  firmLEI: string;
  firmRegistration: string;
  firmAddress: string;
  firmCity: string;
  firmState: string;
  firmCountry: string;
  
  // Contact Information
  officePhone: string;
  officeEmail: string;
  linkedin: string;
}

interface SignupFormLawOfficerProps {
  formData: Partial<LawOfficerFormData>;
  onChange: (data: Partial<LawOfficerFormData>) => void;
  errors?: Record<string, string>;
}

export function SignupFormLawOfficer({ formData, onChange, errors = {} }: SignupFormLawOfficerProps) {
  const updateField = (field: keyof LawOfficerFormData, value: string) => {
    onChange({ [field]: value });
  };

  return (
    <div className="space-y-6">
      {/* Personal Information */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <Briefcase className="h-5 w-5" />
          <h3 className="font-semibold">Personal Information</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="firstName">First Name</Label>
            <Input
              id="firstName"
              value={formData.firstName || ''}
              onChange={(e) => updateField('firstName', e.target.value)}
              className={errors.firstName ? 'border-red-500' : ''}
              placeholder="John"
            />
            {errors.firstName && (
              <p className="mt-1 text-sm text-red-400">{errors.firstName}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="lastName">Last Name</Label>
            <Input
              id="lastName"
              value={formData.lastName || ''}
              onChange={(e) => updateField('lastName', e.target.value)}
              className={errors.lastName ? 'border-red-500' : ''}
              placeholder="Smith"
            />
            {errors.lastName && (
              <p className="mt-1 text-sm text-red-400">{errors.lastName}</p>
            )}
          </div>
        </div>
        
        <div>
          <Label htmlFor="phone">Phone Number</Label>
          <Input
            id="phone"
            type="tel"
            value={formData.phone || ''}
            onChange={(e) => updateField('phone', e.target.value)}
            className={errors.phone ? 'border-red-500' : ''}
            placeholder="+1 (555) 123-4567"
          />
          {errors.phone && (
            <p className="mt-1 text-sm text-red-400">{errors.phone}</p>
          )}
        </div>
      </div>

      {/* Professional Information */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <Award className="h-5 w-5" />
          <h3 className="font-semibold">Professional Information</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="jobTitle">Job Title</Label>
            <Input
              id="jobTitle"
              value={formData.jobTitle || ''}
              onChange={(e) => updateField('jobTitle', e.target.value)}
              className={errors.jobTitle ? 'border-red-500' : ''}
              placeholder="Partner"
            />
            {errors.jobTitle && (
              <p className="mt-1 text-sm text-red-400">{errors.jobTitle}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="department">Department</Label>
            <Input
              id="department"
              value={formData.department || ''}
              onChange={(e) => updateField('department', e.target.value)}
              className={errors.department ? 'border-red-500' : ''}
              placeholder="Corporate Law"
            />
            {errors.department && (
              <p className="mt-1 text-sm text-red-400">{errors.department}</p>
            )}
          </div>
        </div>
        
        <div>
          <Label htmlFor="yearsOfExperience">Years of Experience</Label>
          <Input
            id="yearsOfExperience"
            type="number"
            value={formData.yearsOfExperience || ''}
            onChange={(e) => updateField('yearsOfExperience', e.target.value)}
            className={errors.yearsOfExperience ? 'border-red-500' : ''}
            placeholder="15"
          />
          {errors.yearsOfExperience && (
            <p className="mt-1 text-sm text-red-400">{errors.yearsOfExperience}</p>
          )}
        </div>
        
        <div>
          <Label htmlFor="barAdmission">Bar Admission (comma-separated jurisdictions)</Label>
          <Input
            id="barAdmission"
            value={formData.barAdmission || ''}
            onChange={(e) => updateField('barAdmission', e.target.value)}
            className={errors.barAdmission ? 'border-red-500' : ''}
            placeholder="New York, California"
          />
          {errors.barAdmission && (
            <p className="mt-1 text-sm text-red-400">{errors.barAdmission}</p>
          )}
        </div>
        
        <div>
          <Label htmlFor="certifications">Professional Certifications (comma-separated)</Label>
          <Input
            id="certifications"
            value={formData.certifications || ''}
            onChange={(e) => updateField('certifications', e.target.value)}
            className={errors.certifications ? 'border-red-500' : ''}
            placeholder="CIPP, CAMS"
          />
          {errors.certifications && (
            <p className="mt-1 text-sm text-red-400">{errors.certifications}</p>
          )}
        </div>
        
        <div>
          <Label htmlFor="licenses">Professional Licenses (comma-separated)</Label>
          <Input
            id="licenses"
            value={formData.licenses || ''}
            onChange={(e) => updateField('licenses', e.target.value)}
            className={errors.licenses ? 'border-red-500' : ''}
            placeholder="Bar License #12345"
          />
          {errors.licenses && (
            <p className="mt-1 text-sm text-red-400">{errors.licenses}</p>
          )}
        </div>
        
        <div>
          <Label htmlFor="practiceAreas">Practice Areas (comma-separated)</Label>
          <Input
            id="practiceAreas"
            value={formData.practiceAreas || ''}
            onChange={(e) => updateField('practiceAreas', e.target.value)}
            className={errors.practiceAreas ? 'border-red-500' : ''}
            placeholder="Corporate Law, Securities Law, Banking Law"
          />
          {errors.practiceAreas && (
            <p className="mt-1 text-sm text-red-400">{errors.practiceAreas}</p>
          )}
        </div>
        
        <div>
          <Label htmlFor="jurisdictions">Jurisdictions (comma-separated)</Label>
          <Input
            id="jurisdictions"
            value={formData.jurisdictions || ''}
            onChange={(e) => updateField('jurisdictions', e.target.value)}
            className={errors.jurisdictions ? 'border-red-500' : ''}
            placeholder="New York, Delaware, Federal"
          />
          {errors.jurisdictions && (
            <p className="mt-1 text-sm text-red-400">{errors.jurisdictions}</p>
          )}
        </div>
      </div>

      {/* Law Firm Information */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <Building2 className="h-5 w-5" />
          <h3 className="font-semibold">Law Firm Information</h3>
        </div>
        
        <div>
          <Label htmlFor="firmName">Law Firm Name</Label>
          <Input
            id="firmName"
            value={formData.firmName || ''}
            onChange={(e) => updateField('firmName', e.target.value)}
            className={errors.firmName ? 'border-red-500' : ''}
            placeholder="Smith & Associates LLP"
          />
          {errors.firmName && (
            <p className="mt-1 text-sm text-red-400">{errors.firmName}</p>
          )}
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="firmLEI">Firm LEI</Label>
            <Input
              id="firmLEI"
              value={formData.firmLEI || ''}
              onChange={(e) => updateField('firmLEI', e.target.value)}
              className={errors.firmLEI ? 'border-red-500' : ''}
              placeholder="5493000IBP32UQZ0KL24"
            />
            {errors.firmLEI && (
              <p className="mt-1 text-sm text-red-400">{errors.firmLEI}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="firmRegistration">Registration Number</Label>
            <Input
              id="firmRegistration"
              value={formData.firmRegistration || ''}
              onChange={(e) => updateField('firmRegistration', e.target.value)}
              className={errors.firmRegistration ? 'border-red-500' : ''}
              placeholder="12345678"
            />
            {errors.firmRegistration && (
              <p className="mt-1 text-sm text-red-400">{errors.firmRegistration}</p>
            )}
          </div>
        </div>
        
        <div>
          <Label htmlFor="firmAddress">Firm Address</Label>
          <Input
            id="firmAddress"
            value={formData.firmAddress || ''}
            onChange={(e) => updateField('firmAddress', e.target.value)}
            className={errors.firmAddress ? 'border-red-500' : ''}
            placeholder="123 Legal Street"
          />
          {errors.firmAddress && (
            <p className="mt-1 text-sm text-red-400">{errors.firmAddress}</p>
          )}
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="firmCity">City</Label>
            <Input
              id="firmCity"
              value={formData.firmCity || ''}
              onChange={(e) => updateField('firmCity', e.target.value)}
              className={errors.firmCity ? 'border-red-500' : ''}
              placeholder="New York"
            />
            {errors.firmCity && (
              <p className="mt-1 text-sm text-red-400">{errors.firmCity}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="firmState">State</Label>
            <Input
              id="firmState"
              value={formData.firmState || ''}
              onChange={(e) => updateField('firmState', e.target.value)}
              className={errors.firmState ? 'border-red-500' : ''}
              placeholder="NY"
            />
            {errors.firmState && (
              <p className="mt-1 text-sm text-red-400">{errors.firmState}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="firmCountry">Country</Label>
            <Input
              id="firmCountry"
              value={formData.firmCountry || ''}
              onChange={(e) => updateField('firmCountry', e.target.value)}
              className={errors.firmCountry ? 'border-red-500' : ''}
              placeholder="United States"
            />
            {errors.firmCountry && (
              <p className="mt-1 text-sm text-red-400">{errors.firmCountry}</p>
            )}
          </div>
        </div>
      </div>

      {/* Contact Information */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <Scale className="h-5 w-5" />
          <h3 className="font-semibold">Contact Information</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="officePhone">Office Phone</Label>
            <Input
              id="officePhone"
              type="tel"
              value={formData.officePhone || ''}
              onChange={(e) => updateField('officePhone', e.target.value)}
              className={errors.officePhone ? 'border-red-500' : ''}
              placeholder="+1 (555) 123-4567"
            />
            {errors.officePhone && (
              <p className="mt-1 text-sm text-red-400">{errors.officePhone}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="officeEmail">Office Email</Label>
            <Input
              id="officeEmail"
              type="email"
              value={formData.officeEmail || ''}
              onChange={(e) => updateField('officeEmail', e.target.value)}
              className={errors.officeEmail ? 'border-red-500' : ''}
              placeholder="john.smith@lawfirm.com"
            />
            {errors.officeEmail && (
              <p className="mt-1 text-sm text-red-400">{errors.officeEmail}</p>
            )}
          </div>
        </div>
        
        <div>
          <Label htmlFor="linkedin">LinkedIn Profile URL</Label>
          <Input
            id="linkedin"
            type="url"
            value={formData.linkedin || ''}
            onChange={(e) => updateField('linkedin', e.target.value)}
            className={errors.linkedin ? 'border-red-500' : ''}
            placeholder="https://linkedin.com/in/johnsmith"
          />
          {errors.linkedin && (
            <p className="mt-1 text-sm text-red-400">{errors.linkedin}</p>
          )}
        </div>
      </div>
    </div>
  );
}
