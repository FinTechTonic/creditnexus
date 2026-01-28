import React from 'react';
import { Dashboard } from '@/components/Dashboard';
import { MyPendingSignatures } from '@/components/dashboard-tabs/MyPendingSignatures';
import { SignatureCoordinationPanel } from '@/components/dashboard-tabs/SignatureCoordinationPanel';
import { SignatureAuditTrail } from '@/components/dashboard-tabs/SignatureAuditTrail';
import { GDPRDashboard } from '@/components/dashboard-tabs/GDPRDashboard';
import {
  PenTool,
  Shield,
  DollarSign,
  ExternalLink,
} from 'lucide-react';

export function SignatureDashboard() {
  const [activeTab, setActiveTab] = React.useState('pending');

  return (
    <div className="p-6 space-y-6 flex flex-col h-full overflow-hidden">
      <div>
        <h2 className="text-2xl font-bold mb-2 text-slate-100">Signature Dashboard</h2>
        <p className="text-muted-foreground max-w-2xl text-sm">
          Manage digital signatures for your documents. Open any document from the Documents tab to request a
          signature, then track its status here or on the deal view.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
        <TabsList className="bg-slate-900 border-slate-800 self-start">
          <TabsTrigger value="pending" className="data-[state=active]:bg-slate-800">My Pending</TabsTrigger>
          <TabsTrigger value="coordinated" className="data-[state=active]:bg-slate-800">Coordination</TabsTrigger>
          <TabsTrigger value="audit" className="data-[state=active]:bg-slate-800">Global Audit</TabsTrigger>
          <TabsTrigger value="guide" className="data-[state=active]:bg-slate-800">Help Guide</TabsTrigger>
        </TabsList>

        <TabsContent value="pending" className="flex-1 overflow-auto mt-4 bg-slate-950/20 rounded-xl border border-slate-800/50">
          <MyPendingSignatures />
        </TabsContent>

        <TabsContent value="coordinated" className="flex-1 overflow-auto mt-4 bg-slate-950/20 rounded-xl border border-slate-800/50">
          <SignatureCoordinationPanel />
        </TabsContent>

        <TabsContent value="audit" className="flex-1 overflow-auto mt-4 p-6 bg-slate-950/20 rounded-xl border border-slate-800/50">
          <SignatureAuditTrail />
        </TabsContent>

        <TabsContent value="guide" className="flex-1 overflow-auto mt-4 p-6 bg-slate-950/20 rounded-xl border border-slate-800/50">
          <div className="grid gap-8 md:grid-cols-2">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                <PenTool className="h-5 w-5 text-blue-400" />
                Workflow Instructions
              </h3>
              <ol className="list-decimal list-inside text-sm text-slate-300 space-y-3 leading-relaxed">
                <li>Go to the <span className="text-blue-400 font-semibold">Documents</span> tab and select any document.</li>
                <li>Use the <span className="text-emerald-400 font-semibold">“Sign”</span> button in the top toolbar to open the request modal.</li>
                <li>Verify signer details (names, roles, and emails).</li>
                <li>Submit the request. Our system will generate a secure, token-based link.</li>
                <li>The signer receives an email notification with their unique link.</li>
              </ol>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                <ExternalLink className="h-5 w-5 text-emerald-400" />
                Native Signer Portal
              </h3>
              <p className="text-sm text-slate-300 leading-relaxed">
                External signers do not need a CreditNexus account. They can use their secure token links to access
                the <span className="text-emerald-400 italic">Signer Portal</span>, where they can:
              </p>
              <ul className="list-disc list-inside text-sm text-slate-400 space-y-1 ml-2">
                <li>Preview the document content</li>
                <li>Draw or type their signature</li>
                <li>Provide MetaMask verification (if required)</li>
                <li>Download a signed copy instantly</li>
              </ul>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export function ComplianceDashboard() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Compliance Dashboard</h2>
      <p className="text-muted-foreground">Compliance monitoring and reporting will be implemented here.</p>
    </div>
  );
}

export function BillingDashboard() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Billing Dashboard</h2>
      <p className="text-muted-foreground">Billing and subscription management will be implemented here.</p>
    </div>
  );
}

export function UnifiedDashboard() {
  // Phase 2 requirement: Dashboard should no longer render
  // its own nested top-level tabs. All major sections
  // (Trading, Bridge, Documents, Signatures, Applications,
  // Billing, Privacy) are now accessed via the sidebar.
  //
  // The unified dashboard is now a single overview view.
  return (
    <div className="flex flex-col h-full space-y-4">
      <Dashboard />
    </div>
  );
}

export { GDPRDashboard };
