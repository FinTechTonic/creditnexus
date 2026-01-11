/**
 * Policy Validator - Real-time YAML validation component.
 * 
 * Features:
 * - Real-time YAML validation
 * - Syntax error highlighting
 * - Structure validation feedback
 * - Field reference validation
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '../../context/AuthContext';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Loader2,
  Code,
  FileText,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';

// Types
interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  metadata?: {
    rules_count?: number;
    rule_names?: string[];
    [key: string]: any;
  };
}

interface PolicyValidatorProps {
  yaml: string;
  policyId?: number;
  onValidationChange?: (result: ValidationResult | null) => void;
  className?: string;
}

interface ErrorLocation {
  line?: number;
  column?: number;
  message: string;
  type: 'syntax' | 'structure' | 'field_reference' | 'other';
}

export function PolicyValidator({ 
  yaml, 
  policyId,
  onValidationChange,
  className = '' 
}: PolicyValidatorProps) {
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [validating, setValidating] = useState(false);
  const [errorLocations, setErrorLocations] = useState<ErrorLocation[]>([]);
  
  // Debounce validation
  useEffect(() => {
    const timer = setTimeout(() => {
      if (yaml.trim()) {
        validateYaml(yaml);
      } else {
        setValidationResult(null);
        setErrorLocations([]);
        if (onValidationChange) {
          onValidationChange(null);
        }
      }
    }, 500); // 500ms debounce
    
    return () => clearTimeout(timer);
  }, [yaml, policyId]);
  
  const validateYaml = async (yamlToValidate: string) => {
    try {
      setValidating(true);
      
      const endpoint = policyId 
        ? `/api/policies/${policyId}/validate`
        : '/api/policies/0/validate';
      
      const response = await fetchWithAuth(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules_yaml: yamlToValidate })
      });
      
      if (!response.ok) {
        throw new Error('Validation request failed');
      }
      
      const data = await response.json();
      const result: ValidationResult = {
        valid: data.valid,
        errors: data.errors || [],
        warnings: data.warnings || [],
        metadata: data.metadata
      };
      
      setValidationResult(result);
      
      // Parse error locations from error messages
      const locations = parseErrorLocations(result.errors, result.warnings);
      setErrorLocations(locations);
      
      if (onValidationChange) {
        onValidationChange(result);
      }
    } catch (err) {
      console.error('Validation error:', err);
      setValidationResult({
        valid: false,
        errors: ['Failed to validate YAML'],
        warnings: []
      });
    } finally {
      setValidating(false);
    }
  };
  
  const parseErrorLocations = (errors: string[], warnings: string[]): ErrorLocation[] => {
    const locations: ErrorLocation[] = [];
    
    // Parse errors
    errors.forEach(error => {
      // Try to extract line number from error message
      const lineMatch = error.match(/Rule (\d+)/i) || error.match(/line (\d+)/i);
      const line = lineMatch ? parseInt(lineMatch[1]) : undefined;
      
      let type: ErrorLocation['type'] = 'other';
      if (error.toLowerCase().includes('yaml') || error.toLowerCase().includes('syntax')) {
        type = 'syntax';
      } else if (error.toLowerCase().includes('field')) {
        type = 'field_reference';
      } else if (error.toLowerCase().includes('structure') || error.toLowerCase().includes('required')) {
        type = 'structure';
      }
      
      locations.push({
        line,
        message: error,
        type
      });
    });
    
    // Parse warnings
    warnings.forEach(warning => {
      locations.push({
        message: warning,
        type: 'other'
      });
    });
    
    return locations;
  };
  
  const getErrorIcon = (type: ErrorLocation['type']) => {
    switch (type) {
      case 'syntax':
        return <Code className="h-4 w-4" />;
      case 'structure':
        return <FileText className="h-4 w-4" />;
      case 'field_reference':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <AlertTriangle className="h-4 w-4" />;
    }
  };
  
  const getErrorBadgeColor = (type: ErrorLocation['type']) => {
    switch (type) {
      case 'syntax':
        return 'bg-red-500';
      case 'structure':
        return 'bg-orange-500';
      case 'field_reference':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };
  
  if (!yaml.trim()) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Validation
          </CardTitle>
          <CardDescription>YAML validation results will appear here</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>Enter YAML to validate</p>
          </div>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Validation
            </CardTitle>
            <CardDescription>
              {validating ? 'Validating...' : 'Real-time YAML validation'}
            </CardDescription>
          </div>
          {validationResult && (
            <Badge variant={validationResult.valid ? "default" : "destructive"}>
              {validating ? (
                <>
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  Validating
                </>
              ) : validationResult.valid ? (
                <>
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Valid
                </>
              ) : (
                <>
                  <XCircle className="h-3 w-3 mr-1" />
                  {validationResult.errors.length} error(s)
                </>
              )}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {validating ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : validationResult ? (
          <div className="space-y-4">
            {/* Validation Status */}
            {validationResult.valid ? (
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertDescription>
                  YAML is valid. {validationResult.metadata?.rules_count || 0} rule(s) found.
                </AlertDescription>
              </Alert>
            ) : (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  YAML validation failed. Please fix the errors below.
                </AlertDescription>
              </Alert>
            )}
            
            {/* Metadata */}
            {validationResult.metadata && (
              <div className="grid grid-cols-2 gap-4 text-sm">
                {validationResult.metadata.rules_count !== undefined && (
                  <div>
                    <span className="text-muted-foreground">Rules:</span>{' '}
                    <span className="font-semibold">{validationResult.metadata.rules_count}</span>
                  </div>
                )}
                {validationResult.metadata.rule_names && validationResult.metadata.rule_names.length > 0 && (
                  <div>
                    <span className="text-muted-foreground">Rule Names:</span>{' '}
                    <span className="font-semibold">{validationResult.metadata.rule_names.length}</span>
                  </div>
                )}
              </div>
            )}
            
            {/* Errors */}
            {validationResult.errors.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-destructive" />
                  Errors ({validationResult.errors.length})
                </h4>
                <div className="space-y-2">
                  {errorLocations
                    .filter(loc => validationResult.errors.includes(loc.message))
                    .map((location, index) => (
                      <Alert key={index} variant="destructive">
                        <div className="flex items-start gap-2">
                          {getErrorIcon(location.type)}
                          <div className="flex-1">
                            {location.line && (
                              <Badge variant="outline" className="mb-1 mr-2">
                                Line {location.line}
                              </Badge>
                            )}
                            <Badge variant="outline" className={`mb-1 ${getErrorBadgeColor(location.type)} text-white`}>
                              {location.type.replace('_', ' ')}
                            </Badge>
                            <AlertDescription className="mt-1">
                              {location.message}
                            </AlertDescription>
                          </div>
                        </div>
                      </Alert>
                    ))}
                </div>
              </div>
            )}
            
            {/* Warnings */}
            {validationResult.warnings.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-500" />
                  Warnings ({validationResult.warnings.length})
                </h4>
                <div className="space-y-2">
                  {validationResult.warnings.map((warning, index) => (
                    <Alert key={index}>
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>{warning}</AlertDescription>
                    </Alert>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <p>Validation results will appear here</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
