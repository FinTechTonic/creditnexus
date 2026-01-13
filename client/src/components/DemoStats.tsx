import React, { useState, useEffect } from 'react';

export const DemoStats: React.FC = () => {
  const [stats, setStats] = useState({
    deals: 0,
    documents: 0,
    loading: true,
    error: null
  });

  useEffect(() => {
    const fetchDemoData = async () => {
      try {
        // Fetch demo deals
        const dealsResponse = await fetch('/api/deals?is_demo=true');
        if (dealsResponse.ok) {
          const dealsData = await dealsResponse.json();
          setStats(prev => ({ ...prev, deals: dealsData.length || 0 }));
        }

        // Fetch demo documents
        const docsResponse = await fetch('/api/documents?is_demo=true');
        if (docsResponse.ok) {
          const docsData = await docsResponse.json();
          setStats(prev => ({ ...prev, documents: docsData.length || 0 }));
        }

        setStats(prev => ({ ...prev, loading: false }));
      } catch (error) {
        setStats(prev => ({ ...prev, loading: false, error: error.message }));
      }
    };

    fetchDemoData();
  }, []);

  if (stats.loading) {
    return <div className="p-4 bg-blue-50 rounded-lg">Loading demo stats...</div>;
  }

  if (stats.error) {
    return <div className="p-4 bg-red-50 rounded-lg text-red-600">Error: {stats.error}</div>;
  }

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-xl border border-blue-200 shadow-sm">
      <h3 className="text-xl font-semibold text-blue-800 mb-4 flex items-center gap-2">
        <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
        Demo Data Statistics
      </h3>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-white p-4 rounded-lg border border-blue-100">
          <div className="text-3xl font-bold text-blue-600">{stats.deals}</div>
          <div className="text-sm text-gray-500 mt-1">Total Deals</div>
        </div>

        <div className="bg-white p-4 rounded-lg border border-blue-100">
          <div className="text-3xl font-bold text-blue-600">{stats.documents}</div>
          <div className="text-sm text-gray-500 mt-1">Total Documents</div>
        </div>
      </div>

      <div className="flex items-center gap-2 text-sm text-blue-600 bg-blue-50 px-3 py-1 rounded-full inline-flex">
        <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
        <span>Demo Mode Active</span>
      </div>
    </div>
  );
};