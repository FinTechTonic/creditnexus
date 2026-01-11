/**
 * Template Preview - Preview policy template structure and rules.
 * 
 * Features:
 * - Display template metadata
 * - Show YAML rules preview
 * - Display use case and category
 * - Show template description
 */

import { useState } from 'react';
import { 
  FileText, 
  X,
  Code,
  Tag,
  Building2,
  Calendar,
  User,
  Copy,
  CheckCircle2
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Badge } from '../../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';

// Types
interface PolicyTemplate {
  id: number;
  name: string;
  category: string;
  description?: string;
  rules_yaml: string;
  use_case?: string;
  metadata?: Record<string, any>;
  is_system_template: boolean;
  created_by?: number;
  created_at: string;
}

interface TemplatePreviewProps {
  isOpen: boolean;
  onClose: () => void;
  template: PolicyTemplate | null;
  onClone?: (template: PolicyTemplate) => void;
}

export function TemplatePreview({
  isOpen,
  onClose,
  template,
  onClone
}: TemplatePreviewProps) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'yaml'>('overview');
  
  const handleCopyYaml = () => {
    if (template) {
      navigator.clipboard.writeText(template.rules_yaml);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };
  
  const handleClone = () => {
    if (template && onClone) {
      onClone(template);
      onClose();
    }
  };
  
  if (!template) {
    return null;
  }
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {template.name}
          </DialogTitle>
          <DialogDescription>
            Preview policy template structure and rules
          </DialogDescription>
        </DialogHeader>
        
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="yaml">YAML Rules</TabsTrigger>
          </TabsList>
          
          <TabsContent value="overview" className="space-y-4">
            {/* Metadata */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Template Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className="text-sm text-muted-foreground">Category</label>
                  <div className="mt-1">
                    <Badge variant="outline">{template.category}</Badge>
                  </div>
                </div>
                
                {template.use_case && (
                  <div>
                    <label className="text-sm text-muted-foreground">Use Case</label>
                    <div className="mt-1">
                      <Badge variant="secondary">
                        <Tag className="h-3 w-3 mr-1" />
                        {template.use_case}
                      </Badge>
                    </div>
                  </div>
                )}
                
                {template.description && (
                  <div>
                    <label className="text-sm text-muted-foreground">Description</label>
                    <p className="mt-1 text-sm">{template.description}</p>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      Created
                    </label>
                    <p className="mt-1 text-sm">
                      {new Date(template.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  {template.is_system_template && (
                    <div>
                      <label className="text-sm text-muted-foreground">Type</label>
                      <div className="mt-1">
                        <Badge variant="default">System Template</Badge>
                      </div>
                    </div>
                  )}
                </div>
                
                {template.metadata && Object.keys(template.metadata).length > 0 && (
                  <div>
                    <label className="text-sm text-muted-foreground">Metadata</label>
                    <pre className="mt-1 p-2 bg-muted rounded text-xs overflow-x-auto">
                      {JSON.stringify(template.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>
            
            {/* Actions */}
            <div className="flex items-center gap-2">
              <Button
                onClick={handleClone}
                className="flex-1"
              >
                <Copy className="h-4 w-4 mr-2" />
                Clone Template
              </Button>
            </div>
          </TabsContent>
          
          <TabsContent value="yaml" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Code className="h-5 w-5" />
                    YAML Rules
                  </CardTitle>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCopyYaml}
                  >
                    {copied ? (
                      <>
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4 mr-2" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <pre className="bg-muted p-4 rounded text-xs overflow-x-auto max-h-96 overflow-y-auto">
                  {template.rules_yaml}
                </pre>
              </CardContent>
            </Card>
            
            {/* Actions */}
            <div className="flex items-center gap-2">
              <Button
                onClick={handleClone}
                className="flex-1"
              >
                <Copy className="h-4 w-4 mr-2" />
                Clone Template
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
