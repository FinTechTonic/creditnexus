/**
 * Enhanced verification page with file references.
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  DocumentIcon,
  FolderIcon
} from '@heroicons/react/24/outline'

interface VerificationData {
  verification_id: string
  deal_id: number
  deal_data: any
  cdm_payload: any
  verifier_info: any
  file_references: Array<{
    document_id: string
    filename: string
    category: string
    subdirectory: string
    size: number
    download_url: string
    title: string
  }>
  expires_at: string
}

export function VerificationPage() {
  const { payload } = useParams<{ payload: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<VerificationData | null>(null)

  useEffect(() => {
    if (payload) {
      loadVerificationFromPayload(payload)
    }
  }, [payload])

  const loadVerificationFromPayload = async (payload: string) => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/remote/verify/${payload}`)
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Invalid or expired verification link')
      }
      
      const result = await response.json()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load verification')
    } finally {
      setLoading(false)
    }
  }

  const handleAccept = async () => {
    if (!data) return

    // TODO: Implement actual accept endpoint call
    console.log('Accept verification:', data.verification_id)
    navigate('/verification/success')
  }

  const handleDecline = async () => {
    if (!data) return

    const reason = prompt('Please provide a reason for declining this verification:')
    if (!reason || reason.trim() === '') {
      setError('Reason is required')
      return
    }

    // TODO: Implement actual decline endpoint call
    console.log('Decline verification:', data.verification_id, reason)
    navigate('/verification/declined')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="max-w-md w-full">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <XCircleIcon className="h-10 w-10 text-red-600" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Verification Error</h2>
            <p className="text-gray-700">{error}</p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
          >
            Return to Home
          </button>
        </div>
      </div>
    )
  }

  const isExpired = data ? new Date(data.expires_at) < new Date() : false
  const isPending = data?.status === 'pending'
  const isAccepted = data?.status === 'accepted'
  const isDeclined = data?.status === 'declined'

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white shadow-lg rounded-lg overflow-hidden">
          {/* Header */}
          <div className={`px-6 py-4 ${
            isAccepted ? 'bg-green-50 border-b border-green-200' :
            isDeclined ? 'bg-red-50 border-b border-red-200' :
            isExpired ? 'bg-yellow-50 border-b border-yellow-200' :
            'bg-blue-50 border-b border-blue-200'
          }`}>
            <div className="flex items-center justify-between">
              {isAccepted ? (
                <CheckCircleIcon className="h-8 w-8 text-green-600 mr-3" />
              ) : isDeclined ? (
                <XCircleIcon className="h-8 w-8 text-red-600 mr-3" />
              ) : isExpired ? (
                <ExclamationTriangleIcon className="h-8 w-8 text-yellow-600 mr-3" />
              ) : (
                <FolderIcon className="h-8 w-8 text-blue-600 mr-3" />
              )}
              <h1 className="text-2xl font-bold text-gray-900">
                Deal Verification
              </h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                isAccepted ? 'bg-green-100 text-green-800' :
                isDeclined ? 'bg-red-100 text-red-800' :
                isExpired ? 'bg-yellow-100 text-yellow-800' :
                'bg-blue-100 text-blue-800'
              }`}>
                {data?.status?.toUpperCase() || 'PENDING'}
              </span>
            </div>
          </div>

          {/* Content */}
          <div className="px-6 py-6">
            {isPending && !isExpired ? (
              <div>
                <p className="text-gray-700 mb-6">
                  You have been asked to verify a deal. Please review the details below and accept or decline this verification request.
                </p>

                {/* Deal Information */}
                {data?.deal_id && (
                  <div className="bg-gray-50 rounded-lg p-4 mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Deal Information</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-gray-600">Deal ID</label>
                        <p className="text-gray-900 font-mono">{data.deal_id}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-600">Status</label>
                        <p className="text-gray-900">{data?.status}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* File References */}
                {data?.file_references && data.file_references.length > 0 && (
                  <div className="bg-blue-50 rounded-lg p-4 mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                      <DocumentIcon className="h-5 w-5 text-blue-600" />
                      Referenced Files
                    </h3>
                    <div className="space-y-2">
                      {data.file_references.map((file, idx) => (
                        <div key={idx} className="flex items-start gap-3 p-3 bg-white rounded border border-gray-200">
                          <a
                            href={file.download_url}
                            target="_blank"
                            className="text-blue-600 hover:underline flex-1"
                          >
                            <FolderIcon className="h-5 w-5 text-gray-400" />
                            <div className="flex-1">
                              <p className="text-sm font-medium text-gray-900">{file.title || file.filename}</p>
                              <p className="text-xs text-gray-500">
                                {file.category} • {(file.size / 1024).toFixed(1)} KB
                              </p>
                            </div>
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Verification Metadata */}
                {data?.verifier_info && Object.keys(data.verifier_info).length > 0 && (
                  <div className="bg-purple-50 rounded-lg p-4 mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Verification Details
                    </h3>
                    <pre className="text-sm">
                      {JSON.stringify(data.verifier_info, null, 2)}
                    </pre>
                  </div>
                )}

                {/* CDM Payload */}
                {data?.cdm_payload && Object.keys(data.cdm_payload).length > 0 && (
                  <div className="bg-slate-100 rounded-lg p-4 mb-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      CDM Payload
                    </h3>
                    <pre className="text-xs overflow-auto max-h-48 bg-slate-800 p-3 rounded font-mono">
                      {JSON.stringify(data.cdm_payload, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Expiration Notice */}
                <div className={`flex items-start p-4 rounded-lg mb-6 ${
                  new Date(data.expires_at) - new Date() < 24 * 60 * 60 * 1000
                    ? 'bg-yellow-50 border border-yellow-200'
                    : 'bg-gray-50 border border-gray-200'
                }`}>
                  <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 mr-3 mt-0.5" />
                  <div>
                    <p className="font-medium text-gray-900">
                      {isExpired
                        ? 'This verification link has expired'
                        : `Expires on ${new Date(data.expires_at).toLocaleString()}`
                      }
                    </p>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-4">
                  <button
                    onClick={handleAccept}
                    disabled={isExpired || !isPending}
                    className="flex-1 bg-green-600 text-white py-3 px-6 rounded-md hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  >
                    {isPending && !isExpired ? (
                      <>
                        <CheckCircleIcon className="h-5 w-5 mr-2" />
                        Accept Verification
                      </>
                    ) : isPending ? (
                      <>
                        <CheckCircleIcon className="h-5 w-5 mr-2" />
                        Verification Accepted
                      </>
                    ) : null}
                  </button>
                  <button
                    onClick={handleDecline}
                    disabled={isExpired || !isPending}
                    className="flex-1 bg-red-600 text-white py-3 px-6 rounded-md hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  >
                    {isPending && !isExpired ? (
                      <>
                        <XCircleIcon className="h-5 w-5 mr-2" />
                        Decline Verification
                      </>
                    ) : isPending ? (
                      <>
                        <XCircleIcon className="h-5 w-5 mr-2" />
                        Verification Declined
                      </>
                    ) : null}
                  </button>
                </div>
              </div>
            ) : null}

            {/* Accepted State */}
            {isAccepted && (
              <div className="text-center py-8">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-4">
                  <CheckCircleIcon className="h-12 w-12 text-green-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  Verification Accepted
                </h2>
                <p className="text-gray-700 mb-6">
                  Thank you for accepting this verification. The deal has been verified successfully.
                </p>
                {data.accepted_at && (
                  <p className="text-sm text-gray-600">
                    Accepted on {new Date(data.accepted_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}

            {/* Declined State */}
            {isDeclined && (
              <div className="text-center py-8">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-red-100 rounded-full mb-4">
                  <XCircleIcon className="h-12 w-12 text-red-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  Verification Declined
                </h2>
                <p className="text-gray-700 mb-2">
                  This verification has been declined.
                </p>
                {data.declined_reason && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                    <p className="font-medium text-gray-900 mb-1">Reason:</p>
                    <p className="text-gray-700">{data.declined_reason}</p>
                  </div>
                )}
                {data.declined_at && (
                  <p className="text-sm text-gray-600">
                    Declined on {new Date(data.declined_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}

            {/* Expired State */}
            {isExpired && (
              <div className="text-center py-8">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-yellow-100 rounded-full mb-4">
                  <ExclamationTriangleIcon className="h-12 w-12 text-yellow-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  Verification Link Expired
                </h2>
                <p className="text-gray-700">
                  This verification link has expired. Please contact the sender for a new verification link.
                </p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
            <div className="text-center text-sm text-gray-600">
              Powered by <span className="font-semibold">CreditNexus</span>
              {' '}{new Date().getFullYear()}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
