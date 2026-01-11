import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Building2, Briefcase, Award, MapPin } from 'lucide-react';

export interface BankerFormData {
  // Personal Information
  firstName: string;
  lastName: string;
  phone: string;
  
  // Professional Information
  jobTitle: string;
  department: string;
  yearsOfExperience: string;
  certifications: string; // Comma-separated
  licenses: string; // Comma-separated
  specializations: string; // Comma-separated
  
  // Bank/Company Information
  bankName: string;
  bankLEI: string;
  bankRegistration: string;
  bankAddress: string;
  bankCity: string;
  bankState: string;
  bankCountry: string;
  
  // Contact Information
  officePhone: string;
  officeEmail: string;
  linkedin: string;
}

interface SignupFormBankerProps {
  formData: Partial<BankerFormData>;
  onChange: (data: Partial<BankerFormData>) => void;
  errors?: Record<string, string>;
}

export function SignupFormBanker({ formData, onChange, errors = {} }: SignupFormBankerProps) {
  const updateField = (field: keyof BankerFormData, value: string) => {
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
              placeholder="Senior Credit Analyst"
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
              placeholder="Credit Risk"
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
            placeholder="10"
          />
          {errors.yearsOfExperience && (
            <p className="mt-1 text-sm text-red-400">{errors.yearsOfExperience}</p>
          )}
        </div>
        
        <div>
          <Label htmlFor="certifications">Professional Certifications (comma-separated)</Label>
          <Input
            id="certifications"
            value={formData.certifications || ''}
            onChange={(e) => updateField('certifications', e.target.value)}
            className={errors.certifications ? 'border-red-500' : ''}
            placeholder="CFA, FRM, CAIA"
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
            placeholder="Series 7, Series 63"
          />
          {errors.licenses && (
            <p className="mt-1 text-sm text-red-400">{errors.licenses}</p>
          )}
        </div>
        
        <div>
          <Label htmlFor="specializations">Areas of Specialization (comma-separated)</Label>
          <Input
            id="specializations"
            value={formData.specializations || ''}
            onChange={(e) => updateField('specializations', e.target.value)}
            className={errors.specializations ? 'border-red-500' : ''}
            placeholder="Corporate Lending, Risk Management, Credit Analysis"
          />
          {errors.specializations && (
            <p className="mt-1 text-sm text-red-400">{errors.specializations}</p>
          )}
        </div>
      </div>

      {/* Bank Information */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <Building2 className="h-5 w-5" />
          <h3 className="font-semibold">Bank/Company Information</h3>
        </div>
        
        <div>
          <Label htmlFor="bankName">Bank Name</Label>
          <Input
            id="bankName"
            value={formData.bankName || ''}
            onChange={(e) => updateField('bankName', e.target.value)}
            className={errors.bankName ? 'border-red-500' : ''}
            placeholder="First National Bank"
          />
          {errors.bankName && (
            <p className="mt-1 text-sm text-red-400">{errors.bankName}</p>
          )}
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="bankLEI">Bank LEI</Label>
            <Input
              id="bankLEI"
              value={formData.bankLEI || ''}
              onChange={(e) => updateField('bankLEI', e.target.value)}
              className={errors.bankLEI ? 'border-red-500' : ''}
              placeholder="5493000IBP32UQZ0KL24"
            />
            {errors.bankLEI && (
              <p className="mt-1 text-sm text-red-400">{errors.bankLEI}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="bankRegistration">Registration Number</Label>
            <Input
              id="bankRegistration"
              value={formData.bankRegistration || ''}
              onChange={(e) => updateField('bankRegistration', e.target.value)}
              className={errors.bankRegistration ? 'border-red-500' : ''}
              placeholder="12345678"
            />
            {errors.bankRegistration && (
              <p className="mt-1 text-sm text-red-400">{errors.bankRegistration}</p>
            )}
          </div>
        </div>
        
        <div>
          <Label htmlFor="bankAddress">Bank Address</Label>
          <Input
            id="bankAddress"
            value={formData.bankAddress || ''}
            onChange={(e) => updateField('bankAddress', e.target.value)}
            className={errors.bankAddress ? 'border-red-500' : ''}
            placeholder="123 Wall Street"
          />
          {errors.bankAddress && (
            <p className="mt-1 text-sm text-red-400">{errors.bankAddress}</p>
          )}
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="bankCity">City</Label>
            <Input
              id="bankCity"
              value={formData.bankCity || ''}
              onChange={(e) => updateField('bankCity', e.target.value)}
              className={errors.bankCity ? 'border-red-500' : ''}
              placeholder="New York"
            />
            {errors.bankCity && (
              <p className="mt-1 text-sm text-red-400">{errors.bankCity}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="bankState">State</Label>
            <Input
              id="bankState"
              value={formData.bankState || ''}
              onChange={(e) => updateField('bankState', e.target.value)}
              className={errors.bankState ? 'border-red-500' : ''}
              placeholder="NY"
            />
            {errors.bankState && (
              <p className="mt-1 text-sm text-red-400">{errors.bankState}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="bankCountry">Country</Label>
            <Input
              id="bankCountry"
              value={formData.bankCountry || ''}
              onChange={(e) => updateField('bankCountry', e.target.value)}
              className={errors.bankCountry ? 'border-red-500' : ''}
              placeholder="United States"
            />
            {errors.bankCountry && (
              <p className="mt-1 text-sm text-red-400">{errors.bankCountry}</p>
            )}
          </div>
        </div>
      </div>

      {/* Contact Information */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-300">
          <MapPin className="h-5 w-5" />
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
              placeholder="john.smith@bank.com"
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
