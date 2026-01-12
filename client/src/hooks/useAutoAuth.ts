"""Auto-authentication hook for MetaMask hot login."""

import { useEffect, useState, useCallback } from 'react'
import { useWallet } from '@/context/WalletContext'
import { useAuth } from '@/context/AuthContext'

interface AutoAuthState {
  attempting: boolean
  error: string | null
  requiresSignup: boolean
  signupWallet?: string
}

export function useAutoAuth() {
  const { isConnected, account } = useWallet()
  const { user, login, isAuthenticated } = useAuth()
  const [state, setState] = useState<AutoAuthState>({
    attempting: false,
    error: null,
    requiresSignup: false
  })

  const attemptAutoLogin = useCallback(async (walletAddress: string) => {
    setState(prev => ({ ...prev, attempting: true, error: null }))

    try {
      const response = await fetch('/api/auth/wallet/auto-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: walletAddress })
      })

      const data = await response.json()

      if (response.ok && data.status === 'success') {
        // Store tokens
        localStorage.setItem('access_token', data.access_token)
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token)
        }

        // Update auth context
        await login(data.user)
        
        setState(prev => ({ ...prev, attempting: false }))
        return { success: true }
      } else if (data.status === 'signup_required') {
        setState({
          attempting: false,
          error: null,
          requiresSignup: true,
          signupWallet: walletAddress
        })
        return { success: false, requiresSignup: true, walletAddress }
      } else {
        setState({
          attempting: false,
          error: data.detail || 'Auto-login failed',
          requiresSignup: false
        })
        return { success: false, error: data.detail }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Auto-login failed'
      setState({
        attempting: false,
        error: errorMsg,
        requiresSignup: false
      })
      return { success: false, error: errorMsg }
    }
  }, [login])

  const attemptSignup = useCallback(async (
    walletAddress: string,
    signature: string,
    message: string,
    email?: string,
    displayName?: string
  ) => {
    setState(prev => ({ ...prev, attempting: true, error: null }))

    try {
      const response = await fetch('/api/auth/wallet/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: walletAddress,
          signature,
          message,
          email,
          display_name: displayName
        })
      })

      const data = await response.json()

      if (response.ok && data.status === 'success') {
        localStorage.setItem('access_token', data.access_token)
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token)
        }

        await login(data.user)
        
        setState(prev => ({ ...prev, attempting: false, requiresSignup: false }))
        return { success: true }
      } else {
        setState({
          attempting: false,
          error: data.detail || 'Signup failed',
          requiresSignup: true,
          signupWallet: walletAddress
        })
        return { success: false, error: data.detail }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Signup failed'
      setState({
        attempting: false,
        error: errorMsg,
        requiresSignup: true,
        signupWallet: walletAddress
      })
      return { success: false, error: errorMsg }
    }
  }, [login])

  // Auto-login when wallet is connected but user is not logged in
  useEffect(() => {
    if (isConnected && account && !user && !state.attempting) {
      attemptAutoLogin(account)
    }
  }, [isConnected, account, user, state.attempting, attemptAutoLogin])

  // Check for persisted wallet on mount
  useEffect(() => {
    const persistedAccount = localStorage.getItem('last_connected_wallet')
    if (persistedAccount && !isConnected && !account && !user) {
      // Wallet was previously connected, prompt user to reconnect
      console.log('Previously connected wallet found:', persistedAccount)
    }
  }, [isConnected, account, user])

  // Persist wallet on connection
  useEffect(() => {
    if (account) {
      localStorage.setItem('last_connected_wallet', account)
    } else if (!isConnected) {
      localStorage.removeItem('last_connected_wallet')
    }
  }, [account, isConnected])

  const clearState = useCallback(() => {
    setState({
      attempting: false,
      error: null,
      requiresSignup: false
    })
  }, [])

  return {
    ...state,
    attemptAutoLogin,
    attemptSignup,
    clearState,
    isAuthenticated
  }
}
