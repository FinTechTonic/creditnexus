"use client"

/**
 * MCP Config Snippet Generator
 * Generates personalized MCP config for Cursor/Claude Desktop
 */

import { useState, useEffect } from 'react'
import Link from 'next/link'

export default function SnippetPage() {
  const [walletAddress, setWalletAddress] = useState<string>('')
  const [apiToken, setApiToken] = useState<string>('')
  const [copied, setCopied] = useState(false)
  const [registered, setRegistered] = useState(false)

  useEffect(() => {
    // Get wallet address from localStorage or state
    // TODO: Implement proper state management
    const mockWallet = '0x1234...5678'
    setWalletAddress(mockWallet)

    // Generate API token
    const token = generateToken()
    setApiToken(token)
  }, [])

  const generateToken = () => {
    // Simple token generation (should be server-side in production)
    return 'cn_' + Math.random().toString(36).substring(2, 15)
  }

  const registerAgent = async () => {
    // TODO: Call verifier API to add wallet to allowlist
    try {
      const response = await fetch('http://localhost:4022/allowlist/agent/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: walletAddress,
          admin_key: 'hackathon_admin_key' // TODO: Secure this
        })
      })

      if (response.ok) {
        setRegistered(true)
      }
    } catch (error) {
      console.error('Agent registration failed:', error)
    }
  }

  const snippet = {
    mcpServers: {
      creditnexus: {
        command: "python",
        args: ["/path/to/demo/mcp_demo/mcp_server/server.py"],
        env: {
          CREDITNEXUS_API_URL: "http://localhost:8000",
          VERIFIER_URL: "http://localhost:4022",
          CREDITNEXUS_MCP_TOKEN: apiToken,
          USER_WALLET_ADDRESS: walletAddress
        }
      }
    }
  }

  const snippetString = JSON.stringify(snippet, null, 2)

  const copyToClipboard = () => {
    navigator.clipboard.writeText(snippetString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <Link href="/" className="text-blue-500 hover:underline mb-4 inline-block">
              ← Back to Onboarding
            </Link>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Your MCP Configuration
            </h1>
            <p className="text-gray-600">
              Copy this snippet to configure CreditNexus tools in Cursor or Claude Desktop
            </p>
          </div>

          {/* Registration Step */}
          {!registered && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
              <h2 className="text-lg font-semibold mb-4">⚠️ Register Your Agent First</h2>
              <p className="text-sm text-gray-700 mb-4">
                Before using the MCP tools, you need to register your wallet address with the verifier.
              </p>
              <button
                onClick={registerAgent}
                className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-6 rounded-lg transition"
              >
                Register Agent
              </button>
            </div>
          )}

          {registered && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-6">
              <p className="text-green-800 font-semibold">✓ Agent registered successfully!</p>
            </div>
          )}

          {/* MCP Snippet */}
          <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Cursor Configuration</h2>
              <button
                onClick={copyToClipboard}
                className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded transition"
              >
                {copied ? '✓ Copied!' : 'Copy'}
              </button>
            </div>

            <p className="text-sm text-gray-600 mb-4">
              Add this to <code className="bg-gray-100 px-2 py-1 rounded">~/.cursor/mcp.json</code>:
            </p>

            <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
              {snippetString}
            </pre>
          </div>

          {/* Instructions */}
          <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
            <h2 className="text-xl font-semibold mb-4">Setup Instructions</h2>

            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">For Cursor:</h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
                  <li>Copy the configuration above</li>
                  <li>Open or create <code className="bg-gray-100 px-2 py-1 rounded">~/.cursor/mcp.json</code></li>
                  <li>Paste the configuration</li>
                  <li>Update the path in "args" to match your local installation</li>
                  <li>Restart Cursor</li>
                  <li>CreditNexus tools will appear in your MCP tools list</li>
                </ol>
              </div>

              <div>
                <h3 className="font-semibold mb-2">For Claude Desktop:</h3>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
                  <li>Copy the configuration above</li>
                  <li>Open Claude Desktop config:
                    <ul className="list-disc list-inside ml-6 mt-1">
                      <li>macOS: <code className="bg-gray-100 px-2 py-1 rounded text-xs">~/Library/Application Support/Claude/claude_desktop_config.json</code></li>
                      <li>Windows: <code className="bg-gray-100 px-2 py-1 rounded text-xs">%APPDATA%\Claude\claude_desktop_config.json</code></li>
                    </ul>
                  </li>
                  <li>Paste the configuration</li>
                  <li>Update the path to match your installation</li>
                  <li>Restart Claude Desktop</li>
                </ol>
              </div>
            </div>
          </div>

          {/* Available Tools */}
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h2 className="text-xl font-semibold mb-4">Available Tools</h2>

            <div className="space-y-4">
              <div className="border-l-4 border-blue-500 pl-4">
                <h3 className="font-semibold">run_prediction</h3>
                <p className="text-sm text-gray-600">Stock price prediction • 6¢ • Aptos</p>
              </div>

              <div className="border-l-4 border-blue-500 pl-4">
                <h3 className="font-semibold">run_backtest</h3>
                <p className="text-sm text-gray-600">Strategy backtesting • 6¢ • Aptos</p>
              </div>

              <div className="border-l-4 border-purple-500 pl-4">
                <h3 className="font-semibold">people_service</h3>
                <p className="text-sm text-gray-600">People service (support, docs) • 45¢ • Aptos</p>
              </div>

              <div className="border-l-4 border-green-500 pl-4">
                <h3 className="font-semibold">open_bank_account</h3>
                <p className="text-sm text-gray-600">Open bank account via Plaid • $3.65 • Base</p>
              </div>
            </div>
          </div>

          {/* User Info */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">
              <strong>Your Wallet:</strong> <code className="font-mono">{walletAddress}</code>
            </p>
            <p className="text-sm text-gray-600 mt-1">
              <strong>API Token:</strong> <code className="font-mono">{apiToken}</code>
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
