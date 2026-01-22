import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Shield, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { NotarizationModal } from './NotarizationModal';
// useAuth removed - unused

interface NotarizationButtonProps {
  documentId?: number;
  dealId?: number;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
  onNotarizationComplete?: (notarizationId: number) => void;
  onError?: (error: string) => void;
}

export function NotarizationButton({
  documentId,
  dealId,
  variant = 'outline',
  size = 'sm',
  className = '',
  onNotarizationComplete,
  onError,
}: NotarizationButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [notarizationStatus, setNotarizationStatus] = useState<'idle' | 'pending' | 'completed' | 'error'>('idle');
  // const { user } = useAuth(); // user unused

  const handleNotarizationComplete = (notarizationId: number) => {
    setNotarizationStatus('completed');
    setIsModalOpen(false);
    onNotarizationComplete?.(notarizationId);
    
    // Reset status after 3 seconds
    setTimeout(() => setNotarizationStatus('idle'), 3000);
  };

  const handleError = (error: string) => {
    setNotarizationStatus('error');
    onError?.(error);
    
    // Reset status after 5 seconds
    setTimeout(() => setNotarizationStatus('idle'), 5000);
  };

  const getButtonContent = () => {
    switch (notarizationStatus) {
      case 'pending':
        return (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Notarizing...
          </>
        );
      case 'completed':
        return (
          <>
            <CheckCircle className="h-4 w-4 mr-2 text-emerald-400" />
            Notarized
          </>
        );
      case 'error':
        return (
          <>
            <AlertCircle className="h-4 w-4 mr-2 text-red-400" />
            Error
          </>
        );
      default:
        return (
          <>
            <Shield className="h-4 w-4 mr-2" />
            Notarize
          </>
        );
    }
  };

  const getButtonClassName = () => {
    const baseClass = className;
    const statusClass = 
      notarizationStatus === 'completed' 
        ? 'bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 border-emerald-600/30'
        : notarizationStatus === 'error'
        ? 'bg-red-600/10 hover:bg-red-600/20 text-red-400 border-red-600/30'
        : 'bg-purple-600/10 hover:bg-purple-600/20 text-purple-400 border-purple-600/30';
    
    return `${baseClass} ${statusClass}`;
  };

  if (!documentId && !dealId) {
    return null;
  }

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={() => setIsModalOpen(true)}
        disabled={notarizationStatus === 'pending'}
        className={getButtonClassName()}
        title="Notarize document on blockchain"
      >
        {getButtonContent()}
      </Button>
      
      <NotarizationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        documentId={documentId}
        dealId={dealId}
        onNotarizationComplete={handleNotarizationComplete}
        onError={handleError}
      />
    </>
  );
}
