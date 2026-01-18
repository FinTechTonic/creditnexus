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
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  PenTool,
  Mail,
  Plus,
  X,
  Loader2,
  AlertCircle,
  // CheckCircle removed - unused
  Info,
  User,
  // Edit removed - unused
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { useToast } from '@/components/ui/toast';

interface Signer {
  name: string;
  email: string;
  role?: string;
}

interface SignatureRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: number;
  onSignatureRequested?: (signatureId: number) => void;
  onError?: (error: string) => void;
}

export function SignatureRequestModal({
  isOpen,
  onClose,
  documentId,
  onSignatureRequested,
  onError,
}: SignatureRequestModalProps) {
  // const { user } = useAuth(); // user unused
  const { addToast } = useToast();
  const [signers, setSigners] = useState<Signer[]>([]);
  const [newSigner, setNewSigner] = useState({ name: '', email: '', role: '' });
  const [subject, setSubject] = useState('Please sign the document');
  const [message, setMessage] = useState('Please review and sign the attached document');
  const [expiresInDays, setExpiresInDays] = useState(30);
  const [urgency, setUrgency] = useState<'standard' | 'time_sensitive' | 'complex'>('standard');
  const [autoDetectSigners, setAutoDetectSigners] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detectingSigners, setDetectingSigners] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editedSigner, setEditedSigner] = useState<Signer | null>(null);

  useEffect(() => {
    if (isOpen && autoDetectSigners && signers.length === 0) {
      detectSigners();
    }
    if (!isOpen) {
      // Reset state when modal closes
      setEditingIndex(null);
      setEditedSigner(null);
      setError(null);
    }
  }, [isOpen, autoDetectSigners]);

  const detectSigners = async () => {
    setDetectingSigners(true);
    setError(null);
    
    try {
      // Get document CDM data to extract signers
      const docResponse = await fetchWithAuth(`/api/documents/${documentId}?include_cdm_data=true`);
      if (!docResponse.ok) {
        throw new Error('Failed to fetch document data');
      }
      
      const docData = await docResponse.json();
      const cdmData = docData.cdm_data || docData.source_cdm_data;
      
      if (cdmData && cdmData.parties) {
        const detectedSigners: Signer[] = [];
        const parties = Array.isArray(cdmData.parties) ? cdmData.parties : [];
        
        for (const party of parties) {
          const roles = party.roles || [];
          const roleStr = Array.isArray(roles) ? roles.join(', ') : String(roles);
          
          // Only include parties that typically need to sign
          if (roleStr.toLowerCase().includes('borrower') || 
              roleStr.toLowerCase().includes('lender') ||
              roleStr.toLowerCase().includes('agent') ||
              roleStr.toLowerCase().includes('guarantor')) {
            detectedSigners.push({
              name: party.name || 'Unknown',
              email: party.contact?.email || `${party.name?.toLowerCase().replace(/\s+/g, '.')}@example.com`,
              role: roleStr,
            });
          }
        }
        
        if (detectedSigners.length > 0) {
          setSigners(detectedSigners);
        }
      }
    } catch (err) {
      console.error('Error detecting signers:', err);
      // Don't show error, just continue with manual entry
    } finally {
      setDetectingSigners(false);
    }
  };

  const handleAddSigner = () => {
    if (!newSigner.name.trim() || !newSigner.email.trim()) {
      setError('Name and email are required');
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(newSigner.email.trim())) {
      setError('Invalid email format');
      return;
    }

    setSigners([...signers, { ...newSigner, email: newSigner.email.trim() }]);
    setNewSigner({ name: '', email: '', role: '' });
    setError(null);
  };

  const handleRemoveSigner = (index: number) => {
    setSigners(signers.filter((_, i) => i !== index));
  };

  const handleRequestSignature = async () => {
    if (signers.length === 0 && !autoDetectSigners) {
      setError('At least one signer is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetchWithAuth(`/api/documents/${documentId}/signatures/request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          signers: signers.length > 0 ? signers : undefined,
          auto_detect_signers: autoDetectSigners && signers.length === 0,
          expires_in_days: expiresInDays,
          subject: subject,
          message: message,
          urgency: urgency,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail?.message || errorData.detail || 'Failed to request signature');
      }

      const data = await response.json();
      const signatureId = data.signature.id;
      const signerCount = data.signature.signers?.length || signers.length;
      
      // Show success message
      addToast(
        `Signature request sent successfully! ${signerCount} signer${signerCount > 1 ? 's' : ''} will receive an email to sign the document.`,
        'success',
        6000
      );
      
      onSignatureRequested?.(signatureId);
      
      // Close modal after short delay
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to request signature';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-slate-100">
            <PenTool className="h-5 w-5 text-blue-400" />
            Request Document Signatures
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            Request digital signatures for this document via DigiSigner. Signers will receive an email with a link to sign.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Auto-detect option */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto-detect"
              checked={autoDetectSigners}
              onChange={(e) => setAutoDetectSigners(e.target.checked)}
              className="rounded border-slate-600 bg-slate-900"
            />
            <Label htmlFor="auto-detect" className="text-slate-300 text-sm cursor-pointer">
              Auto-detect signers from document CDM data
            </Label>
            {detectingSigners && (
              <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
            )}
          </div>

          {/* Signers Section */}
          <div>
            <Label className="text-slate-300 mb-2 block">Signers</Label>
            <div className="space-y-3">
              {signers.map((signer, index) => {
                const isEditing = editingIndex === index;
                // const _currentEditedSigner = isEditing ? (editedSigner || signer) : signer; // unused
                
                const handleStartEdit = () => {
                  setEditingIndex(index);
                  setEditedSigner({ ...signer });
                };
                
                const handleSaveEdit = () => {
                  if (!editedSigner || !editedSigner.name.trim() || !editedSigner.email.trim()) {
                    setError('Name and email are required');
                    return;
                  }
                  
                  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                  if (!emailRegex.test(editedSigner.email.trim())) {
                    setError('Invalid email format');
                    return;
                  }
                  
                  const updatedSigners = [...signers];
                  updatedSigners[index] = { ...editedSigner, email: editedSigner.email.trim() };
                  setSigners(updatedSigners);
                  setEditingIndex(null);
                  setEditedSigner(null);
                  setError(null);
                };
                
                const handleCancelEdit = () => {
                  setEditingIndex(null);
                  setEditedSigner(null);
                  setError(null);
                };
                
                return (
                  <div
                    key={index}
                    className="p-3 bg-slate-900 rounded-lg border border-slate-700 space-y-2"
                  >
                    {isEditing ? (
                      <div className="space-y-2">
                        <Input
                          placeholder="Name"
                          value={editedSigner?.name || ''}
                          onChange={(e) => setEditedSigner(editedSigner ? { ...editedSigner, name: e.target.value } : null)}
                          className="bg-slate-800 border-slate-600 text-slate-100"
                        />
                        <Input
                          placeholder="Email"
                          type="email"
                          value={editedSigner?.email || ''}
                          onChange={(e) => setEditedSigner(editedSigner ? { ...editedSigner, email: e.target.value } : null)}
                          className="bg-slate-800 border-slate-600 text-slate-100"
                        />
                        <Input
                          placeholder="Role (optional)"
                          value={editedSigner?.role || ''}
                          onChange={(e) => setEditedSigner(editedSigner ? { ...editedSigner, role: e.target.value } : null)}
                          className="bg-slate-800 border-slate-600 text-slate-100"
                        />
                        <div className="flex gap-2">
                          <Button
                            onClick={handleSaveEdit}
                            size="sm"
                            className="bg-blue-600 hover:bg-blue-700 text-white"
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
                        <div className="flex items-center gap-3 flex-1">
                          <div className="w-10 h-10 rounded-full flex items-center justify-center bg-slate-700 text-slate-400">
                            <User className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <p className="text-slate-100 font-medium">{signer.name}</p>
                            <div className="flex items-center gap-2 text-sm text-slate-400">
                              <Mail className="h-3 w-3" />
                              {signer.email}
                              {signer.email.includes('@example.com') && (
                                <Badge variant="outline" className="text-xs text-yellow-400 border-yellow-500/50">
                                  Placeholder
                                </Badge>
                              )}
                            </div>
                            {signer.role && (
                              <Badge variant="outline" className="text-xs text-slate-400 mt-1">
                                {signer.role}
                              </Badge>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleStartEdit}
                            className="h-8 w-8 p-0 text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                            title="Edit signer"
                          >
                            <PenTool className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveSigner(index)}
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

              {signers.length === 0 && !detectingSigners && (
                <div className="text-center py-4 text-slate-400 text-sm">
                  {autoDetectSigners ? 'No signers detected. Add signers manually below.' : 'Add signers below'}
                </div>
              )}
              
              {signers.some(s => s.email.includes('@example.com')) && (
                <div className="bg-yellow-900/20 border border-yellow-500/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-yellow-400">
                    <AlertCircle className="h-4 w-4" />
                    <p className="text-sm">
                      Some signers have placeholder emails. Please edit them before sending.
                    </p>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-3 gap-2">
                <Input
                  placeholder="Name"
                  value={newSigner.name}
                  onChange={(e) => setNewSigner({ ...newSigner, name: e.target.value })}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && newSigner.name && newSigner.email) {
                      handleAddSigner();
                    }
                  }}
                  className="bg-slate-900 border-slate-700 text-slate-100"
                />
                <Input
                  placeholder="Email"
                  type="email"
                  value={newSigner.email}
                  onChange={(e) => setNewSigner({ ...newSigner, email: e.target.value })}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && newSigner.name && newSigner.email) {
                      handleAddSigner();
                    }
                  }}
                  className="bg-slate-900 border-slate-700 text-slate-100"
                />
                <div className="flex gap-2">
                  <Input
                    placeholder="Role (optional)"
                    value={newSigner.role}
                    onChange={(e) => setNewSigner({ ...newSigner, role: e.target.value })}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && newSigner.name && newSigner.email) {
                        handleAddSigner();
                      }
                    }}
                    className="bg-slate-900 border-slate-700 text-slate-100"
                  />
                  <Button
                    onClick={handleAddSigner}
                    variant="outline"
                    size="sm"
                    className="border-slate-700"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Email Settings */}
          <div>
            <Label className="text-slate-300 mb-2 block">Email Subject</Label>
            <Input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="bg-slate-900 border-slate-700 text-slate-100"
            />
          </div>

          <div>
            <Label className="text-slate-300 mb-2 block">Email Message</Label>
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              className="bg-slate-900 border-slate-700 text-slate-100"
            />
          </div>

          {/* Expiration */}
          <div>
            <Label className="text-slate-300 mb-2 block">Expires In (days)</Label>
            <Input
              type="number"
              min="1"
              max="90"
              value={expiresInDays}
              onChange={(e) => setExpiresInDays(parseInt(e.target.value) || 30)}
              className="bg-slate-900 border-slate-700 text-slate-100"
            />
          </div>

          {/* Urgency */}
          <div>
            <Label className="text-slate-300 mb-2 block">Urgency</Label>
            <select
              value={urgency}
              onChange={(e) => setUrgency(e.target.value as any)}
              className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-100"
            >
              <option value="standard">Standard</option>
              <option value="time_sensitive">Time Sensitive</option>
              <option value="complex">Complex</option>
            </select>
          </div>

          {/* Info Box */}
          <div className="bg-blue-900/20 border border-blue-500/50 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Info className="h-4 w-4 text-blue-400 mt-0.5" />
              <div className="text-xs text-slate-400">
                <p className="mb-1">
                  <strong className="text-blue-400">Signature Process:</strong>
                </p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>Signers will receive an email with a link to sign</li>
                  <li>They can sign the document electronically via DigiSigner</li>
                  <li>You'll be notified when all signers have completed signing</li>
                  <li>The signed document will be available for download</li>
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
            <Button
              onClick={handleRequestSignature}
              disabled={loading || signers.length === 0 || signers.some(s => !s.name.trim() || !s.email.trim() || s.email.includes('@example.com'))}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Requesting...
                </>
              ) : (
                <>
                  <PenTool className="h-4 w-4 mr-2" />
                  Request Signatures
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
