import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWallet } from '@/context/WalletContext';
import { useAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MetaMaskConnect } from '@/components/MetaMaskConnect';
import { 
  Wallet, 
  CheckCircle, 
  AlertCircle, 
  Loader2,
  ArrowRight,
  Shield
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

export function MetaMaskLogin() {
  const navigate = useNavigate();
  const { isConnected, account, signMessage } = useWallet();
  const { login, user } = useAuth();
  const [authenticating, setAuthenticating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<'connect' | 'sign' | 'authenticate' | 'success'>('connect');

  useEffect(() => {
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  useEffect(() => {
    if (isConnected && account && step === 'connect') {
      setStep('sign');
    }
  }, [isConnected, account, step]);

  const handleAuthenticate = async () => {
    if (!account) {
      setError('Please connect your wallet first');
      return;
    }

    setAuthenticating(true);
    setError(null);
    setStep('authenticate');

    try {
      // Step 1: Get nonce from server
      const nonceResponse = await fetchWithAuth('/api/auth/wallet/nonce', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: account }),
      });

      if (!nonceResponse.ok) {
        throw new Error('Failed to get authentication nonce');
      }

      const { nonce: _nonce, message } = await nonceResponse.json(); // nonce unused - prefix with _

      // Step 2: Sign message with MetaMask
      const signature = await signMessage(message);

      // Step 3: Authenticate with server
      const authResponse = await fetch('/api/auth/wallet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: account,
          signature,
          message,
        }),
      });

      if (!authResponse.ok) {
        const errorData = await authResponse.json();
        throw new Error(errorData.detail || 'Authentication failed');
      }

      const { access_token, refresh_token, user: userData } = await authResponse.json();

      // Step 4: Store tokens and update auth context
      localStorage.setItem('access_token', access_token);
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token);
      }

      await login(userData);
      setStep('success');

      // Navigate to dashboard after short delay
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
      setStep('sign');
    } finally {
      setAuthenticating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[var(--surface-gradient-start)] via-[var(--surface-panel)] to-[var(--surface-gradient-end)] text-[var(--color-foreground)] flex items-center justify-center py-12 px-4">
      <div className="max-w-md w-full">
        <Card className="surface-panel">
          <CardHeader className="text-center">
            <div className="w-16 h-16 bg-[var(--color-primary)]/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <Wallet className="h-8 w-8 text-[var(--color-primary)]" />
            </div>
            <CardTitle className="text-2xl">MetaMask Login</CardTitle>
            <CardDescription className="text-[var(--color-muted-foreground)]">
              Connect your wallet to sign in securely
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Step 1: Connect Wallet */}
            {step === 'connect' && (
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold mb-2">Step 1: Connect Your Wallet</h3>
                  <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
                    Click the button below to connect your MetaMask wallet
                  </p>
                  <MetaMaskConnect onConnect={() => setStep('sign')} />
                </div>
              </div>
            )}

            {/* Step 2: Sign Message */}
            {step === 'sign' && isConnected && account && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle className="h-5 w-5" />
                  <span className="text-sm">Wallet Connected</span>
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">Step 2: Authenticate</h3>
                  <p className="text-sm text-[var(--color-muted-foreground)] mb-4">
                    Sign a message to verify ownership of your wallet address
                  </p>
                  <Button
                    onClick={handleAuthenticate}
                    disabled={authenticating}
                    className="w-full bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-[var(--color-on-primary)]"
                  >
                    {authenticating ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Authenticating...
                      </>
                    ) : (
                      <>
                        <Shield className="h-4 w-4 mr-2" />
                        Sign & Authenticate
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Authenticating */}
            {step === 'authenticate' && (
              <div className="text-center space-y-4">
                <Loader2 className="h-8 w-8 animate-spin text-[var(--color-primary)] mx-auto" />
                <p className="text-[var(--color-muted-foreground)]">Authenticating...</p>
              </div>
            )}

            {/* Step 4: Success */}
            {step === 'success' && (
              <div className="text-center space-y-4">
                <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto">
                  <CheckCircle className="h-8 w-8 text-emerald-400" />
                </div>
                <h3 className="text-lg font-semibold">Authentication Successful!</h3>
                <p className="text-sm text-[var(--color-muted-foreground)]">Redirecting to dashboard...</p>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="p-4 bg-[var(--color-destructive)]/20 border border-[var(--color-destructive)]/50 rounded-lg">
                <div className="flex items-center gap-2 text-[var(--color-destructive)]">
                  <AlertCircle className="h-5 w-5" />
                  <p className="text-sm">{error}</p>
                </div>
              </div>
            )}

            {/* Instructions */}
            <div className="border-t border-[var(--color-border)] pt-6">
              <h4 className="text-sm font-semibold mb-3">How it works:</h4>
              <ul className="space-y-2 text-sm text-[var(--color-muted-foreground)]">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400">1.</span>
                  <span>Connect your MetaMask wallet</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400">2.</span>
                  <span>Sign a message to verify wallet ownership</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400">3.</span>
                  <span>Access your account securely</span>
                </li>
              </ul>
            </div>

            {/* Alternative Login */}
            <div className="border-t border-[var(--color-border)] pt-6">
              <p className="text-sm text-[var(--color-muted-foreground)] text-center mb-3">
                Don't have a wallet?
              </p>
              <Button
                variant="outline"
                className="w-full border-[var(--color-border)] text-[var(--color-muted-foreground)] hover:bg-[var(--surface-panel)]"
                onClick={() => navigate('/login')}
              >
                Use Email Login
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
