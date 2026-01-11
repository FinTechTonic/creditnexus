/**
 * Policy Version History - Version timeline and diff viewer component.
 * 
 * Features:
 * - Version timeline view
 * - Diff viewer between versions
 * - Rollback functionality
 * - Version comparison
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchWithAuth } from '../../context/AuthContext';
import { 
  History, 
  GitCompare, 
  RotateCcw, 
  ChevronRight, 
  Loader2, 
  AlertCircle,
  CheckCircle2,
  Clock,
  User
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';

// Types
interface PolicyVersion {
  id: number;
  policy_id: number;
  version: number;
  rules_yaml: string;
  changes_summary?: string;
  created_by: number;
  created_at: string;
}

interface Policy {
  id: number;
  name: string;
  version: number;
  status: string;
}

interface PolicyVersionHistoryProps {
  policyId?: number;
  onVersionSelect?: (version: PolicyVersion) => void;
  onRollback?: (version: number) => void;
  className?: string;
}

export function PolicyVersionHistory({ 
  policyId: propPolicyId,
  onVersionSelect,
  onRollback,
  className = '' 
}: PolicyVersionHistoryProps) {
  const { policyId: urlPolicyId } = useParams<{ policyId?: string }>();
  const policyId = propPolicyId || (urlPolicyId ? parseInt(urlPolicyId) : null);
  
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<PolicyVersion | null>(null);
  const [compareVersion, setCompareVersion] = useState<PolicyVersion | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [showRollbackConfirm, setShowRollbackConfirm] = useState(false);
  const [rollbackVersion, setRollbackVersion] = useState<number | null>(null);
  const [rollingBack, setRollingBack] = useState(false);
  
  useEffect(() => {
    if (policyId) {
      loadPolicy();
      loadVersions();
    }
  }, [policyId]);
  
  const loadPolicy = async () => {
    if (!policyId) return;
    
    try {
      const response = await fetchWithAuth(`/api/policies/${policyId}`);
      if (!response.ok) {
        throw new Error('Failed to load policy');
      }
      
      const data = await response.json();
      setPolicy(data.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load policy');
    }
  };
  
  const loadVersions = async () => {
    if (!policyId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetchWithAuth(`/api/policies/${policyId}/versions`);
      if (!response.ok) {
        throw new Error('Failed to load versions');
      }
      
      const data = await response.json();
      setVersions(data.versions || []);
      
      // Select current version by default
      if (data.current_version && data.versions) {
        const current = data.versions.find((v: PolicyVersion) => v.version === data.current_version);
        if (current) {
          setSelectedVersion(current);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load versions');
    } finally {
      setLoading(false);
    }
  };
  
  const handleVersionSelect = (version: PolicyVersion) => {
    setSelectedVersion(version);
    if (onVersionSelect) {
      onVersionSelect(version);
    }
  };
  
  const handleCompare = (version: PolicyVersion) => {
    setCompareVersion(version);
    setShowDiff(true);
  };
  
  const handleRollback = (version: number) => {
    setRollbackVersion(version);
    setShowRollbackConfirm(true);
  };
  
  const confirmRollback = async () => {
    if (!policyId || !rollbackVersion) return;
    
    try {
      setRollingBack(true);
      setError(null);
      
      // Activate the selected version
      const response = await fetchWithAuth(`/api/policies/${policyId}/activate?version=${rollbackVersion}`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to rollback policy');
      }
      
      // Reload policy and versions
      await loadPolicy();
      await loadVersions();
      
      if (onRollback) {
        onRollback(rollbackVersion);
      }
      
      setShowRollbackConfirm(false);
      setRollbackVersion(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback policy');
    } finally {
      setRollingBack(false);
    }
  };
  
  const computeDiff = (oldYaml: string, newYaml: string): string => {
    // Simple line-by-line diff (in production, use a proper diff library like diff-match-patch)
    const oldLines = oldYaml.split('\n');
    const newLines = newYaml.split('\n');
    const maxLines = Math.max(oldLines.length, newLines.length);
    const diff: string[] = [];
    
    for (let i = 0; i < maxLines; i++) {
      const oldLine = oldLines[i] || '';
      const newLine = newLines[i] || '';
      
      if (oldLine === newLine) {
        diff.push(`  ${oldLine}`);
      } else {
        if (oldLine) {
          diff.push(`- ${oldLine}`);
        }
        if (newLine) {
          diff.push(`+ ${newLine}`);
        }
      }
    }
    
    return diff.join('\n');
  };
  
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  if (loading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }
  
  if (!policyId) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>No policy ID provided</AlertDescription>
      </Alert>
    );
  }
  
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <History className="h-6 w-6" />
            Version History
          </h2>
          {policy && (
            <p className="text-muted-foreground">
              {policy.name} - Current Version: {policy.version}
            </p>
          )}
        </div>
      </div>
      
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      {/* Version Timeline */}
      <div className="space-y-2">
        {versions.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              <p>No version history available</p>
            </CardContent>
          </Card>
        ) : (
          versions.map((version, index) => {
            const isCurrent = policy && version.version === policy.version;
            const isSelected = selectedVersion?.version === version.version;
            
            return (
              <Card 
                key={version.id} 
                className={`cursor-pointer transition-all ${
                  isSelected ? 'border-2 border-primary' : ''
                } ${isCurrent ? 'bg-primary/5' : ''}`}
                onClick={() => handleVersionSelect(version)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant={isCurrent ? 'default' : 'outline'}>
                          v{version.version}
                          {isCurrent && ' (Current)'}
                        </Badge>
                        <span className="text-sm text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(version.created_at)}
                        </span>
                      </div>
                      
                      {version.changes_summary && (
                        <p className="text-sm text-muted-foreground mb-2">
                          {version.changes_summary}
                        </p>
                      )}
                      
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <User className="h-3 w-3" />
                        Created by user {version.created_by}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {!isCurrent && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCompare(version);
                            }}
                          >
                            <GitCompare className="h-4 w-4 mr-2" />
                            Compare
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRollback(version.version);
                            }}
                          >
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Rollback
                          </Button>
                        </>
                      )}
                      {isSelected && (
                        <ChevronRight className="h-4 w-4 text-primary" />
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
      
      {/* Selected Version Details */}
      {selectedVersion && (
        <Card>
          <CardHeader>
            <CardTitle>Version {selectedVersion.version} Details</CardTitle>
            <CardDescription>
              Created {formatDate(selectedVersion.created_at)}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="yaml">
              <TabsList>
                <TabsTrigger value="yaml">YAML</TabsTrigger>
                {selectedVersion.changes_summary && (
                  <TabsTrigger value="changes">Changes</TabsTrigger>
                )}
              </TabsList>
              <TabsContent value="yaml" className="mt-4">
                <pre className="p-4 bg-muted rounded-lg overflow-x-auto text-sm">
                  {selectedVersion.rules_yaml}
                </pre>
              </TabsContent>
              {selectedVersion.changes_summary && (
                <TabsContent value="changes" className="mt-4">
                  <p className="text-sm">{selectedVersion.changes_summary}</p>
                </TabsContent>
              )}
            </Tabs>
          </CardContent>
        </Card>
      )}
      
      {/* Diff Dialog */}
      <Dialog open={showDiff} onOpenChange={setShowDiff}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Compare Versions</DialogTitle>
            <DialogDescription>
              Comparing version {selectedVersion?.version} with version {compareVersion?.version}
            </DialogDescription>
          </DialogHeader>
          
          {selectedVersion && compareVersion && (
            <div className="space-y-4">
              <Tabs defaultValue="diff">
                <TabsList>
                  <TabsTrigger value="diff">Diff</TabsTrigger>
                  <TabsTrigger value="old">Version {selectedVersion.version}</TabsTrigger>
                  <TabsTrigger value="new">Version {compareVersion.version}</TabsTrigger>
                </TabsList>
                <TabsContent value="diff" className="mt-4">
                  <pre className="p-4 bg-muted rounded-lg overflow-x-auto text-sm font-mono">
                    {computeDiff(selectedVersion.rules_yaml, compareVersion.rules_yaml)}
                  </pre>
                </TabsContent>
                <TabsContent value="old" className="mt-4">
                  <pre className="p-4 bg-muted rounded-lg overflow-x-auto text-sm">
                    {selectedVersion.rules_yaml}
                  </pre>
                </TabsContent>
                <TabsContent value="new" className="mt-4">
                  <pre className="p-4 bg-muted rounded-lg overflow-x-auto text-sm">
                    {compareVersion.rules_yaml}
                  </pre>
                </TabsContent>
              </Tabs>
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Rollback Confirmation Dialog */}
      <Dialog open={showRollbackConfirm} onOpenChange={setShowRollbackConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Rollback</DialogTitle>
            <DialogDescription>
              Are you sure you want to rollback to version {rollbackVersion}? This will activate that version as the current policy.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setShowRollbackConfirm(false);
                setRollbackVersion(null);
              }}
              disabled={rollingBack}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmRollback}
              disabled={rollingBack}
            >
              {rollingBack ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Rolling back...
                </>
              ) : (
                <>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Confirm Rollback
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
