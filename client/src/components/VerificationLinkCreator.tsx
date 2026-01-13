/**
 * Verification link creator component with file selection.
 */

import { useState, useEffect } from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Copy, Check, Share2, FileText, Loader2 } from 'lucide-react'

interface Document {
  id: number
  title: string
  filename: string
  category: string
  subdirectory: string
  size: number
}

interface VerificationLinkCreatorProps {
  dealId: number
  verificationId: string
  onLinkGenerated?: (link: string) => void
}

export function VerificationLinkCreator({
  dealId,
  verificationId,
  onLinkGenerated
}: VerificationLinkCreatorProps) {
  const [includeFiles, setIncludeFiles] = useState(true)
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [selectedDocuments, setSelectedDocuments] = useState<number[]>([])
  const [availableDocuments, setAvailableDocuments] = useState<Document[]>([])
  const [availableCategories, setAvailableCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [generatedLink, setGeneratedLink] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDocuments()
    loadCategories()
  }, [dealId])

  const loadDocuments = async () => {
    try {
      const response = await fetch(`/api/deals/${dealId}/documents`)
      if (response.ok) {
        const docs = await response.json()
        setAvailableDocuments(docs)
      }
    } catch (err) {
      console.error('Failed to load documents:', err)
    }
  }

  const loadCategories = async () => {
    try {
      const response = await fetch('/api/config/verification-file-categories')
      if (response.ok) {
        const data = await response.json()
        const categories = data.categories || []
        setAvailableCategories(categories)
        setSelectedCategories(categories) // Select all by default
      }
    } catch (err) {
      console.error('Failed to load categories:', err)
      // Use default categories
      setAvailableCategories(['legal', 'financial', 'compliance'])
      setSelectedCategories(['legal', 'financial', 'compliance'])
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateLink = async () => {
    setGenerating(true)
    setError(null)

    try {
      const response = await fetch(
        `/api/remote/verification/${verificationId}/generate-link`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            verification_id: verificationId,
            include_files: includeFiles,
            file_categories: includeFiles ? selectedCategories : null,
            file_document_ids: includeFiles ? selectedDocuments : null,
            expires_in_hours: 72
          })
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to generate link')
      }

      const data = await response.json()
      setGeneratedLink(data.link)
      onLinkGenerated?.(data.link)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate link')
    } finally {
      setGenerating(false)
    }
  }

  const handleCopy = async () => {
    if (generatedLink) {
      await navigator.clipboard.writeText(generatedLink)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleShare = async () => {
    if (generatedLink && navigator.share) {
      try {
        await navigator.share({
          title: 'Deal Verification Request',
          text: 'Please review and verify this deal.',
          url: generatedLink
        })
      } catch (err) {
        // User cancelled or share failed, just copy instead
        handleCopy()
      }
    } else {
      handleCopy()
    }
  }

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          <span className="ml-2 text-slate-400">Loading...</span>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Create Verification Link
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* File Inclusion Toggle */}
        <div className="flex items-center gap-3">
          <Checkbox
            id="include-files"
            checked={includeFiles}
            onCheckedChange={(checked) => setIncludeFiles(checked === true)}
          />
          <label
            htmlFor="include-files"
            className="text-sm font-medium text-slate-300 cursor-pointer"
          >
            Include relevant files in verification link
          </label>
        </div>

        {/* Category Selection */}
        {includeFiles && availableCategories.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-300">
              File Categories
            </label>
            <div className="grid grid-cols-2 gap-2">
              {availableCategories.map(cat => (
                <div key={cat} className="flex items-center gap-2">
                  <Checkbox
                    id={`category-${cat}`}
                    checked={selectedCategories.includes(cat)}
                    onCheckedChange={(checked) => {
                      if (checked === true) {
                        setSelectedCategories([...selectedCategories, cat])
                      } else {
                        setSelectedCategories(selectedCategories.filter(c => c !== cat))
                      }
                    }}
                  />
                  <label
                    htmlFor={`category-${cat}`}
                    className="text-sm text-slate-300 capitalize cursor-pointer"
                  >
                    {cat}
                  </label>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Document Selection */}
        {includeFiles && availableDocuments.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-300">
              Select Documents
            </label>
            <div className="max-h-48 overflow-y-auto space-y-1 bg-slate-900 rounded p-2">
              {availableDocuments.map(doc => (
                <div
                  key={doc.id}
                  className="flex items-center gap-2 p-2 hover:bg-slate-800 rounded cursor-pointer"
                  onClick={() => {
                    if (selectedDocuments.includes(doc.id)) {
                      setSelectedDocuments(selectedDocuments.filter(id => id !== doc.id))
                    } else {
                      setSelectedDocuments([...selectedDocuments, doc.id])
                    }
                  }}
                >
                  <Checkbox
                    checked={selectedDocuments.includes(doc.id)}
                    onCheckedChange={(checked) => {
                      if (checked === true) {
                        setSelectedDocuments([...selectedDocuments, doc.id])
                      } else {
                        setSelectedDocuments(selectedDocuments.filter(id => id !== doc.id))
                      }
                    }}
                  />
                  <FileText className="h-4 w-4 text-slate-400" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200 truncate">{doc.title || doc.filename}</p>
                    <p className="text-xs text-slate-500">
                      {doc.category} • {(doc.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-red-900/50 border border-red-700 rounded-lg">
            <p className="text-sm text-red-200">{error}</p>
          </div>
        )}

        {/* Generate Button */}
        <Button
          onClick={handleGenerateLink}
          disabled={generating}
          className="w-full"
        >
          {generating ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Share2 className="h-4 w-4 mr-2" />
              Generate Verification Link
            </>
          )}
        </Button>

        {/* Generated Link */}
        {generatedLink && (
          <div className="space-y-2 p-4 bg-slate-900 rounded-lg border border-slate-700">
            <label className="text-sm font-semibold text-slate-300">
              Verification Link
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={generatedLink}
                readOnly
                className="flex-1 p-2 bg-slate-800 border border-slate-600 rounded text-sm text-slate-200"
              />
              <Button onClick={handleCopy} size="sm" variant="outline">
                {copied ? (
                  <Check className="h-4 w-4 text-green-400" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
              {navigator.share && (
                <Button onClick={handleShare} size="sm" variant="outline">
                  <Share2 className="h-4 w-4" />
                </Button>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Share this link via email, Slack, Teams, or any other channel.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
