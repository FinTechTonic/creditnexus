/**
 * YAML configuration editor component for verification file whitelist.
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Save, RefreshCw, AlertCircle, CheckCircle, Loader2, Eye, FileCheck, X } from 'lucide-react'
import { PermissionGate } from '@/components/PermissionGate'
import { PERMISSION_USER_VIEW } from '@/utils/permissions'
import { useAuth, fetchWithAuth } from '@/context/AuthContext'

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

interface ConfigPreview {
  enabled_categories?: string[]
  file_types?: {
    allowed_extensions?: string[]
    max_file_size_mb?: number
  }
  categories?: Record<string, {
    enabled?: boolean
    required?: boolean
    file_types?: string[]
    description?: string
  }>
  subdirectories?: Record<string, {
    enabled?: boolean
    priority?: number
    description?: string
  }>
}

export function VerificationFileConfigEditor() {
  const { isAuthenticated } = useAuth()
  const [yamlContent, setYamlContent] = useState(DEFAULT_YAML)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const [previewConfig, setPreviewConfig] = useState<ConfigPreview | null>(null)
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [showPreview, setShowPreview] = useState(false)
  
  useEffect(() => {
    if (isAuthenticated) {
      loadConfig()
    } else {
      setLoading(false)
      setError('Authentication required. Please log in.')
    }
  }, [isAuthenticated])

  const loadConfig = async () => {
    setLoading(true)
    setError(null)
    setValidationErrors([])

    try {
      const response = await fetchWithAuth('/api/config/verification-file-whitelist', {
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (response.status === 403) {
        setError('Admin permissions required to view configuration')
        return
      }
      
      if (response.ok) {
        const data = await response.json()
        if (data.yaml) {
          setYamlContent(data.yaml)
          validateYAML(data.yaml)
        }
      } else if (response.status !== 404) {
        const errorData = await response.json().catch(() => ({}))
        setError(errorData.detail || `Failed to load: ${response.statusText}`)
      }
    } catch (err) {
      console.error('Failed to load configuration:', err)
      setError(err instanceof Error ? err.message : 'Failed to load configuration')
    } finally {
      setLoading(false)
    }
  }
  
  const validateYAML = (yamlText: string) => {
    const errors: string[] = []
    
    try {
      // Basic YAML structure validation - check for common patterns
      if (!yamlText.trim()) {
        errors.push('Configuration cannot be empty')
        setValidationErrors(errors)
        setPreviewConfig(null)
        return
      }
      
      // Try to parse as JSON-like structure (basic validation)
      // For full YAML parsing, we'd need js-yaml library
      // For now, we'll do basic structure checks
      
      // Check for required top-level keys
      const requiredKeys = ['enabled_categories', 'file_types', 'categories', 'subdirectories']
      const missingKeys = requiredKeys.filter(key => !yamlText.includes(`${key}:`))
      if (missingKeys.length > 0) {
        errors.push(`Missing required sections: ${missingKeys.join(', ')}`)
      }
      
      // Check for enabled_categories as array
      if (yamlText.includes('enabled_categories:')) {
        const categoriesMatch = yamlText.match(/enabled_categories:\s*\n\s*-\s*(\w+)/g)
        if (!categoriesMatch || categoriesMatch.length === 0) {
          errors.push('enabled_categories should be a list with at least one item')
        }
      }
      
      // Check for file_types.allowed_extensions
      if (yamlText.includes('file_types:') && !yamlText.includes('allowed_extensions:')) {
        errors.push('file_types section must include allowed_extensions')
      }
      
      // Check for max_file_size_mb
      if (yamlText.includes('file_types:') && !yamlText.includes('max_file_size_mb:')) {
        errors.push('file_types section must include max_file_size_mb')
      }
      
      // Try to extract basic structure for preview
      const preview: ConfigPreview = {}
      
      // Extract enabled_categories
      const categoriesMatch = yamlText.match(/enabled_categories:\s*\n((?:\s*-\s*\w+\n?)+)/)
      if (categoriesMatch) {
        preview.enabled_categories = categoriesMatch[1]
          .split('\n')
          .map(line => line.match(/-\s*(\w+)/)?.[1])
          .filter(Boolean) as string[]
      }
      
      // Extract file_types
      const fileTypesMatch = yamlText.match(/file_types:\s*\n((?:\s+\w+[^\n]*\n?)+)/)
      if (fileTypesMatch) {
        preview.file_types = {}
        const extensionsMatch = fileTypesMatch[1].match(/allowed_extensions:\s*\n((?:\s+-\s*\.[^\n]+\n?)+)/)
        if (extensionsMatch) {
          preview.file_types.allowed_extensions = extensionsMatch[1]
            .split('\n')
            .map(line => line.match(/-\s*(\.[^\s]+)/)?.[1])
            .filter(Boolean) as string[]
        }
        const maxSizeMatch = fileTypesMatch[1].match(/max_file_size_mb:\s*(\d+)/)
        if (maxSizeMatch) {
          preview.file_types.max_file_size_mb = parseInt(maxSizeMatch[1], 10)
        }
      }
      
      setPreviewConfig(preview)
    } catch (e) {
      errors.push(`Parse error: ${e instanceof Error ? e.message : 'Unknown error'}`)
    }
    
    setValidationErrors(errors)
  }

  const handleSave = async () => {
    // Validate before saving
    if (validationErrors.length > 0) {
      setError('Please fix validation errors before saving')
      return
    }
    
    setSaving(true)
    setError(null)
    setSuccess(false)

    try {
      if (!isAuthenticated) {
        setError('Authentication required. Please log in.')
        return
      }
      
      const response = await fetchWithAuth('/api/config/verification-file-whitelist', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ yaml: yamlContent })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        if (errorData.detail) {
          if (typeof errorData.detail === 'object' && errorData.detail.validation_errors) {
            setValidationErrors(errorData.detail.validation_errors)
            throw new Error('Configuration validation failed')
          }
          throw new Error(errorData.detail.message || errorData.detail || 'Failed to save configuration')
        }
        throw new Error(`Failed to save: ${response.statusText}`)
      }

      setSuccess(true)
      setIsDirty(false)
      setValidationErrors([])
      validateYAML(yamlContent) // Refresh preview
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
    validateYAML(value)
  }

  if (loading) {
    return (
      <PermissionGate permission={PERMISSION_USER_VIEW}>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
          <span className="ml-2 text-slate-400">Loading configuration...</span>
        </div>
      </PermissionGate>
    )
  }

  return (
    <PermissionGate 
      permission={PERMISSION_USER_VIEW}
      fallback={
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-200 mb-2">Access Denied</h3>
            <p className="text-slate-400">Admin permissions required to access this configuration.</p>
          </div>
        </div>
      }
    >
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
          <div className="flex gap-2 flex-wrap">
            <Button
              onClick={handleSave}
              disabled={saving || !isDirty || validationErrors.length > 0}
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
            <Button
              onClick={() => setShowPreview(!showPreview)}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Eye className="h-4 w-4" />
              {showPreview ? 'Hide' : 'Show'} Preview
            </Button>
          </div>
          
          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="p-3 bg-amber-900/50 border border-amber-700 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="h-4 w-4 text-amber-400" />
                <span className="text-sm font-semibold text-amber-300">Validation Warnings</span>
              </div>
              <ul className="list-disc list-inside text-sm text-amber-200 space-y-1">
                {validationErrors.map((err, idx) => (
                  <li key={idx}>{err}</li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Preview Panel */}
          {showPreview && previewConfig && (
            <div className="mt-4 p-4 bg-slate-900 rounded-lg border border-slate-600">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                  <FileCheck className="h-4 w-4" />
                  Configuration Preview
                </h4>
                <button
                  onClick={() => setShowPreview(false)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="space-y-3 text-sm">
                {previewConfig.enabled_categories && previewConfig.enabled_categories.length > 0 && (
                  <div>
                    <span className="text-slate-400 font-medium">Enabled Categories: </span>
                    <span className="text-slate-200">
                      {previewConfig.enabled_categories.join(', ')}
                    </span>
                  </div>
                )}
                {previewConfig.file_types && (
                  <>
                    {previewConfig.file_types.allowed_extensions && previewConfig.file_types.allowed_extensions.length > 0 && (
                      <div>
                        <span className="text-slate-400 font-medium">Allowed Extensions: </span>
                        <span className="text-slate-200">
                          {previewConfig.file_types.allowed_extensions.join(', ')}
                        </span>
                      </div>
                    )}
                    {previewConfig.file_types.max_file_size_mb && (
                      <div>
                        <span className="text-slate-400 font-medium">Max File Size: </span>
                        <span className="text-slate-200">
                          {previewConfig.file_types.max_file_size_mb} MB
                        </span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

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
    </PermissionGate>
  )
}
