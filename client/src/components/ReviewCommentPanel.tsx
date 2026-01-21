import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
// ScrollArea component - using div with overflow instead
import { 
  MessageSquare, 
  CheckCircle2, 
  Trash2,
  Reply
} from 'lucide-react';
import { fetchWithAuth, useAuth } from '@/context/AuthContext';

interface ReviewComment {
  id: number;
  document_id: number;
  version_id?: number;
  user_id: number;
  comment_text: string;
  comment_type: 'general' | 'annotation' | 'change_request';
  target_field?: string;
  target_range?: { start: number; end: number };
  resolved: boolean;
  resolved_by?: number;
  resolved_at?: string;
  parent_comment_id?: number;
  created_at: string;
  updated_at: string;
}

interface ReviewCommentPanelProps {
  documentId: number;
  versionId?: number;
  onCommentAdded?: () => void;
}

export function ReviewCommentPanel({ 
  documentId, 
  versionId,
  onCommentAdded 
}: ReviewCommentPanelProps) {
  const { user } = useAuth();
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newComment, setNewComment] = useState('');
  const [commentType, setCommentType] = useState<'general' | 'annotation' | 'change_request'>('general');
  const [replyingTo, setReplyingTo] = useState<number | null>(null);
  const [replyText, setReplyText] = useState('');

  useEffect(() => {
    loadComments();
  }, [documentId, versionId]);

  const loadComments = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (versionId) params.append('version_id', versionId.toString());
      
      const response = await fetchWithAuth(
        `/api/reviews/documents/${documentId}/comments?${params.toString()}`
      );
      
      if (response.ok) {
        const data = await response.json();
        setComments(data.comments || []);
      }
    } catch (error) {
      console.error('Error loading comments:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;

    try {
      const response = await fetchWithAuth(
        `/api/reviews/documents/${documentId}/comments`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            comment_text: newComment,
            comment_type: commentType,
            version_id: versionId,
          }),
        }
      );

      if (response.ok) {
        setNewComment('');
        setCommentType('general');
        loadComments();
        onCommentAdded?.();
      }
    } catch (error) {
      console.error('Error adding comment:', error);
    }
  };

  const handleReply = async (parentId: number) => {
    if (!replyText.trim()) return;

    try {
      const response = await fetchWithAuth(
        `/api/reviews/documents/${documentId}/comments`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            comment_text: replyText,
            comment_type: 'general',
            version_id: versionId,
            parent_comment_id: parentId,
          }),
        }
      );

      if (response.ok) {
        setReplyText('');
        setReplyingTo(null);
        loadComments();
        onCommentAdded?.();
      }
    } catch (error) {
      console.error('Error replying to comment:', error);
    }
  };

  const handleResolve = async (commentId: number) => {
    try {
      const response = await fetchWithAuth(
        `/api/reviews/comments/${commentId}/resolve`,
        { method: 'PUT' }
      );

      if (response.ok) {
        loadComments();
      }
    } catch (error) {
      console.error('Error resolving comment:', error);
    }
  };

  const handleDelete = async (commentId: number) => {
    if (!confirm('Are you sure you want to delete this comment?')) return;

    try {
      const response = await fetchWithAuth(
        `/api/reviews/comments/${commentId}`,
        { method: 'DELETE' }
      );

      if (response.ok) {
        loadComments();
      }
    } catch (error) {
      console.error('Error deleting comment:', error);
    }
  };

  const getCommentTypeBadge = (type: string) => {
    const badges = {
      general: <Badge variant="secondary">General</Badge>,
      annotation: <Badge variant="outline">Annotation</Badge>,
      change_request: <Badge variant="destructive">Change Request</Badge>,
    };
    return badges[type as keyof typeof badges] || badges.general;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const renderComment = (comment: ReviewComment, level = 0) => {
    const replies = comments.filter(c => c.parent_comment_id === comment.id);
    const isOwner = comment.user_id === user?.id;

    return (
      <div key={comment.id} className={`${level > 0 ? 'ml-6 mt-2 border-l-2 pl-4' : ''}`}>
        <Card className="mb-2">
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                <CardTitle className="text-sm">
                  Comment #{comment.id}
                  {comment.target_field && (
                    <span className="text-xs text-muted-foreground ml-2">
                      on {comment.target_field}
                    </span>
                  )}
                </CardTitle>
                {getCommentTypeBadge(comment.comment_type)}
              </div>
              <div className="flex items-center gap-2">
                {comment.resolved ? (
                  <Badge variant="outline" className="text-green-600">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Resolved
                  </Badge>
                ) : (
                  <>
                    {isOwner && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleResolve(comment.id)}
                      >
                        <CheckCircle2 className="h-4 w-4" />
                      </Button>
                    )}
                    {isOwner && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(comment.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-2">{comment.comment_text}</p>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{formatDate(comment.created_at)}</span>
              {!comment.resolved && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setReplyingTo(comment.id)}
                >
                  <Reply className="h-3 w-3 mr-1" />
                  Reply
                </Button>
              )}
            </div>
            {replyingTo === comment.id && (
              <div className="mt-2 space-y-2">
                <Textarea
                  placeholder="Write a reply..."
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  rows={2}
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => handleReply(comment.id)}>
                    Post Reply
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setReplyingTo(null);
                      setReplyText('');
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
        {replies.map(reply => renderComment(reply, level + 1))}
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Review Comments
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add Comment Form */}
        <div className="space-y-2">
          <Textarea
            placeholder="Add a comment..."
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            rows={3}
          />
          <div className="flex items-center gap-2">
            <select
              value={commentType}
              onChange={(e) => setCommentType(e.target.value as any)}
              className="px-3 py-1 border rounded-md text-sm"
            >
              <option value="general">General</option>
              <option value="annotation">Annotation</option>
              <option value="change_request">Change Request</option>
            </select>
            <Button onClick={handleAddComment} size="sm">
              Add Comment
            </Button>
          </div>
        </div>

        {/* Comments List */}
        <div className="h-[400px] overflow-y-auto">
          {loading ? (
            <div className="text-center text-muted-foreground py-4">Loading comments...</div>
          ) : comments.length === 0 ? (
            <div className="text-center text-muted-foreground py-4">
              No comments yet. Be the first to comment!
            </div>
          ) : (
            <div>
              {comments
                .filter(c => !c.parent_comment_id)
                .map(comment => renderComment(comment))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
