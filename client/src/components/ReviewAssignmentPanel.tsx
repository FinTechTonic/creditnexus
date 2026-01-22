import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  UserPlus, 
  Users, 
  Clock, 
  CheckCircle2, 
  Calendar
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';

interface ReviewAssignment {
  id: number;
  document_id: number;
  workflow_id?: number;
  reviewer_id: number;
  assigned_by: number;
  assigned_at: string;
  due_date?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  completed_at?: string;
  review_notes?: string;
}

interface User {
  id: number;
  email: string;
  display_name?: string;
}

interface ReviewAssignmentPanelProps {
  documentId: number;
  onAssignmentAdded?: () => void;
}

export function ReviewAssignmentPanel({ 
  documentId, 
  onAssignmentAdded 
}: ReviewAssignmentPanelProps) {
  const [assignments, setAssignments] = useState<ReviewAssignment[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAssignForm, setShowAssignForm] = useState(false);
  const [selectedReviewer, setSelectedReviewer] = useState<string>('');
  const [dueDate, setDueDate] = useState('');

  useEffect(() => {
    loadAssignments();
    loadUsers();
  }, [documentId]);

  const loadAssignments = async () => {
    try {
      setLoading(true);
      const response = await fetchWithAuth(
        `/api/reviews/documents/${documentId}/assignments`
      );
      
      if (response.ok) {
        const data = await response.json();
        setAssignments(data.assignments || []);
      }
    } catch (error) {
      console.error('Error loading assignments:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      // Assuming there's a users endpoint - adjust if needed
      const response = await fetchWithAuth('/api/users');
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || data || []);
      }
    } catch (error) {
      console.error('Error loading users:', error);
    }
  };

  const handleAssignReviewer = async () => {
    if (!selectedReviewer) return;

    try {
      const response = await fetchWithAuth(
        `/api/reviews/documents/${documentId}/assign`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            reviewer_id: parseInt(selectedReviewer),
            due_date: dueDate || undefined,
          }),
        }
      );

      if (response.ok) {
        setSelectedReviewer('');
        setDueDate('');
        setShowAssignForm(false);
        loadAssignments();
        onAssignmentAdded?.();
      }
    } catch (error) {
      console.error('Error assigning reviewer:', error);
    }
  };

  const handleUpdateStatus = async (assignmentId: number, status: string) => {
    try {
      const response = await fetchWithAuth(
        `/api/reviews/assignments/${assignmentId}/status`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status }),
        }
      );

      if (response.ok) {
        loadAssignments();
      }
    } catch (error) {
      console.error('Error updating assignment status:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    const badges = {
      pending: <Badge variant="secondary">Pending</Badge>,
      in_progress: <Badge variant="default" className="bg-blue-600">In Progress</Badge>,
      completed: <Badge variant="default" className="bg-green-600">Completed</Badge>,
      cancelled: <Badge variant="destructive">Cancelled</Badge>,
    };
    return badges[status as keyof typeof badges] || badges.pending;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Not set';
    return new Date(dateString).toLocaleString();
  };

  const getUserName = (userId: number) => {
    const userObj = users.find(u => u.id === userId);
    return userObj?.display_name || userObj?.email || `User ${userId}`;
  };

  const isOverdue = (dueDate?: string) => {
    if (!dueDate) return false;
    return new Date(dueDate) < new Date();
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Review Assignments
          </CardTitle>
          <Button
            size="sm"
            onClick={() => setShowAssignForm(!showAssignForm)}
          >
            <UserPlus className="h-4 w-4 mr-2" />
            Assign Reviewer
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Assign Form */}
        {showAssignForm && (
          <Card className="bg-muted/50">
            <CardContent className="pt-6 space-y-4">
              <div>
                <Label htmlFor="reviewer">Reviewer</Label>
                <Select value={selectedReviewer} onValueChange={setSelectedReviewer}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select reviewer" />
                  </SelectTrigger>
                  <SelectContent>
                    {users.map((u) => (
                      <SelectItem key={u.id} value={u.id.toString()}>
                        {u.display_name || u.email}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="dueDate">Due Date (Optional)</Label>
                <Input
                  id="dueDate"
                  type="datetime-local"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleAssignReviewer}>Assign</Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowAssignForm(false);
                    setSelectedReviewer('');
                    setDueDate('');
                  }}
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Assignments List */}
        {loading ? (
          <div className="text-center text-muted-foreground py-4">Loading assignments...</div>
        ) : assignments.length === 0 ? (
          <div className="text-center text-muted-foreground py-4">
            No reviewers assigned yet.
          </div>
        ) : (
          <div className="space-y-2">
            {assignments.map((assignment) => (
              <Card key={assignment.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-semibold">
                        {getUserName(assignment.reviewer_id)}
                      </span>
                      {getStatusBadge(assignment.status)}
                    </div>
                    <div className="text-sm text-muted-foreground space-y-1">
                      <div className="flex items-center gap-2">
                        <Clock className="h-3 w-3" />
                        Assigned: {formatDate(assignment.assigned_at)}
                      </div>
                      {assignment.due_date && (
                        <div className={`flex items-center gap-2 ${isOverdue(assignment.due_date) && assignment.status !== 'completed' ? 'text-red-600' : ''}`}>
                          <Calendar className="h-3 w-3" />
                          Due: {formatDate(assignment.due_date)}
                          {isOverdue(assignment.due_date) && assignment.status !== 'completed' && (
                            <Badge variant="destructive" className="ml-2">Overdue</Badge>
                          )}
                        </div>
                      )}
                      {assignment.completed_at && (
                        <div className="flex items-center gap-2 text-green-600">
                          <CheckCircle2 className="h-3 w-3" />
                          Completed: {formatDate(assignment.completed_at)}
                        </div>
                      )}
                      {assignment.review_notes && (
                        <div className="mt-2 p-2 bg-muted rounded text-xs">
                          {assignment.review_notes}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    {assignment.status === 'pending' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleUpdateStatus(assignment.id, 'in_progress')}
                      >
                        Start Review
                      </Button>
                    )}
                    {assignment.status === 'in_progress' && (
                      <Button
                        size="sm"
                        variant="default"
                        onClick={() => handleUpdateStatus(assignment.id, 'completed')}
                      >
                        Complete
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
