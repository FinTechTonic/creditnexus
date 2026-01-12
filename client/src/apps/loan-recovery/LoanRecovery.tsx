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

const LoanRecovery: React.FC = () => {
  const [loanDefaults, setLoanDefaults] = useState<LoanDefault[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sendingReminder, setSendingReminder] = useState<number | null>(null);

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
              {loanDefaults.map((loan) => (
                <tr key={loan.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{loan.loan_id}</td>
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
        </div>
      )}
    </div>
  );
};

export default LoanRecovery;
