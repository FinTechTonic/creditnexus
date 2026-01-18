import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
// Textarea removed - unused
import { Badge } from '@/components/ui/badge';
import {
  Shield,
  Wallet,
  Plus,
  X,
  Loader2,
  AlertCircle,
  // CheckCircle removed - unused
  Info,
  PenTool,
} from 'lucide-react';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';
import { useWallet } from '@/context/WalletContext';
import { useToast } from '@/components/ui/toast';
import { NotarizationPayment } from './NotarizationPayment';

interface NotarizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId?: number;
  dealId?: number;
  onNotarizationComplete?: (notarizationId: number) => void;
  onError?: (error: string) => void;
}

export function NotarizationModal({
  isOpen,
  onClose,
  documentId,
  dealId,
  onNotarizationComplete,
  onError,
}: NotarizationModalProps) {
  const { user } = useAuth();
  const { isConnected, account, connect } = useWallet();
  const { addToast } = useToast();
  const [signers, setSigners] = useState<string[]>([]);
  const [newSignerAddress, setNewSignerAddress] = useState('');
  const [messagePrefix, setMessagePrefix] = useState('CreditNexus Notarization');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notarizationId, setNotarizationId] = useState<number | null>(null);
  const [paymentRequired, setPaymentRequired] = useState(false);
  const [autoHydrateDeal, setAutoHydrateDeal] = useState(true);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editedAddress, setEditedAddress] = useState<string>('');

  useEffect(() => {
    // Initialize with connected wallet if available
    if (isConnected && account && signers.length === 0) {
      setSigners([account]);
    }
    if (!isOpen) {
      // Reset state when modal closes
      setEditingIndex(null);
      setEditedAddress('');
      setError(null);
    }
  }, [isOpen, isConnected, account]);

  const handleAddSigner = () => {
    if (!newSignerAddress.trim()) {
      setError('Please enter a wallet address');
      return;
    }

    // Basic Ethereum address validation
    if (!/^0x[a-fA-F0-9]{40}$/.test(newSignerAddress.trim())) {
      setError('Invalid Ethereum address format');
      return;
    }

    const address = newSignerAddress.trim().toLowerCase();
    if (signers.includes(address)) {
      setError('Signer already added');
      return;
    }

    setSigners([...signers, address]);
    setNewSignerAddress('');
    setError(null);
  };

  const handleRemoveSigner = (address: string) => {
    setSigners(signers.filter((s) => s !== address));
  };

  const handleConnectWallet = async () => {
    try {
      await connect();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect wallet');
    }
  };

  const handleCreateNotarization = async (skipPayment: boolean = false) => {
    if (signers.length === 0) {
      setError('At least one signer is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const endpoint = documentId
        ? `/api/documents/${documentId}/notarize`
        : `/api/remote/deals/${dealId}/notarize`;

      const requestBody: any = {
        required_signers: signers,
        message_prefix: messagePrefix,
        auto_hydrate_deal: autoHydrateDeal,
      };

      if (skipPayment && user?.role === 'admin') {
        requestBody.skip_payment = true;
      }

      const response = await fetchWithAuth(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (response.status === 402) {
        // Payment Required
        const paymentData = await response.json();
        setNotarizationId(paymentData.notarization_id);
        setPaymentRequired(true);
        setLoading(false);
        return;
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to create notarization');
      }

      const data = await response.json();
      const notarizationId = data.notarization_id;
      setNotarizationId(notarizationId);
      
      if (data.payment_status === 'skipped_admin' || data.payment_status === 'paid') {
        // Show success message
        const statusMessage = data.payment_status === 'skipped_admin' 
          ? 'Notarization created successfully (payment skipped - admin privilege).'
          : 'Notarization created successfully and payment processed.';
        
        addToast(
          `${statusMessage} Notarization hash: ${data.notarization_hash?.slice(0, 16)}...`,
          'success',
          6000
        );
        
        onNotarizationComplete?.(notarizationId);
        setTimeout(() => {
          onClose();
        }, 2000);
      } else {
        setPaymentRequired(true);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create notarization';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handlePaymentComplete = (transactionHash: string) => {
    if (notarizationId) {
      // Show success message with transaction hash
      addToast(
        `Payment processed successfully! Notarization completed. Transaction: ${transactionHash.slice(0, 10)}...${transactionHash.slice(-8)}`,
        'success',
        6000
      );
      
      onNotarizationComplete?.(notarizationId);
      setTimeout(() => {
        onClose();
      }, 2000);
    }
  };

  const canSkipPayment = user?.role === 'admin';

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-slate-100">
            <Shield className="h-5 w-5 text-purple-400" />
            Notarize Document
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            Create a blockchain notarization request. The document will be hashed and stored on-chain with signatures from required signers.
          </DialogDescription>
        </DialogHeader>

        {paymentRequired && notarizationId && dealId ? (
          <div className="space-y-4">
            <NotarizationPayment
              notarizationId={notarizationId}
              dealId={dealId}
              onPaymentComplete={handlePaymentComplete}
              onPaymentSkipped={() => {
                addToast(
                  'Notarization created successfully (payment skipped - admin privilege).',
                  'success',
                  6000
                );
                onNotarizationComplete?.(notarizationId);
                setTimeout(() => onClose(), 2000);
              }}
              onError={(err) => {
                setError(err);
                onError?.(err);
              }}
            />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Signers Section */}
            <div>
              <Label className="text-slate-300 mb-2 block">Required Signers</Label>
              <div className="space-y-3">
                {signers.map((address, index) => {
                  const isEditing = editingIndex === index;
                  
                  const handleStartEdit = () => {
                    setEditingIndex(index);
                    setEditedAddress(address);
                  };
                  
                  const handleSaveEdit = () => {
                    if (!editedAddress.trim()) {
                      setError('Please enter a wallet address');
                      return;
                    }
                    
                    if (!/^0x[a-fA-F0-9]{40}$/.test(editedAddress.trim())) {
                      setError('Invalid Ethereum address format');
                      return;
                    }
                    
                    const newAddress = editedAddress.trim().toLowerCase();
                    if (signers.some((s, i) => i !== index && s.toLowerCase() === newAddress)) {
                      setError('Address already added');
                      return;
                    }
                    
                    const updatedSigners = [...signers];
                    updatedSigners[index] = newAddress;
                    setSigners(updatedSigners);
                    setEditingIndex(null);
                    setEditedAddress('');
                    setError(null);
                  };
                  
                  const handleCancelEdit = () => {
                    setEditingIndex(null);
                    setEditedAddress('');
                    setError(null);
                  };
                  
                  return (
                    <div
                      key={address}
                      className="p-3 bg-slate-900 rounded-lg border border-slate-700"
                    >
                      {isEditing ? (
                        <div className="space-y-2">
                          <Input
                            placeholder="0x..."
                            value={editedAddress}
                            onChange={(e) => setEditedAddress(e.target.value)}
                            className="bg-slate-800 border-slate-600 text-slate-100 font-mono text-sm"
                          />
                          <div className="flex gap-2">
                            <Button
                              onClick={handleSaveEdit}
                              size="sm"
                              className="bg-purple-600 hover:bg-purple-700 text-white"
                            >
                              Save
                            </Button>
                            <Button
                              onClick={handleCancelEdit}
                              variant="outline"
                              size="sm"
                              className="border-slate-700"
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 flex-1">
                            <Wallet className="h-4 w-4 text-slate-400" />
                            <span className="text-sm font-mono text-slate-300">
                              {address.slice(0, 6)}...{address.slice(-4)}
                            </span>
                            {address.toLowerCase() === account?.toLowerCase() && (
                              <Badge variant="outline" className="text-xs">
                                You
                              </Badge>
                            )}
                          </div>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={handleStartEdit}
                              className="h-8 w-8 p-0 text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                              title="Edit address"
                            >
                              <PenTool className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRemoveSigner(address)}
                              className="h-8 w-8 p-0 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                              title="Remove signer"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}

                <div className="flex gap-2">
                  <Input
                    placeholder="0x..."
                    value={newSignerAddress}
                    onChange={(e) => setNewSignerAddress(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleAddSigner();
                      }
                    }}
                    className="bg-slate-900 border-slate-700 text-slate-100 font-mono text-sm"
                  />
                  <Button
                    onClick={handleAddSigner}
                    variant="outline"
                    size="sm"
                    className="border-slate-700"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add
                  </Button>
                </div>

                {!isConnected && (
                  <div className="bg-yellow-900/20 border border-yellow-500/50 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-yellow-400 mb-2">
                      <AlertCircle className="h-4 w-4" />
                      <span className="text-sm font-semibold">Wallet Not Connected</span>
                    </div>
                    <p className="text-xs text-slate-400 mb-3">
                      Connect your wallet to automatically add your address as a signer.
                    </p>
                    <Button
                      onClick={handleConnectWallet}
                      variant="outline"
                      size="sm"
                      className="border-yellow-500/50 text-yellow-400 hover:bg-yellow-900/20"
                    >
                      <Wallet className="h-4 w-4 mr-2" />
                      Connect Wallet
                    </Button>
                  </div>
                )}
              </div>
            </div>

            {/* Message Prefix */}
            <div>
              <Label className="text-slate-300 mb-2 block">Message Prefix</Label>
              <Input
                value={messagePrefix}
                onChange={(e) => setMessagePrefix(e.target.value)}
                className="bg-slate-900 border-slate-700 text-slate-100"
                placeholder="CreditNexus Notarization"
              />
            </div>

            {/* Auto-hydrate Deal (only for documents) */}
            {documentId && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="auto-hydrate"
                  checked={autoHydrateDeal}
                  onChange={(e) => setAutoHydrateDeal(e.target.checked)}
                  className="rounded border-slate-600 bg-slate-900"
                />
                <Label htmlFor="auto-hydrate" className="text-slate-300 text-sm cursor-pointer">
                  Automatically create or link to deal if document has no deal
                </Label>
              </div>
            )}

            {/* Info Box */}
            <div className="bg-blue-900/20 border border-blue-500/50 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-blue-400 mt-0.5" />
                <div className="text-xs text-slate-400">
                  <p className="mb-1">
                    <strong className="text-blue-400">Notarization Process:</strong>
                  </p>
                  <ul className="list-disc list-inside space-y-1 ml-2">
                    <li>Document content is hashed using SHA-256</li>
                    <li>Hash is stored on blockchain with required signatures</li>
                    <li>Each signer must sign a message with their wallet</li>
                    <li>Notarization is complete when all signers have signed</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-3">
                <div className="flex items-center gap-2 text-red-400">
                  <AlertCircle className="h-4 w-4" />
                  <p className="text-sm">{error}</p>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-700">
              <Button
                variant="outline"
                onClick={onClose}
                disabled={loading}
                className="border-slate-700"
              >
                Cancel
              </Button>
              {canSkipPayment && (
                <Button
                  variant="outline"
                  onClick={() => handleCreateNotarization(true)}
                  disabled={loading || signers.length === 0}
                  className="border-yellow-500/50 text-yellow-400 hover:bg-yellow-900/20"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Shield className="h-4 w-4 mr-2" />
                      Skip Payment (Admin)
                    </>
                  )}
                </Button>
              )}
              <Button
                onClick={() => handleCreateNotarization(false)}
                disabled={loading || signers.length === 0}
                className="bg-purple-600 hover:bg-purple-700 text-white"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Shield className="h-4 w-4 mr-2" />
                    Create Notarization
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
