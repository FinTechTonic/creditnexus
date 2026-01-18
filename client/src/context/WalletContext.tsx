import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

interface WalletState {
  isConnected: boolean;
  account: string | null;
  chainId: number | null;
  provider: any | null;
  error: string | null;
}

interface WalletContextType extends WalletState {
  connect: () => Promise<void>;
  disconnect: () => void;
  switchChain?: (chainId: number) => Promise<void>;
  signMessage: (message: string) => Promise<string>;
}

const WalletContext = createContext<WalletContextType | undefined>(undefined);

export function WalletProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WalletState>({
    isConnected: false,
    account: null,
    chainId: null,
    provider: null,
    error: null,
  });

  // Check if wallet is already connected on mount
  useEffect(() => {
    checkConnection();
    
    // Listen for account changes
    if (typeof window.ethereum !== 'undefined' && window.ethereum.on) {
      window.ethereum.on('accountsChanged', handleAccountsChanged as (accounts: unknown) => void);
      window.ethereum.on('chainChanged', handleChainChanged as (chainId: unknown) => void);
      window.ethereum.on('disconnect', handleDisconnect);
      window.ethereum.on('connect', handleConnect as (connectInfo: unknown) => void);
    }

    // Periodic connection check (hot reload support)
    const connectionCheckInterval = setInterval(() => {
      if (state.isConnected) {
        checkConnection();
      }
    }, 30000); // Check every 30 seconds

    return () => {
      if (typeof window.ethereum !== 'undefined' && window.ethereum.removeListener) {
        window.ethereum.removeListener('accountsChanged', handleAccountsChanged as (accounts: unknown) => void);
        window.ethereum.removeListener('chainChanged', handleChainChanged as (chainId: unknown) => void);
        window.ethereum.removeListener('disconnect', handleDisconnect);
        window.ethereum.removeListener('connect', handleConnect as (connectInfo: unknown) => void);
      }
      clearInterval(connectionCheckInterval);
    };
  }, [state.isConnected]);

  const checkConnection = async () => {
    if (typeof window.ethereum === 'undefined') {
      setState(prev => ({ ...prev, error: 'MetaMask is not installed' }));
      return;
    }

    try {
      const accounts = await window.ethereum.request({ method: 'eth_accounts' }) as string[];
      if (Array.isArray(accounts) && accounts.length > 0) {
        const chainId = await window.ethereum.request({ method: 'eth_chainId' }) as string;
        const currentAccount = accounts[0];
        const currentChainId = parseInt(chainId, 16);
        
        // Only update state if connection status changed
        setState(prev => {
          if (prev.isConnected && prev.account === currentAccount && prev.chainId === currentChainId) {
            return prev; // No change needed
          }
          return {
            isConnected: true,
            account: currentAccount,
            chainId: currentChainId,
            provider: window.ethereum,
            error: null,
          };
        });
      } else {
        // No accounts - disconnect if previously connected
        setState(prev => {
          if (prev.isConnected) {
            return {
              isConnected: false,
              account: null,
              chainId: null,
              provider: null,
              error: null,
            };
          }
          return prev;
        });
      }
    } catch (err) {
      // Only update error if it's a new error
      setState(prev => {
        const errorMessage = err instanceof Error ? err.message : 'Failed to check connection';
        if (prev.error === errorMessage) {
          return prev; // No change needed
        }
        return {
          ...prev,
          error: errorMessage,
        };
      });
    }
  };

  const handleAccountsChanged = (accounts: unknown) => {
    if (!Array.isArray(accounts) || accounts.length === 0) {
      setState({
        isConnected: false,
        account: null,
        chainId: null,
        provider: null,
        error: null,
      });
    } else {
      setState(prev => ({
        ...prev,
        account: accounts[0],
      }));
    }
  };

  const handleChainChanged = (chainId: unknown) => {
    const chainIdStr = typeof chainId === 'string' ? chainId : String(chainId);
    setState(prev => ({
      ...prev,
      chainId: parseInt(chainIdStr, 16),
    }));
  };

  const handleDisconnect = () => {
    setState({
      isConnected: false,
      account: null,
      chainId: null,
      provider: null,
      error: null,
    });
  };

  const handleConnect = async (connectInfo: unknown) => {
    // Auto-reconnect when MetaMask reconnects
    try {
      if (!window.ethereum) return;
      const accounts = await window.ethereum.request({ method: 'eth_accounts' });
      if (accounts && Array.isArray(accounts) && accounts.length > 0) {
        const connectInfoObj = connectInfo as { chainId?: string };
        const chainId = connectInfoObj?.chainId || '0x1';
        setState(prev => ({
          ...prev,
          isConnected: true,
          account: accounts[0] as string,
          chainId: parseInt(chainId, 16),
          provider: window.ethereum,
          error: null,
        }));
      }
    } catch (err) {
      // Silently fail - connection check will retry
      console.warn('Auto-reconnect failed:', err);
    }
  };

  const connect = async () => {
    if (typeof window.ethereum === 'undefined') {
      setState(prev => ({ ...prev, error: 'MetaMask is not installed' }));
      throw new Error('MetaMask is not installed');
    }

    try {
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts',
      }) as string[];

      if (!Array.isArray(accounts) || accounts.length === 0) {
        throw new Error('No accounts found');
      }

      const chainId = await window.ethereum.request({ method: 'eth_chainId' }) as string;

      setState({
        isConnected: true,
        account: accounts[0],
        chainId: parseInt(chainId, 16),
        provider: window.ethereum,
        error: null,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect wallet';
      setState(prev => ({ ...prev, error: errorMessage }));
      throw err;
    }
  };

  const disconnect = () => {
    setState({
      isConnected: false,
      account: null,
      chainId: null,
      provider: null,
      error: null,
    });
  };

  const switchChain = async (chainId: number) => {
    if (!state.provider) {
      throw new Error('Wallet not connected');
    }

    if (typeof window.ethereum === 'undefined') {
      throw new Error('Ethereum provider not available');
    }

    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: `0x${chainId.toString(16)}` }],
      });
    } catch (err) {
      // If chain doesn't exist, try to add it
      if ((err as { code?: number }).code === 4902) {
        // Chain not added, would need to add it here
        throw new Error('Chain not supported');
      }
      throw err;
    }
  };

  const signMessage = async (message: string): Promise<string> => {
    if (!state.account || !state.provider || !window.ethereum) {
      throw new Error('Wallet not connected');
    }

    try {
      const signature = await window.ethereum.request({
        method: 'personal_sign',
        params: [message, state.account],
      });
      return signature as string;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to sign message');
    }
  };

  return (
    <WalletContext.Provider
      value={{
        ...state,
        connect,
        disconnect,
        switchChain,
        signMessage,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  const context = useContext(WalletContext);
  if (context === undefined) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
}

// Extend Window interface for MetaMask
declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
      on: (event: string, handler: (...args: unknown[]) => void) => void;
      removeListener: (event: string, handler: (...args: unknown[]) => void) => void;
    };
  }
}
