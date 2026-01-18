import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { LayoutDashboard, FileText, Shield, FileSearch, BarChart } from 'lucide-react';

export function AuditorLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const pathname = location.pathname;

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="h-4 w-4" />, path: '/auditor' },
    { id: 'logs', label: 'Audit Logs', icon: <FileText className="h-4 w-4" />, path: '/auditor/logs' },
    { id: 'policy', label: 'Policy Decisions', icon: <Shield className="h-4 w-4" />, path: '/auditor/policy' },
    { id: 'cdm', label: 'CDM Events', icon: <FileSearch className="h-4 w-4" />, path: '/auditor/cdm-events' },
    { id: 'reports', label: 'Report Generator', icon: <BarChart className="h-4 w-4" />, path: '/auditor/reports' },
  ];

  const activeTab = tabs.find(tab => 
    tab.path === '/auditor' ? pathname === '/auditor' : pathname.startsWith(tab.path)
  )?.id || 'dashboard';

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex items-center gap-1 bg-slate-800/50 p-1 rounded-lg border border-slate-700">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? 'default' : 'ghost'}
            size="sm"
            onClick={() => navigate(tab.path)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-emerald-600 text-white hover:bg-emerald-500'
                : 'text-slate-400 hover:text-white hover:bg-slate-700'
            }`}
          >
            {tab.icon}
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Content Area */}
      <div className="min-h-[600px]">
        {children}
      </div>
    </div>
  );
}
