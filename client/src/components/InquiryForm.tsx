import { useState } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  Mail, 
  Send, 
  Loader2, 
  AlertCircle,
  CheckCircle,
  FileText,
  X,
  Upload
} from 'lucide-react';

interface InquiryFormProps {
  applicationId?: number;
  onSuccess?: () => void;
  onCancel?: () => void;
  className?: string;
}

export function InquiryForm({ applicationId, onSuccess, onCancel, className = '' }: InquiryFormProps) {
  // const { user } = useAuth(); // user unused
  const [formData, setFormData] = useState({
    inquiry_type: 'general',
    subject: '',
    message: '',
    priority: 'normal',
  });
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const response = await fetchWithAuth('/api/inquiries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          inquiry_type: formData.inquiry_type,
          subject: formData.subject,
          message: formData.message,
          priority: formData.priority,
          application_id: applicationId || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create inquiry');
      }

      await response.json(); // _data removed - unused
      setSuccess(true);
      
      // Reset form
      setFormData({
        inquiry_type: 'general',
        subject: '',
        message: '',
        priority: 'normal',
      });
      setFiles([]);

      // Call success callback after short delay
      setTimeout(() => {
        if (onSuccess) {
          onSuccess();
        }
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit inquiry');
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  if (success) {
    return (
      <Card className={`bg-slate-800 border-slate-700 ${className}`}>
        <CardContent className="p-8 text-center">
          <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="h-8 w-8 text-emerald-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">Inquiry Submitted!</h3>
          <p className="text-slate-400">We'll get back to you soon.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`bg-slate-800 border-slate-700 ${className}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-5 w-5" />
          Create Inquiry
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Inquiry Type */}
          <div>
            <label className="text-sm text-slate-400 mb-2 block">Inquiry Type</label>
            <select
              value={formData.inquiry_type}
              onChange={(e) => setFormData(prev => ({ ...prev, inquiry_type: e.target.value }))}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100"
              required
            >
              <option value="general">General Inquiry</option>
              <option value="application_status">Application Status</option>
              <option value="technical_support">Technical Support</option>
              <option value="sales">Sales</option>
            </select>
          </div>

          {/* Subject */}
          <div>
            <label className="text-sm text-slate-400 mb-2 block">Subject</label>
            <Input
              type="text"
              value={formData.subject}
              onChange={(e) => setFormData(prev => ({ ...prev, subject: e.target.value }))}
              placeholder="Enter inquiry subject"
              className="bg-slate-900 border-slate-700 text-slate-100"
              required
            />
          </div>

          {/* Priority */}
          <div>
            <label className="text-sm text-slate-400 mb-2 block">Priority</label>
            <select
              value={formData.priority}
              onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value }))}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-100"
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>

          {/* Message */}
          <div>
            <label className="text-sm text-slate-400 mb-2 block">Message</label>
            <Textarea
              value={formData.message}
              onChange={(e) => setFormData(prev => ({ ...prev, message: e.target.value }))}
              placeholder="Enter your message..."
              className="bg-slate-900 border-slate-700 text-slate-100 min-h-[150px]"
              required
            />
          </div>

          {/* File Attachments */}
          <div>
            <label className="text-sm text-slate-400 mb-2 block">Attachments (Optional)</label>
            <div className="space-y-2">
              <label className="flex items-center justify-center w-full px-4 py-2 border border-slate-700 rounded cursor-pointer hover:bg-slate-900 transition-colors">
                <Upload className="h-4 w-4 mr-2" />
                <span className="text-sm">Choose Files</span>
                <input
                  type="file"
                  multiple
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
              {files.length > 0 && (
                <div className="space-y-1">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-slate-900 rounded">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-slate-400" />
                        <span className="text-sm text-slate-300">{file.name}</span>
                        <span className="text-xs text-slate-500">
                          ({(file.size / 1024).toFixed(1)} KB)
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="text-slate-400 hover:text-red-400 transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Note: File upload functionality will be implemented in a future update
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg">
              <div className="flex items-center gap-2 text-red-400">
                <AlertCircle className="h-5 w-5" />
                <p className="text-sm">{error}</p>
              </div>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                className="border-slate-600 text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              disabled={submitting}
              className="bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Submit Inquiry
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
