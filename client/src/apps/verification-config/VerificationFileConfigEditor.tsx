/**
 * YAML configuration editor component for verification file whitelist.
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Save, RefreshCw, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'

const DEFAULT_YAML = `# Verification File Whitelist Configuration
# Controls which files and categories are included in verification links

enabled_categories:
  - legal
  - financial
  - compliance

file_types:
  allowed_extensions:
    - .pdf
    - .doc
    - .docx
    - .txt
    - .json
    - .xlsx
    - .csv
  max_file_size_mb: 50

categories:
  legal:
    enabled: true
    required: true
    file_types:
      - .pdf
      - .doc
      - .docx
    description: "Legal documents (agreements, contracts)"
  
  financial:
    enabled: true
    required: false
    file_types:
      - .pdf
      - .xlsx
      - .csv
    description: "Financial statements and reports"
  
  compliance:
    enabled: true
    required: false
    file_types:
      - .pdf
      - .doc
    description: "Compliance and regulatory documents"

subdirectories:
  documents:
    enabled: true
    priority: 1
    description: "Main deal documents"
  
  extractions:
    enabled: true
    priority: 2
    description: "Extracted data files"
  
  generated:
    enabled: false
    priority: 3
    description: "Generated documents"
  
  notes:
    enabled: false
    priority: 4
    description: "Deal notes and comments"
`

export function VerificationFileConfigEditor() {
  const [yamlContent, setYamlContent] = useState(DEFAULT_YAML)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [isDirty, setIsDirty] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/config/verification-file-whitelist')
      
      if (response.ok) {
        const data = await response.json()
        if (data.yaml) {
          setYamlContent(data.yaml)
        }
      } else {
        // Use default config if endpoint doesn't exist yet
        console.log('Config endpoint not available, using default')
      }
    } catch (err) {
      console.error('Failed to load configuration:', err)
      // Continue with default
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(false)

    try {
      const response = await fetch('/api/config/verification-file-whitelist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ yaml: yamlContent })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to save configuration')
      }

      setSuccess(true)
      setIsDirty(false)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setYamlContent(DEFAULT_YAML)
    setIsDirty(true)
    setError(null)
    setSuccess(false)
  }

  const handleChange = (value: string) => {
    setYamlContent(value)
    setIsDirty(true)
    setError(null)
    setSuccess(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        <span className="ml-2 text-slate-400">Loading configuration...</span>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle>Verification File Whitelist Configuration</CardTitle>
          <p className="text-sm text-slate-400">
            Configure which files and categories are included in verification links.
            Changes take effect immediately after saving.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* YAML Editor */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-300">
              YAML Configuration
            </label>
            <Textarea
              value={yamlContent}
              onChange={(e) => handleChange(e.target.value)}
              className="font-mono text-sm min-h-[500px] bg-slate-900 border-slate-600 text-slate-200"
              placeholder="Enter YAML configuration..."
              spellCheck={false}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              onClick={handleSave}
              disabled={saving || !isDirty}
              className="flex items-center gap-2"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save Configuration
                </>
              )}
            </Button>
            <Button
              onClick={handleReset}
              variant="outline"
              disabled={saving}
              className="flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Reset to Default
            </Button>
          </div>

          {/* Status Messages */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-900/50 border border-red-700 rounded-lg">
              <AlertCircle className="h-5 w-5 text-red-400" />
              <span className="text-sm text-red-200">{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 p-3 bg-green-900/50 border border-green-700 rounded-lg">
              <CheckCircle className="h-5 w-5 text-green-400" />
              <span className="text-sm text-green-200">
                Configuration saved successfully
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Configuration Guide */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-lg">Configuration Guide</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-400 space-y-4">
          <div>
            <h4 className="font-semibold text-slate-300 mb-2">Categories</h4>
            <p>
              Define file categories (legal, financial, compliance, etc.) that can be
              included in verification links. Required categories must be included.
            </p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-300 mb-2">File Types</h4>
            <p>
              Specify allowed file extensions and maximum file size. Only files with
              allowed extensions can be included in verification links.
            </p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-300 mb-2">Subdirectories</h4>
            <p>
              Control which deal subdirectories are scanned for files. Enable only
              the directories that contain relevant documents.
            </p>
          </div>
          <div>
            <h4 className="font-semibold text-slate-300 mb-2">Security Note</h4>
            <p className="text-amber-400">
              Only administrators can modify this configuration. Changes affect all
              verification links generated after the save.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
