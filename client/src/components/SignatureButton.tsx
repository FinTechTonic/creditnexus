import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { PenTool, Loader2, CheckCircle, AlertCircle, FileText } from 'lucide-react';
import { SignatureRequestModal } from './SignatureRequestModal';
import { fetchWithAuth } from '@/context/AuthContext';

interface SignatureButtonProps {
  documentId: number;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
  onSignatureRequested?: (signatureId: number) => void;
  onError?: (error: string) => void;
}

export function SignatureButton({
  documentId,
  variant = 'outline',
  size = 'sm',
  className = '',
  onSignatureRequested,
  onError,
}: SignatureButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [signatureStatus, setSignatureStatus] = useState<'idle' | 'checking' | 'needs_signature' | 'pending' | 'completed' | 'error'>('checking');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkSignatureStatus();
  }, [documentId]);

  const checkSignatureStatus = async () => {
    if (!documentId) {
      setSignatureStatus('idle');
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const response = await fetchWithAuth(`/api/documents/${documentId}/signatures`);
      if (!response.ok) {
        throw new Error('Failed to check signature status');
      }
      const data = await response.json();
      
      if (data.needs_signature) {
        if (data.has_pending) {
          setSignatureStatus('pending');
        } else {
          setSignatureStatus('needs_signature');
        }
      } else if (data.has_completed) {
        setSignatureStatus('completed');
      } else {
        setSignatureStatus('needs_signature');
      }
    } catch (err) {
      console.error('Error checking signature status:', err);
      // Default to showing button if check fails
      setSignatureStatus('needs_signature');
    } finally {
      setLoading(false);
    }
  };

  const handleSignatureRequested = (signatureId: number) => {
    setSignatureStatus('pending');
    setIsModalOpen(false);
    onSignatureRequested?.(signatureId);
    // Refresh status after a delay
    setTimeout(() => checkSignatureStatus(), 2000);
  };

  const handleError = (error: string) => {
    setSignatureStatus('error');
    onError?.(error);
    setTimeout(() => setSignatureStatus('needs_signature'), 5000);
  };

  const getButtonContent = () => {
    if (loading) {
      return (
        <>
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          Checking...
        </>
      );
    }

    switch (signatureStatus) {
      case 'pending':
        return (
          <>
            <FileText className="h-4 w-4 mr-2 text-yellow-400" />
            Pending
          </>
        );
      case 'completed':
        return (
          <>
            <CheckCircle className="h-4 w-4 mr-2 text-emerald-400" />
            Signed
          </>
        );
      case 'error':
        return (
          <>
            <AlertCircle className="h-4 w-4 mr-2 text-red-400" />
            Error
          </>
        );
      case 'needs_signature':
      default:
        return (
          <>
            <PenTool className="h-4 w-4 mr-2" />
            Sign
          </>
        );
    }
  };

  const getButtonClassName = () => {
    const baseClass = className;
    const statusClass = 
      signatureStatus === 'completed' 
        ? 'bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-400 border-emerald-600/30'
        : signatureStatus === 'pending'
        ? 'bg-yellow-600/10 hover:bg-yellow-600/20 text-yellow-400 border-yellow-600/30'
        : signatureStatus === 'error'
        ? 'bg-red-600/10 hover:bg-red-600/20 text-red-400 border-red-600/30'
        : 'bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border-blue-600/30';
    
    return `${baseClass} ${statusClass}`;
  };

  // Don't show button if document is already signed (unless user wants to see status)
  if (signatureStatus === 'completed' && !isModalOpen) {
    return null; // Or return a small status badge instead
  }

  // Don't show if checking and no document
  if (loading && signatureStatus === 'checking') {
    return null;
  }

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={() => setIsModalOpen(true)}
        disabled={loading || signatureStatus === 'checking'}
        className={getButtonClassName()}
        title={signatureStatus === 'pending' ? 'Signature request pending' : 'Request document signatures'}
      >
        {getButtonContent()}
      </Button>
      
      <SignatureRequestModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        documentId={documentId}
        onSignatureRequested={handleSignatureRequested}
        onError={handleError}
      />
    </>
  );
}
