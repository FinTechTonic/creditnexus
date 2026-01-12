import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';

interface LoanDefault {
  id: number;
  loan_id: string;
  borrower_id: string;
  deal_id: string;
  status: string;
  severity: string;
  due_date: string;
  outstanding_amount: number;
  created_at: string;
  updated_at: string;
}

interface LoanAction {
  id: number;
  action_type: 'SMS_REMINDER' | 'EMAIL_SENT' | 'CALL_MADE' | 'STATUS_CHANGE';
  timestamp: string;
  details: string;
  user: string;
}

const LoanRecovery: React.FC = () => {
  const [loanDefaults, setLoanDefaults] = useState<LoanDefault[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sendingReminder, setSendingReminder] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [selectedLoan, setSelectedLoan] = useState<LoanDefault | null>(null);

  useEffect(() => {
    const fetchLoanDefaults = async () => {
      try {
        const response = await fetch('/api/recovery/defaults');
        if (!response.ok) {
          throw new Error('Failed to fetch loan defaults');
        }
        const data = await response.json();
        setLoanDefaults(data);
      } catch (err) {
        if (err instanceof Error) {
            setError(err.message);
        } else {
            setError('An unknown error occurred');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchLoanDefaults();
  }, []);

  const handleSendReminder = async (defaultId: number) => {
    setSendingReminder(defaultId);
    try {
      const response = await fetch(`/api/recovery/defaults/${defaultId}/actions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action_types: ['SMS_REMINDER'],
        }),
      });
      if (!response.ok) {
        throw new Error('Failed to send reminder');
      }
      // Show success notification
      toast.success(`SMS reminder sent successfully for loan ${defaultId}`);
    } catch (err) {
      if (err instanceof Error) {
        toast.error(`Error sending reminder: ${err.message}`);
      } else {
        toast.error('An unknown error occurred while sending the reminder.');
      }
    } finally {
      setSendingReminder(null);
    }
  };

  // Pagination logic
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = loanDefaults.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(loanDefaults.length / itemsPerPage);

  // Mock action history data
  const getMockActionHistory = (loanId: string): LoanAction[] => [
    {
      id: 1,
      action_type: 'SMS_REMINDER',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      details: 'SMS reminder sent to borrower',
      user: 'Recovery Agent'
    },
    {
      id: 2,
      action_type: 'STATUS_CHANGE',
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      details: 'Status changed to overdue',
      user: 'System'
    },
    {
      id: 3,
      action_type: 'EMAIL_SENT',
      timestamp: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
      details: 'Payment reminder email sent',
      user: 'Recovery Agent'
    }
  ];

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Loan Recovery</h1>
      
      {loading && <p>Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}
      
      {!loading && !error && (
        <div className="bg-white shadow rounded-lg overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Loan ID</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Severity</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Due Date</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Outstanding Amount</th>
                <th scope="col" className="relative px-6 py-3"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {currentItems.map((loan) => (
                <tr key={loan.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    <button 
                      onClick={() => setSelectedLoan(loan)}
                      className="text-indigo-600 hover:text-indigo-900 hover:underline"
                    >
                      {loan.loan_id}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{loan.status}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{loan.severity}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(loan.due_date).toLocaleDateString()}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${loan.outstanding_amount.toLocaleString()}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button 
                      onClick={() => handleSendReminder(loan.id)}
                      disabled={sendingReminder === loan.id}
                      className="text-indigo-600 hover:text-indigo-900 disabled:text-gray-400"
                    >
                      {sendingReminder === loan.id ? 'Sending...' : 'Send Reminder'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing <span className="font-medium">{indexOfFirstItem + 1}</span> to{' '}
                    <span className="font-medium">{Math.min(indexOfLastItem, loanDefaults.length)}</span> of{' '}
                    <span className="font-medium">{loanDefaults.length}</span> results
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                    <button
                      onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                      disabled={currentPage === 1}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700">
                      Page {currentPage} of {totalPages}
                    </span>
                    <button
                      onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                      disabled={currentPage === totalPages}
                      className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Loan Details Modal */}
      {selectedLoan && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Loan Details - {selectedLoan.loan_id}</h2>
              <button onClick={() => setSelectedLoan(null)} className="text-gray-500 hover:text-gray-700 text-xl">
                ✕
              </button>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><strong>Borrower ID:</strong> {selectedLoan.borrower_id}</div>
              <div><strong>Deal ID:</strong> {selectedLoan.deal_id}</div>
              <div><strong>Status:</strong> {selectedLoan.status}</div>
              <div><strong>Severity:</strong> {selectedLoan.severity}</div>
              <div><strong>Due Date:</strong> {new Date(selectedLoan.due_date).toLocaleDateString()}</div>
              <div><strong>Outstanding:</strong> ${selectedLoan.outstanding_amount.toLocaleString()}</div>
              <div><strong>Created:</strong> {new Date(selectedLoan.created_at).toLocaleDateString()}</div>
              <div><strong>Updated:</strong> {new Date(selectedLoan.updated_at).toLocaleDateString()}</div>
            </div>
            
            <div className="mt-6 pt-4 border-t">
              <h3 className="font-semibold mb-2">Action History</h3>
              <div className="space-y-2 max-h-32 overflow-y-auto mb-4">
                {getMockActionHistory(selectedLoan.loan_id).map(action => (
                  <div key={action.id} className="text-xs bg-gray-50 p-2 rounded">
                    <div className="flex justify-between">
                      <span className="font-medium">{action.action_type.replace('_', ' ')}</span>
                      <span className="text-gray-500">{new Date(action.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="text-gray-600">{action.details}</div>
                    <div className="text-gray-500 text-xs">by {action.user}</div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="mt-6 pt-4 border-t">
              <h3 className="font-semibold mb-2">Actions</h3>
              <button 
                onClick={() => {
                  handleSendReminder(selectedLoan.id);
                  setSelectedLoan(null);
                }}
                disabled={sendingReminder === selectedLoan.id}
                className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-50"
              >
                {sendingReminder === selectedLoan.id ? 'Sending...' : 'Send SMS Reminder'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoanRecovery;
