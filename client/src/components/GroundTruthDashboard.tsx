/**
 * Ground Truth Dashboard Component
 * 
 * Main dashboard view for the Ground Truth Protocol combining:
 * - Map visualization of all loan assets
 * - Asset verification cards
 * - Create new asset form
 * - Summary statistics
 */

import { useState, useEffect, useCallback } from 'react';
import {
    Plus,
    RefreshCw,
    Map,
    List,
    Satellite,
    Shield,
    AlertTriangle,
    CheckCircle,
    XCircle,
    FileText,
    Loader2,
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { AssetVerificationCard } from './AssetVerificationCard';
import { MapView } from './MapView';
import { useFDC3 } from '@/context/FDC3Context';

interface LoanAsset {
    id: number;
    loan_id: string;
    collateral_address: string | null;
    geo_lat: number | null;
    geo_lon: number | null;
    spt_data: object | null;
    last_verified_score: number | null;
    spt_threshold: number | null;
    risk_status: string;
    base_interest_rate: number | null;
    current_interest_rate: number | null;
    penalty_bps: number | null;
    created_at: string | null;
    last_verified_at: string | null;
    verification_error: string | null;
}

interface AssetStats {
    total: number;
    compliant: number;
    warning: number;
    breach: number;
    pending: number;
}

export function GroundTruthDashboard() {
    const [assets, setAssets] = useState<LoanAsset[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
    const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
    const [showSatellite, setShowSatellite] = useState(false);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [creating, setCreating] = useState(false);
    const { context } = useFDC3();

    // Form state
    const [loanId, setLoanId] = useState('');
    const [documentText, setDocumentText] = useState('');

    const fetchAssets = useCallback(async () => {
        try {
            setLoading(true);
            const response = await fetchWithAuth('/api/loan-assets');
            if (response.ok) {
                const data = await response.json();
                setAssets(data.loan_assets || []);
                setError(null);
            } else {
                throw new Error('Failed to fetch assets');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAssets();
    }, [fetchAssets]);

    useEffect(() => {
        if (context?.type === 'fdc3.creditnexus.loan' && context.loan?.document_text) {
            setLoanId(context.loan.loan_identification_number || context.loan.deal_id || '');
            setDocumentText(context.loan.document_text);
            setShowCreateForm(true);
        }
    }, [context]);

    const createAsset = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!loanId.trim() || !documentText.trim()) return;

        try {
            setCreating(true);
            const response = await fetchWithAuth('/api/loan-assets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    loan_id: loanId,
                    document_text: documentText,
                }),
            });

            if (response.ok) {
                const data = await response.json();
                setAssets(prev => [data.loan_asset, ...prev]);
                setSelectedAssetId(data.loan_asset.id);
                setShowCreateForm(false);
                setLoanId('');
                setDocumentText('');
            } else {
                const err = await response.json();
                throw new Error(err.detail?.message || 'Failed to create asset');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setCreating(false);
        }
    };

    const createDemoAsset = async () => {
        try {
            setCreating(true);
            const response = await fetchWithAuth('/api/loan-assets/demo');
            if (response.ok) {
                const data = await response.json();
                if (data.loan_asset) {
                    setAssets(prev => {
                        const exists = prev.find(a => a.loan_id === data.loan_asset.loan_id);
                        if (exists) return prev;
                        return [data.loan_asset, ...prev];
                    });
                    setSelectedAssetId(data.loan_asset.id);
                }
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setCreating(false);
        }
    };

    // Calculate stats
    const stats: AssetStats = assets.reduce((acc, asset) => {
        acc.total++;
        const status = asset.risk_status?.toUpperCase();
        if (status === 'COMPLIANT') acc.compliant++;
        else if (status === 'WARNING') acc.warning++;
        else if (status === 'BREACH') acc.breach++;
        else acc.pending++;
        return acc;
    }, { total: 0, compliant: 0, warning: 0, breach: 0, pending: 0 });

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Shield className="w-7 h-7 text-blue-400" />
                        Ground Truth Protocol
                    </h1>
                    <p className="text-slate-400 mt-1">
                        Geospatial verification for sustainability-linked loans
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setShowCreateForm(!showCreateForm)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                    >
                        <Plus className="w-4 h-4" />
                        New Asset
                    </button>

                    <button
                        onClick={fetchAssets}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-4 gap-4">
                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/20 rounded-lg">
                            <FileText className="w-5 h-5 text-blue-400" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-white">{stats.total}</p>
                            <p className="text-sm text-slate-400">Total Assets</p>
                        </div>
                    </div>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/20 rounded-lg">
                            <CheckCircle className="w-5 h-5 text-emerald-400" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-emerald-400">{stats.compliant}</p>
                            <p className="text-sm text-slate-400">Compliant</p>
                        </div>
                    </div>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-500/20 rounded-lg">
                            <AlertTriangle className="w-5 h-5 text-amber-400" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-amber-400">{stats.warning}</p>
                            <p className="text-sm text-slate-400">Warning</p>
                        </div>
                    </div>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-red-500/20 rounded-lg">
                            <XCircle className="w-5 h-5 text-red-400" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-red-400">{stats.breach}</p>
                            <p className="text-sm text-slate-400">Breach</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Create Form */}
            {showCreateForm && (
                <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                    <h2 className="text-lg font-semibold text-white mb-4">Create New Loan Asset</h2>

                    <form onSubmit={createAsset} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">
                                Loan ID
                            </label>
                            <input
                                type="text"
                                value={loanId}
                                onChange={(e) => setLoanId(e.target.value)}
                                placeholder="e.g., LOAN-2024-001"
                                className="w-full px-4 py-2 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-1">
                                Loan Agreement Text
                            </label>
                            <textarea
                                value={documentText}
                                onChange={(e) => setDocumentText(e.target.value)}
                                placeholder="Paste the loan agreement text here, including sustainability covenants and collateral address..."
                                rows={6}
                                className="w-full px-4 py-2 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                                required
                            />
                        </div>

                        <div className="flex items-center gap-3">
                            <button
                                type="submit"
                                disabled={creating}
                                className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-lg transition-all disabled:opacity-50"
                            >
                                {creating ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Processing...
                                    </>
                                ) : (
                                    <>
                                        <Shield className="w-4 h-4" />
                                        Securitize & Verify
                                    </>
                                )}
                            </button>

                            <button
                                type="button"
                                onClick={createDemoAsset}
                                disabled={creating}
                                className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
                            >
                                or use Demo Data
                            </button>

                            <button
                                type="button"
                                onClick={() => setShowCreateForm(false)}
                                className="ml-auto px-4 py-2 text-slate-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Error Display */}
            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                    <p className="text-red-400">{error}</p>
                </div>
            )}

            {/* View Toggle */}
            <div className="flex items-center gap-4">
                <div className="flex items-center bg-slate-800/50 rounded-lg p-1">
                    <button
                        onClick={() => setViewMode('map')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${viewMode === 'map'
                            ? 'bg-blue-600 text-white'
                            : 'text-slate-400 hover:text-white'
                            }`}
                    >
                        <Map className="w-4 h-4" />
                        Map View
                    </button>
                    <button
                        onClick={() => setViewMode('list')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${viewMode === 'list'
                            ? 'bg-blue-600 text-white'
                            : 'text-slate-400 hover:text-white'
                            }`}
                    >
                        <List className="w-4 h-4" />
                        List View
                    </button>
                </div>

                {viewMode === 'map' && (
                    <button
                        onClick={() => setShowSatellite(!showSatellite)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${showSatellite
                            ? 'bg-emerald-600 text-white'
                            : 'bg-slate-700 text-slate-300 hover:text-white'
                            }`}
                    >
                        <Satellite className="w-4 h-4" />
                        Satellite
                    </button>
                )}
            </div>

            {/* Main Content */}
            <div className="grid grid-cols-3 gap-6">
                {/* Map/List View */}
                <div className="col-span-2">
                    {viewMode === 'map' ? (
                        <MapView
                            assets={assets}
                            selectedAssetId={selectedAssetId ?? undefined}
                            onAssetSelect={(asset) => setSelectedAssetId(asset.id)}
                            height="500px"
                            showSatellite={showSatellite}
                        />
                    ) : (
                        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
                            <div className="max-h-[500px] overflow-y-auto">
                                {assets.length === 0 ? (
                                    <div className="p-8 text-center text-slate-400">
                                        <Shield className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                        <p>No loan assets yet</p>
                                        <button
                                            onClick={createDemoAsset}
                                            className="mt-2 text-blue-400 hover:underline"
                                        >
                                            Create demo asset
                                        </button>
                                    </div>
                                ) : (
                                    <table className="w-full">
                                        <thead className="bg-slate-900/50 sticky top-0">
                                            <tr>
                                                <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Loan ID</th>
                                                <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Status</th>
                                                <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">NDVI</th>
                                                <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Rate</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-700/50">
                                            {assets.map(asset => (
                                                <tr
                                                    key={asset.id}
                                                    onClick={() => setSelectedAssetId(asset.id)}
                                                    className={`cursor-pointer transition-colors ${selectedAssetId === asset.id
                                                        ? 'bg-blue-500/10'
                                                        : 'hover:bg-slate-700/30'
                                                        }`}
                                                >
                                                    <td className="px-4 py-3 text-white font-medium">{asset.loan_id}</td>
                                                    <td className="px-4 py-3">
                                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${asset.risk_status === 'COMPLIANT' ? 'bg-emerald-500/20 text-emerald-400' :
                                                            asset.risk_status === 'WARNING' ? 'bg-amber-500/20 text-amber-400' :
                                                                asset.risk_status === 'BREACH' ? 'bg-red-500/20 text-red-400' :
                                                                    'bg-slate-500/20 text-slate-400'
                                                            }`}>
                                                            {asset.risk_status}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-slate-300">
                                                        {asset.last_verified_score !== null
                                                            ? `${(asset.last_verified_score * 100).toFixed(1)}%`
                                                            : 'N/A'}
                                                    </td>
                                                    <td className="px-4 py-3 text-slate-300">
                                                        {asset.current_interest_rate?.toFixed(2)}%
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Selected Asset Card */}
                <div className="col-span-1">
                    {selectedAssetId ? (
                        <AssetVerificationCard
                            assetId={selectedAssetId}
                            onVerify={fetchAssets}
                        />
                    ) : (
                        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50 text-center">
                            <Shield className="w-12 h-12 mx-auto mb-3 text-slate-500" />
                            <p className="text-slate-400">Select an asset to view details</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default GroundTruthDashboard;
