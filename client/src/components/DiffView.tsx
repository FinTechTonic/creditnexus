import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { GitCompare, Plus, Minus, Edit } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface DiffViewProps {
  documentId: number;
  versionId1?: number;
  versionId2?: number;
}

interface DiffChange {
  path: string;
  old_value?: any;
  new_value?: any;
}

interface DiffData {
  version_1: any;
  version_2: any;
  diff: {
    added: Array<{ path: string; value: any }>;
    removed: Array<{ path: string; value: any }>;
    changed: DiffChange[];
  };
  formatted_diff: {
    added: Array<{ path: string; value: string; display: string }>;
    removed: Array<{ path: string; value: string; display: string }>;
    changed: Array<{ path: string; old_value: string; new_value: string; display: string }>;
    summary: {
      total_changes: number;
      added_count: number;
      removed_count: number;
      changed_count: number;
    };
  };
}

export function DiffView({ documentId, versionId1, versionId2 }: DiffViewProps) {
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVersion1, setSelectedVersion1] = useState<number | undefined>(versionId1);
  const [selectedVersion2, setSelectedVersion2] = useState<number | undefined>(versionId2);
  const [diffData, setDiffData] = useState<DiffData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadVersions();
  }, [documentId]);

  useEffect(() => {
    if (selectedVersion1 && selectedVersion2 && selectedVersion1 !== selectedVersion2) {
      loadDiff();
    } else {
      setDiffData(null);
    }
  }, [documentId, selectedVersion1, selectedVersion2]);

  const loadVersions = async () => {
    try {
      const response = await fetchWithAuth(`/api/reviews/documents/${documentId}/versions`);
      if (response.ok) {
        const data = await response.json();
        setVersions(data.versions || []);
        if (data.versions && data.versions.length > 0) {
          if (!selectedVersion1) setSelectedVersion1(data.versions[0].id);
          if (!selectedVersion2 && data.versions.length > 1) {
            setSelectedVersion2(data.versions[0].id);
          }
        }
      }
    } catch (error) {
      console.error('Error loading versions:', error);
    }
  };

  const loadDiff = async () => {
    if (!selectedVersion1 || !selectedVersion2) return;

    try {
      setLoading(true);
      const response = await fetchWithAuth(
        `/api/reviews/documents/${documentId}/versions/${selectedVersion1}/diff/${selectedVersion2}`
      );
      if (response.ok) {
        const data = await response.json();
        setDiffData(data);
      }
    } catch (error) {
      console.error('Error loading diff:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GitCompare className="h-5 w-5" />
          Version Comparison
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Version Selectors */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Version 1 (Old)</label>
            <Select
              value={selectedVersion1?.toString()}
              onValueChange={(value) => setSelectedVersion1(parseInt(value))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select version" />
              </SelectTrigger>
              <SelectContent>
                {versions.map((v) => (
                  <SelectItem key={v.id} value={v.id.toString()}>
                    Version {v.version_number} ({new Date(v.created_at).toLocaleDateString()})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Version 2 (New)</label>
            <Select
              value={selectedVersion2?.toString()}
              onValueChange={(value) => setSelectedVersion2(parseInt(value))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select version" />
              </SelectTrigger>
              <SelectContent>
                {versions.map((v) => (
                  <SelectItem key={v.id} value={v.id.toString()}>
                    Version {v.version_number} ({new Date(v.created_at).toLocaleDateString()})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Diff Summary */}
        {diffData && (
          <div className="flex items-center gap-4 p-4 bg-muted rounded-lg">
            <Badge variant="outline">
              Total Changes: {diffData.formatted_diff.summary.total_changes}
            </Badge>
            <Badge variant="default" className="bg-green-600">
              <Plus className="h-3 w-3 mr-1" />
              Added: {diffData.formatted_diff.summary.added_count}
            </Badge>
            <Badge variant="default" className="bg-red-600">
              <Minus className="h-3 w-3 mr-1" />
              Removed: {diffData.formatted_diff.summary.removed_count}
            </Badge>
            <Badge variant="default" className="bg-blue-600">
              <Edit className="h-3 w-3 mr-1" />
              Changed: {diffData.formatted_diff.summary.changed_count}
            </Badge>
          </div>
        )}

        {/* Diff Content */}
        {loading ? (
          <div className="text-center text-muted-foreground py-8">Loading diff...</div>
        ) : diffData ? (
          <div className="space-y-4">
            {/* Added Items */}
            {diffData.formatted_diff.added.length > 0 && (
              <div>
                <h3 className="font-semibold mb-2 text-green-600 flex items-center gap-2">
                  <Plus className="h-4 w-4" />
                  Added ({diffData.formatted_diff.added.length})
                </h3>
                <div className="space-y-2">
                  {diffData.formatted_diff.added.map((item, idx) => (
                    <div key={idx} className="p-3 bg-green-50 dark:bg-green-950 rounded border border-green-200 dark:border-green-800">
                      <div className="font-mono text-sm font-semibold mb-1">{item.path}</div>
                      <pre className="text-xs text-green-800 dark:text-green-200 overflow-x-auto">
                        {formatValue(item.value)}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Removed Items */}
            {diffData.formatted_diff.removed.length > 0 && (
              <div>
                <h3 className="font-semibold mb-2 text-red-600 flex items-center gap-2">
                  <Minus className="h-4 w-4" />
                  Removed ({diffData.formatted_diff.removed.length})
                </h3>
                <div className="space-y-2">
                  {diffData.formatted_diff.removed.map((item, idx) => (
                    <div key={idx} className="p-3 bg-red-50 dark:bg-red-950 rounded border border-red-200 dark:border-red-800">
                      <div className="font-mono text-sm font-semibold mb-1">{item.path}</div>
                      <pre className="text-xs text-red-800 dark:text-red-200 overflow-x-auto">
                        {formatValue(item.value)}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Changed Items */}
            {diffData.formatted_diff.changed.length > 0 && (
              <div>
                <h3 className="font-semibold mb-2 text-blue-600 flex items-center gap-2">
                  <Edit className="h-4 w-4" />
                  Changed ({diffData.formatted_diff.changed.length})
                </h3>
                <div className="space-y-2">
                  {diffData.formatted_diff.changed.map((item, idx) => (
                    <div key={idx} className="border rounded-lg overflow-hidden">
                      <div className="p-2 bg-blue-50 dark:bg-blue-950 border-b font-mono text-sm font-semibold">
                        {item.path}
                      </div>
                      <div className="grid grid-cols-2">
                        <div className="p-3 bg-red-50 dark:bg-red-950 border-r">
                          <div className="text-xs font-semibold text-red-600 mb-1">Old Value</div>
                          <pre className="text-xs text-red-800 dark:text-red-200 overflow-x-auto">
                            {formatValue(item.old_value)}
                          </pre>
                        </div>
                        <div className="p-3 bg-green-50 dark:bg-green-950">
                          <div className="text-xs font-semibold text-green-600 mb-1">New Value</div>
                          <pre className="text-xs text-green-800 dark:text-green-200 overflow-x-auto">
                            {formatValue(item.new_value)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {diffData.formatted_diff.summary.total_changes === 0 && (
              <div className="text-center text-muted-foreground py-8">
                No changes between these versions.
              </div>
            )}
          </div>
        ) : selectedVersion1 && selectedVersion2 ? (
          <div className="text-center text-muted-foreground py-8">
            Select two different versions to compare.
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-8">
            Select versions to compare.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
