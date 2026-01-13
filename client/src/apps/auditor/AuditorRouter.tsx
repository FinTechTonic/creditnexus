import { useLocation } from 'react-router-dom';
import { AuditDashboard } from './AuditDashboard';
import { AuditDetail } from './AuditDetail';
import { DealAuditView } from './DealAuditView';
import { LoanAuditView } from './LoanAuditView';
import { FilingAuditView } from './FilingAuditView';
import { AuditReportGenerator } from './AuditReportGenerator';

export function AuditorRouter() {
  const location = useLocation();
  const pathname = location.pathname;

  // Handle nested routes
  if (pathname.startsWith('/auditor/logs/')) {
    const match = pathname.match(/\/auditor\/logs\/(\d+)/);
    if (match) {
      return <AuditDetail />;
    }
  }

  if (pathname.startsWith('/auditor/deals/')) {
    const match = pathname.match(/\/auditor\/deals\/(\d+)/);
    if (match) {
      return <DealAuditView />;
    }
  }

  if (pathname.startsWith('/auditor/loans/')) {
    const match = pathname.match(/\/auditor\/loans\/([^/]+)/);
    if (match) {
      return <LoanAuditView />;
    }
  }

  if (pathname.startsWith('/auditor/filings/')) {
    const match = pathname.match(/\/auditor\/filings\/(\d+)/);
    if (match) {
      return <FilingAuditView />;
    }
  }

  if (pathname.startsWith('/auditor/reports')) {
    return <AuditReportGenerator />;
  }

  // Default to dashboard
  return <AuditDashboard />;
}
