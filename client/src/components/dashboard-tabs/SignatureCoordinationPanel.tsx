import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle, RefreshCw, ExternalLink, Mail } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface SignatureRequest {
  id: number;
  document_id: number;
  document_title?: string;
  signature_provider: string;
  signature_status: string;
  signers: Array<{ name: string; email: string; role: string; status?: string }>;
  requested_at: string;
  access_token?: string;
}

export function SignatureCoordinationPanel() {
  const [requests, setRequests] = useState<SignatureRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRequests();
  }, []);

  const loadRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWithAuth('/api/signatures/coordinated');
      if (!res.ok) {
        throw new Error('Failed to load signature requests');
      }
      const data = await res.json();
      setRequests(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load requests');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/50">Completed</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/50">Pending</Badge>;
      case 'declined':
        return <Badge className="bg-red-500/20 text-red-400 border-red-500/50">Declined</Badge>;
      case 'expired':
        return <Badge className="bg-slate-500/20 text-slate-400 border-slate-500/50">Expired</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center text-red-400">
        <AlertCircle className="h-12 w-12 mx-auto mb-4" />
        <p>{error}</p>
        <Button variant="outline" className="mt-4" onClick={loadRequests}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="p-6">
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Active Signature Requests</CardTitle>
            <p className="text-sm text-slate-400 mt-1">Track and manage all document signature workflows.</p>
          </div>
          <Button variant="outline" size="sm" onClick={loadRequests}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-slate-800 hover:bg-transparent">
                <TableHead className="text-slate-400">Document</TableHead>
                <TableHead className="text-slate-400">Provider</TableHead>
                <TableHead className="text-slate-400">Signers</TableHead>
                <TableHead className="text-slate-400">Requested</TableHead>
                <TableHead className="text-slate-400 text-right">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {requests.map((req) => (
                <TableRow key={req.id} className="border-slate-800 hover:bg-slate-800/50">
                  <TableCell className="font-medium">
                    <div className="flex flex-col">
                      <span>{req.document_title || `Doc #${req.document_id}`}</span>
                      <span className="text-[10px] text-slate-500 font-mono uppercase tracking-tighter">ID: {req.id}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px] uppercase font-bold border-slate-700 text-slate-400">
                      {req.signature_provider}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex -space-x-2">
                      {req.signers.map((s, idx) => (
                        <div 
                          key={idx} 
                          className="h-7 w-7 rounded-full bg-slate-700 border-2 border-slate-900 flex items-center justify-center"
                          title={`${s.name} (${s.email}) - ${s.status || 'pending'}`}
                        >
                          <span className="text-[10px] font-bold text-slate-300">
                            {(s?.name || s?.email || '?').substring(0, 1)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-slate-400">
                    {new Date(req.requested_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      {req.access_token && (
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-400/10"
                          title="Copy signing portal link"
                          onClick={() => {
                            navigator.clipboard.writeText(`${window.location.origin}/signers/${req.access_token}`);
                          }}
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      )}
                      {getStatusBadge(req.signature_status)}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {requests.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-12 text-slate-500">
                    No signature requests found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
