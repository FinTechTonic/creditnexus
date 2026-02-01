"use client"

/**
 * CreditNexus Onboarding - Landing Page
 * Multi-step onboarding flow for MCP setup
 */

import { useState } from 'react'
import Link from 'next/link'

export default function HomePage() {
  const [walletConnected, setWalletConnected] = useState(false)
  const [walletAddress, setWalletAddress] = useState<string>('')

  const connectWallet = async () => {
    // TODO: Implement MetaMask connection
    // using wagmi/viem

    if (typeof window.ethereum !== 'undefined') {
      try {
        const accounts = await window.ethereum.request({
          method: 'eth_requestAccounts'
        })
        setWalletAddress(accounts[0])
        setWalletConnected(true)
      } catch (error) {
        console.error('Wallet connection failed:', error)
      }
    } else {
      alert('Please install MetaMask!')
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            CreditNexus MCP
          </h1>
          <p className="text-xl text-gray-600">
            Payment-protected tools for AI agents
          </p>
        </div>

        {/* Onboarding Steps */}
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-2xl font-semibold mb-6">Get Started</h2>

            {/* Step 1: Connect Wallet */}
            <div className="mb-8">
              <div className="flex items-center mb-4">
                <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold mr-3">
                  1
                </div>
                <h3 className="text-lg font-semibold">Connect Your Wallet</h3>
              </div>

              {!walletConnected ? (
                <button
                  onClick={connectWallet}
                  className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 px-6 rounded-lg transition"
                >
                  Connect MetaMask
                </button>
              ) : (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-green-800 font-semibold">✓ Wallet Connected</p>
                  <p className="text-sm text-gray-600 mt-1 font-mono">
                    {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
                  </p>
                </div>
              )}
            </div>

            {/* Step 2: Fund Wallet */}
            <div className="mb-8">
              <div className="flex items-center mb-4">
                <div className="w-8 h-8 bg-gray-300 text-white rounded-full flex items-center justify-center font-bold mr-3">
                  2
                </div>
                <h3 className="text-lg font-semibold">Fund Your Wallet</h3>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div>
                  <p className="text-sm font-semibold mb-2">Aptos Testnet USDC:</p>
                  <a
                    href="https://faucet.circle.com"
                    target="_blank"
                    className="text-blue-500 hover:underline text-sm"
                  >
                    Circle Faucet →
                  </a>
                </div>
                <div>
                  <p className="text-sm font-semibold mb-2">Base Sepolia USDC:</p>
                  <a
                    href="https://faucet.circle.com"
                    target="_blank"
                    className="text-blue-500 hover:underline text-sm"
                  >
                    Circle Faucet →
                  </a>
                </div>
              </div>
            </div>

            {/* Step 3: Get MCP Snippet */}
            <div className="mb-8">
              <div className="flex items-center mb-4">
                <div className="w-8 h-8 bg-gray-300 text-white rounded-full flex items-center justify-center font-bold mr-3">
                  3
                </div>
                <h3 className="text-lg font-semibold">Get MCP Config</h3>
              </div>

              {walletConnected ? (
                <Link
                  href="/snippet"
                  className="block w-full bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-6 rounded-lg transition text-center"
                >
                  Generate MCP Snippet →
                </Link>
              ) : (
                <button
                  disabled
                  className="w-full bg-gray-300 text-gray-500 font-bold py-3 px-6 rounded-lg cursor-not-allowed"
                >
                  Connect wallet first
                </button>
              )}
            </div>
          </div>

          {/* Info Cards */}
          <div className="grid md:grid-cols-2 gap-6 mt-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-semibold mb-2">🔧 Available Tools</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Stock Prediction (6¢)</li>
                <li>• Backtest (6¢)</li>
                <li>• People Service (45¢)</li>
                <li>• Open Bank Account ($3.65)</li>
              </ul>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-semibold mb-2">💳 Payment Networks</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Aptos Testnet (fast, low fees)</li>
                <li>• Base Sepolia (Ethereum L2)</li>
                <li>• USDC payments only</li>
                <li>• Instant settlement</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

// TypeScript declarations for window.ethereum
declare global {
  interface Window {
    ethereum?: {
      request: (args: { method: string; params?: any[] }) => Promise<any>
      isMetaMask?: boolean
    }
  }
}
