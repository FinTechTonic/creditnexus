import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Shield, Lock, Eye, FileText, AlertCircle, CheckCircle2 } from 'lucide-react';

export function PrivacyPolicy() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-slate-100 mb-4">Privacy Policy</h1>
        <p className="text-slate-400">
          Last updated: {new Date().toLocaleDateString()}
        </p>
      </div>

      <div className="space-y-6">
        <Card className="bg-slate-900 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-emerald-400" />
              Introduction
            </CardTitle>
          </CardHeader>
          <CardContent className="text-slate-300 space-y-4">
            <p>
              At CreditNexus, we are committed to protecting your privacy and ensuring the security of your personal data. 
              This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our 
              platform and services.
            </p>
            <p>
              We comply with the General Data Protection Regulation (GDPR) and other applicable data protection laws. 
              By using our services, you agree to the collection and use of information in accordance with this policy.
            </p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-emerald-400" />
              Information We Collect
            </CardTitle>
          </CardHeader>
          <CardContent className="text-slate-300 space-y-4">
            <div>
              <h3 className="font-semibold text-slate-100 mb-2">Personal Information</h3>
              <ul className="list-disc list-inside space-y-1 text-slate-400 ml-4">
                <li>Name, email address, and contact information</li>
                <li>Professional credentials and licenses</li>
                <li>Organization and role information</li>
                <li>Wallet addresses for blockchain transactions</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 mb-2">Financial Information</h3>
              <ul className="list-disc list-inside space-y-1 text-slate-400 ml-4">
                <li>Deal and transaction data</li>
                <li>Investment and trading information</li>
                <li>Credit agreements and documentation</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 mb-2">Technical Information</h3>
              <ul className="list-disc list-inside space-y-1 text-slate-400 ml-4">
                <li>IP addresses and device information</li>
                <li>Browser type and version</li>
                <li>Usage data and analytics</li>
                <li>Cookies and similar tracking technologies</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5 text-emerald-400" />
              How We Use Your Information
            </CardTitle>
          </CardHeader>
          <CardContent className="text-slate-300 space-y-4">
            <p>We use the collected information for the following purposes:</p>
            <ul className="list-disc list-inside space-y-2 text-slate-400 ml-4">
              <li>To provide and maintain our services</li>
              <li>To process transactions and manage deals</li>
              <li>To verify identity and comply with KYC requirements</li>
              <li>To send notifications and updates about your account</li>
              <li>To improve our services and user experience</li>
              <li>To comply with legal and regulatory obligations</li>
              <li>To detect and prevent fraud or security issues</li>
            </ul>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5 text-emerald-400" />
              Data Security
            </CardTitle>
          </CardHeader>
          <CardContent className="text-slate-300 space-y-4">
            <p>
              We implement appropriate technical and organizational measures to protect your personal data against 
              unauthorized access, alteration, disclosure, or destruction. These measures include:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-400 ml-4">
              <li>Encryption of data in transit (SSL/TLS) and at rest</li>
              <li>Access controls and authentication mechanisms</li>
              <li>Regular security audits and vulnerability assessments</li>
              <li>Secure data storage and backup procedures</li>
              <li>Employee training on data protection</li>
            </ul>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              Your GDPR Rights
            </CardTitle>
          </CardHeader>
          <CardContent className="text-slate-300 space-y-4">
            <p>Under GDPR, you have the following rights regarding your personal data:</p>
            <div className="space-y-3">
              <div className="p-3 bg-slate-800 rounded-lg">
                <h4 className="font-semibold text-slate-100 mb-1">Right to Access (Article 15)</h4>
                <p className="text-sm text-slate-400">
                  You can request a copy of all personal data we hold about you.
                </p>
              </div>
              <div className="p-3 bg-slate-800 rounded-lg">
                <h4 className="font-semibold text-slate-100 mb-1">Right to Rectification (Article 16)</h4>
                <p className="text-sm text-slate-400">
                  You can request correction of inaccurate or incomplete data.
                </p>
              </div>
              <div className="p-3 bg-slate-800 rounded-lg">
                <h4 className="font-semibold text-slate-100 mb-1">Right to Erasure (Article 17)</h4>
                <p className="text-sm text-slate-400">
                  You can request deletion of your personal data in certain circumstances.
                </p>
              </div>
              <div className="p-3 bg-slate-800 rounded-lg">
                <h4 className="font-semibold text-slate-100 mb-1">Right to Restriction (Article 18)</h4>
                <p className="text-sm text-slate-400">
                  You can request restriction of processing in certain circumstances.
                </p>
              </div>
              <div className="p-3 bg-slate-800 rounded-lg">
                <h4 className="font-semibold text-slate-100 mb-1">Right to Data Portability (Article 20)</h4>
                <p className="text-sm text-slate-400">
                  You can request your data in a machine-readable format.
                </p>
              </div>
              <div className="p-3 bg-slate-800 rounded-lg">
                <h4 className="font-semibold text-slate-100 mb-1">Right to Object (Article 21)</h4>
                <p className="text-sm text-slate-400">
                  You can object to processing of your data for certain purposes.
                </p>
              </div>
              <div className="p-3 bg-slate-800 rounded-lg">
                <h4 className="font-semibold text-slate-100 mb-1">Right to Withdraw Consent (Article 7)</h4>
                <p className="text-sm text-slate-400">
                  You can withdraw consent at any time where processing is based on consent.
                </p>
              </div>
            </div>
            <p className="text-sm text-slate-400 mt-4">
              To exercise any of these rights, please visit the GDPR Dashboard in your account settings or contact us.
            </p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-emerald-400" />
              Data Retention
            </CardTitle>
          </CardHeader>
          <CardContent className="text-slate-300 space-y-4">
            <p>
              We retain your personal data only for as long as necessary to fulfill the purposes outlined in this policy, 
              unless a longer retention period is required or permitted by law. Our retention periods include:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-400 ml-4">
              <li>Account data: Until account deletion is requested</li>
              <li>Transaction records: 7 years (regulatory requirement)</li>
              <li>Audit logs: 7 years (compliance requirement)</li>
              <li>KYC documents: As required by applicable regulations</li>
            </ul>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-emerald-400" />
              Contact Us
            </CardTitle>
          </CardHeader>
          <CardContent className="text-slate-300 space-y-4">
            <p>
              If you have any questions about this Privacy Policy or wish to exercise your rights, please contact us:
            </p>
            <div className="p-4 bg-slate-800 rounded-lg">
              <p className="text-slate-100 font-semibold mb-2">Data Protection Officer</p>
              <p className="text-slate-400 text-sm">
                Email: privacy@creditnexus.com
              </p>
              <p className="text-slate-400 text-sm mt-2">
                You can also manage your privacy preferences directly in your account's GDPR Dashboard.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
