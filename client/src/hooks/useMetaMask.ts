import { useState, useCallback } from 'react'

interface MetaMaskAccount {
  address: string
  chainId?: number
}

interface UseMetaMaskReturn {
  account: MetaMaskAccount | null
  connect: () => Promise<string | null>
  signMessage: (message: string) => Promise<string | null>
  disconnect: () => Promise<void>
  isConnected: boolean
  isInstalled: boolean
}

declare global {
  interface Window {
    ethereum?: any
  web3?: any
  injectedWeb3?: any
  web3_currentProvider?: any
  ethereum_autoRefreshOnNetworkChange?: boolean
  ethereum_isMetaMask?: boolean
  ethereum_selectedAddress?: string
  ethereum_chainId?: string
  ethereum_requestAccounts?: () => Promise<any>
  ethereum_sendAsync?: (payload: any) => Promise<any>
  ethereum_signMessage?: (params: { from: string; data: string }) => Promise<any>
  ethereum_on?: { (event: string, handler: (args: any) => void) => void }
  ethereum_removeListener?: (event: string, handler: (args: any) => void) => void
  ethereum_autoRefreshOnNetworkChange?: boolean
  ethereum_isMetaMask?: boolean
  ethereum_networkVersion?: string
  ethereum_selectedAddress?: string
  ethereum_chainId?: string
  ethereum_requestAccounts?: () => Promise<any>
  ethereum_sendAsync?: (payload: any) => Promise<any>
  ethereum_signMessage?: (params: { from: string; data: string }) => Promise<any>
  ethereum_on?: { (event: string, handler: (args: any) => void) => void }
  ethereum_removeListener?: (event: string, handler: (args: any) => void) => void }
}

export function useMetaMask(): UseMetaMaskReturn {
  const [account, setAccount] = useState<MetaMaskAccount | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  const isInstalled = Boolean(
    typeof window !== 'undefined' && 
    (window.ethereum || window.web3 || window.injectedWeb3 || window.web3_currentProvider)
  )

  const connect = useCallback(async (): Promise<string | null> => {
    if (!isInstalled) {
      console.error('MetaMask is not installed')
      return null
    }

    const ethereum = window.ethereum || window.web3 || window.injectedWeb3 || window.web3_currentProvider

    try {
      const accounts = await ethereum.requestAccounts?.({ method: 'eth_requestAccounts' })
      
      if (accounts && accounts.length > 0) {
        const address = accounts[0]
        const chainId = await ethereum.request?.({ method: 'eth_chainId' })
        
        setAccount({
          address: address.toLowerCase(),
          chainId: parseInt(chainId, 16)
        })
        setIsConnected(true)
        console.log('Connected to MetaMask:', address)
        
        return address.toLowerCase()
      }
      
      return null
    } catch (error: any) {
      console.error('Failed to connect to MetaMask:', error)
      return null
    }
  }, [isInstalled])

  const signMessage = useCallback(async (message: string): Promise<string | null> => {
    if (!account) {
      console.error('No connected account')
      return null
    }

    if (!isInstalled) {
      console.error('MetaMask is not installed')
      return null
    }

    const ethereum = window.ethereum || window.web3 || window.injectedWeb3 || window.web3_currentProvider

    try {
      const signature = await ethereum.signMessage?.({
        from: account.address,
        data: message
      })

      if (signature) {
        console.log('Message signed successfully')
        return signature
      }
      
      return null
    } catch (error: any) {
      if (error.code === 4001) {
        console.error('User rejected signature request')
      } else {
        console.error('Failed to sign message:', error)
      }
      return null
    }
  }, [account, isInstalled])

  const disconnect = useCallback(async (): Promise<void> => {
    setAccount(null)
    setIsConnected(false)
    console.log('Disconnected from MetaMask')
  }, [])

  // Listen for account changes
  useCallback(() => {
    const handleAccountsChanged = (accounts: string[]) => {
      if (accounts && accounts.length > 0) {
        const newAddress = accounts[0].toLowerCase()
        if (account?.address !== newAddress) {
          const ethereum = window.ethereum || window.web3 || window.injectedWeb3 || window.web3_currentProvider
          const chainId = ethereum.request?.({ method: 'eth_chainId' })
          
          setAccount({
            address: newAddress,
            chainId: chainId ? parseInt(chainId, 16) : undefined
          })
          setIsConnected(true)
        }
      } else {
        setAccount(null)
        setIsConnected(false)
      }
    }

    const ethereum = window.ethereum || window.web3 || window.injectedWeb3 || window.web3_currentProvider
    if (ethereum && ethereum.on) {
      ethereum.on('accountsChanged', handleAccountsChanged)
      
      return () => {
        if (ethereum && ethereum.removeListener) {
          ethereum.removeListener('accountsChanged', handleAccountsChanged)
        }
      }
    }
  }, [account])

  return {
    account,
    connect,
    signMessage,
    disconnect,
    isConnected,
    isInstalled
  }
}
