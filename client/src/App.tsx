import { useState, useEffect } from 'react';
import { DocuDigitizer } from '@/apps/docu-digitizer/DocuDigitizer';
import { TradeBlotter } from '@/apps/trade-blotter/TradeBlotter';
import { GreenLens } from '@/apps/green-lens/GreenLens';
import { DocumentHistory } from '@/components/DocumentHistory';
import { Dashboard } from '@/components/Dashboard';
import { LoginForm } from '@/components/LoginForm';
import { FileText, ArrowLeftRight, Leaf, Sparkles, Radio, LogIn, LogOut, User, Loader2, BookOpen, LayoutDashboard } from 'lucide-react';
import { useAuth } from './context/AuthContext';
import { useFDC3 } from '@/context/FDC3Context';
import type { CreditAgreementData, IntentName, DocumentContext, AgreementContext } from '@/context/FDC3Context';

type AppView = 'dashboard' | 'docu-digitizer' | 'trade-blotter' | 'green-lens' | 'library';

const apps: { id: AppView; name: string; icon: React.ReactNode; description: string }[] = [
  {
    id: 'dashboard',
    name: 'Dashboard',
    icon: <LayoutDashboard className="h-5 w-5" />,
    description: 'Portfolio overview & analytics',
  },
  {
    id: 'docu-digitizer',
    name: 'Docu-Digitizer',
    icon: <FileText className="h-5 w-5" />,
    description: 'Extract & digitize credit agreements',
  },
  {
    id: 'library',
    name: 'Library',
    icon: <BookOpen className="h-5 w-5" />,
    description: 'Saved documents & history',
  },
  {
    id: 'trade-blotter',
    name: 'Trade Blotter',
    icon: <ArrowLeftRight className="h-5 w-5" />,
    description: 'LMA trade confirmation & settlement',
  },
  {
    id: 'green-lens',
    name: 'GreenLens',
    icon: <Leaf className="h-5 w-5" />,
    description: 'ESG performance & margin ratchet',
  },
];

function App() {
  const [activeApp, setActiveApp] = useState<AppView>('docu-digitizer');
  const [hasBroadcast, setHasBroadcast] = useState(false);
  const [viewData, setViewData] = useState<CreditAgreementData | null>(null);
  const [extractionContent, setExtractionContent] = useState<string | null>(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const { isAvailable, pendingIntent, clearPendingIntent, onIntentReceived } = useFDC3();

  const processIntent = (intent: IntentName, context: unknown) => {
    console.log('[App] Processing FDC3 intent:', intent, context);
    
    switch (intent) {
      case 'ViewLoanAgreement': {
        const agreementCtx = context as AgreementContext;
        if (agreementCtx.id?.agreementId) {
          const agreementData: CreditAgreementData = {
            deal_id: agreementCtx.id.agreementId,
            agreement_date: agreementCtx.agreementDate,
            parties: agreementCtx.parties,
            facilities: agreementCtx.facilities,
          };
          setViewData(agreementData);
          setActiveApp('library');
        }
        break;
      }
      case 'ApproveLoanAgreement': {
        const approvalCtx = context as AgreementContext;
        if (approvalCtx.id?.agreementId) {
          const agreementData: CreditAgreementData = {
            deal_id: approvalCtx.id.agreementId,
            agreement_date: approvalCtx.agreementDate,
            parties: approvalCtx.parties,
            facilities: approvalCtx.facilities,
          };
          setViewData(agreementData);
          setActiveApp('library');
        }
        break;
      }
      case 'ViewESGAnalytics': {
        setActiveApp('green-lens');
        break;
      }
      case 'ExtractCreditAgreement': {
        const docCtx = context as DocumentContext;
        if (docCtx.content) {
          setExtractionContent(docCtx.content);
          setActiveApp('docu-digitizer');
        }
        break;
      }
      case 'ViewPortfolio': {
        console.log('[App] ViewPortfolio intent with context:', context);
        setActiveApp('dashboard');
        break;
      }
    }
  };

  useEffect(() => {
    onIntentReceived((intent, context) => {
      processIntent(intent, context);
    });
  }, [onIntentReceived]);

  useEffect(() => {
    if (pendingIntent) {
      const { intent, context } = pendingIntent;
      console.log('[App] Processing pending intent:', intent, context);
      clearPendingIntent();
      processIntent(intent, context);
    }
  }, [pendingIntent, clearPendingIntent]);

  const handleBroadcast = () => {
    setHasBroadcast(true);
  };

  const handleViewData = (data: Record<string, unknown>) => {
    setViewData(data as CreditAgreementData);
    setActiveApp('docu-digitizer');
  };

  const handleSaveToLibrary = () => {
    setExtractionContent(null);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="sticky top-0 z-50 border-b border-slate-700 bg-slate-900/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">CreditNexus</h1>
              <p className="text-xs text-slate-400">FINOS CDM Compliant</p>
            </div>
          </div>

          <nav className="flex items-center gap-1 bg-slate-800 rounded-lg p-1">
            {apps.map((app) => (
              <button
                key={app.id}
                onClick={() => setActiveApp(app.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  activeApp === app.id
                    ? 'bg-emerald-600 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                {app.icon}
                <span className="hidden md:inline">{app.name}</span>
                {app.id !== 'docu-digitizer' && hasBroadcast && (
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                )}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-slate-400" title={isAvailable ? 'FDC3 Desktop Agent Connected' : 'FDC3 Mock Mode (No Desktop Agent)'}>
              <Radio className={`h-4 w-4 ${isAvailable ? 'text-emerald-500' : 'text-slate-500'}`} />
              <span className="hidden sm:inline">FDC3</span>
              {isAvailable && (
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
              )}
            </div>
            
            {isLoading ? (
              <div className="flex items-center gap-2 text-slate-400">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            ) : isAuthenticated && user ? (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  {user.profile_image ? (
                    <img
                      src={user.profile_image}
                      alt={user.display_name}
                      className="w-8 h-8 rounded-full object-cover border-2 border-emerald-500"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center border-2 border-emerald-500">
                      <User className="h-4 w-4 text-slate-300" />
                    </div>
                  )}
                  <div className="hidden md:block">
                    <p className="text-sm font-medium text-slate-100">{user.display_name}</p>
                    <p className="text-xs text-slate-400 capitalize">{user.role}</p>
                  </div>
                </div>
                <button
                  onClick={logout}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
                  title="Log out"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden lg:inline">Log out</span>
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowLoginModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <LogIn className="h-4 w-4" />
                <span>Log in</span>
              </button>
            )}
          </div>
        </div>
      </header>
      
      <LoginForm isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeApp === 'dashboard' && <Dashboard />}
        {activeApp === 'docu-digitizer' && (
          <DocuDigitizer 
            onBroadcast={handleBroadcast} 
            onSaveToLibrary={handleSaveToLibrary}
            initialData={viewData}
          />
        )}
        {activeApp === 'library' && (
          <DocumentHistory onViewData={handleViewData} />
        )}
        {activeApp === 'trade-blotter' && <TradeBlotter />}
        {activeApp === 'green-lens' && <GreenLens />}
      </main>

      <footer className="border-t border-slate-700 mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-400">
          <p>Powered by OpenAI GPT-4o and LangChain</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <Radio className="h-3 w-3 text-emerald-500" />
              FDC3 Desktop Interoperability
            </span>
            <span>FINOS CDM Compliant</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
