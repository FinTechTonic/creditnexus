import { AlertTriangle, TrendingUp, DollarSign, ArrowUpRight } from 'lucide-react';

interface FinancialImpactData {
    compliance_status: string;
    ndvi_score: number;
    spt_threshold: number;
    base_spread_bps: number;
    penalty_bps: number;
    new_spread_bps: number;
    base_rate_pct: string;
    new_rate_pct: string;
    spread_adjustment_display: string;
    annualized_impact: number;
    monthly_impact: number;
    principal: number;
    is_breach: boolean;
    message: string;
}

interface RiskImpactCardProps {
    impactData: FinancialImpactData | null;
    isLoading?: boolean;
}

export function RiskImpactCard({ impactData, isLoading = false }: RiskImpactCardProps) {
    if (isLoading) {
        return (
            <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 animate-pulse">
                <div className="h-4 bg-zinc-700 rounded w-1/3 mb-3"></div>
                <div className="h-8 bg-zinc-700 rounded w-1/2 mb-2"></div>
                <div className="h-4 bg-zinc-700 rounded w-2/3"></div>
            </div>
        );
    }

    if (!impactData) {
        return (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 text-center">
                <DollarSign className="w-8 h-8 text-zinc-600 mx-auto mb-2" />
                <p className="text-zinc-500 text-sm">Financial impact will appear after verification</p>
            </div>
        );
    }

    const isBreach = impactData.is_breach;
    const isCompliant = impactData.compliance_status === 'COMPLIANT' || impactData.compliance_status === 'EXCEEDS_TARGET';

    if (isCompliant) {
        return (
            <div className="bg-gradient-to-br from-green-900/30 to-emerald-900/20 border border-green-500/30 rounded-lg p-4 shadow-lg shadow-green-500/5">
                <div className="flex items-center gap-2 mb-3">
                    <div className="p-1.5 rounded-full bg-green-500/20">
                        <TrendingUp className="w-4 h-4 text-green-400" />
                    </div>
                    <h3 className="text-green-400 font-semibold text-sm uppercase tracking-wider">
                        {impactData.compliance_status === 'EXCEEDS_TARGET' ? 'Exceeds Target' : 'Compliant'}
                    </h3>
                </div>

                <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-mono font-bold text-white">
                        {impactData.spread_adjustment_display}
                    </span>
                    <span className="text-sm text-zinc-400">Spread Adjustment</span>
                </div>

                <p className="text-green-300/80 text-sm mt-3">{impactData.message}</p>

                <div className="mt-4 pt-3 border-t border-green-500/20 grid grid-cols-2 gap-4 text-xs">
                    <div>
                        <span className="text-zinc-500 block">NDVI Score</span>
                        <span className="text-green-400 font-mono font-bold">{impactData.ndvi_score.toFixed(2)}</span>
                    </div>
                    <div>
                        <span className="text-zinc-500 block">SPT Threshold</span>
                        <span className="text-white font-mono">{impactData.spt_threshold}</span>
                    </div>
                </div>
            </div>
        );
    }

    // Breach or Warning state
    return (
        <div className={`relative overflow-hidden rounded-lg shadow-lg ${isBreach
                ? 'bg-gradient-to-br from-red-900/40 to-orange-900/20 border-l-4 border-red-500 shadow-red-500/10'
                : 'bg-gradient-to-br from-yellow-900/30 to-orange-900/20 border-l-4 border-yellow-500 shadow-yellow-500/10'
            }`}>
            {/* Animated warning flash for breach */}
            {isBreach && (
                <div className="absolute inset-0 bg-red-500/5 animate-pulse pointer-events-none" />
            )}

            <div className="relative p-4">
                <div className="flex items-center gap-2 mb-3">
                    <div className={`p-1.5 rounded-full ${isBreach ? 'bg-red-500/20' : 'bg-yellow-500/20'}`}>
                        <AlertTriangle className={`w-4 h-4 ${isBreach ? 'text-red-400' : 'text-yellow-400'}`} />
                    </div>
                    <h3 className={`font-bold text-xs uppercase tracking-wider ${isBreach ? 'text-red-400' : 'text-yellow-400'
                        }`}>
                        {isBreach ? 'Automatic Margin Ratchet Triggered' : 'Warning Zone - Minor Adjustment'}
                    </h3>
                </div>

                {/* Main Impact Display */}
                <div className="flex justify-between items-baseline mt-2">
                    <span className="text-3xl font-mono font-bold text-white">
                        {impactData.spread_adjustment_display}
                    </span>
                    <span className="text-sm text-zinc-400">Spread Adjustment</span>
                </div>

                {/* Financial Cost - The "Money Shot" */}
                <div className={`mt-4 pt-3 border-t ${isBreach ? 'border-red-500/30' : 'border-yellow-500/30'}`}>
                    <div className="flex items-center gap-2">
                        <ArrowUpRight className={`w-5 h-5 ${isBreach ? 'text-red-500' : 'text-yellow-500'}`} />
                        <span className={`text-2xl font-bold ${isBreach ? 'text-red-400' : 'text-yellow-400'}`}>
                            +${impactData.annualized_impact.toLocaleString()}
                        </span>
                        <span className="text-zinc-400 text-sm">/ year</span>
                    </div>
                    <p className="text-zinc-500 text-xs mt-1">Additional Interest Cost</p>
                </div>

                {/* Detailed Breakdown */}
                <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-black/30 rounded p-2">
                        <span className="text-zinc-500 block">Base Rate</span>
                        <span className="text-white font-mono">{impactData.base_rate_pct}</span>
                    </div>
                    <div className="bg-black/30 rounded p-2">
                        <span className="text-zinc-500 block">New Rate</span>
                        <span className={`font-mono font-bold ${isBreach ? 'text-red-400' : 'text-yellow-400'}`}>
                            {impactData.new_rate_pct}
                        </span>
                    </div>
                    <div className="bg-black/30 rounded p-2">
                        <span className="text-zinc-500 block">NDVI Score</span>
                        <span className={`font-mono ${isBreach ? 'text-red-400' : 'text-yellow-400'}`}>
                            {impactData.ndvi_score.toFixed(2)}
                        </span>
                    </div>
                    <div className="bg-black/30 rounded p-2">
                        <span className="text-zinc-500 block">Monthly Cost</span>
                        <span className="text-white font-mono">
                            +${impactData.monthly_impact.toLocaleString()}
                        </span>
                    </div>
                </div>

                {/* Status Message */}
                <p className={`mt-4 text-sm ${isBreach ? 'text-red-300/80' : 'text-yellow-300/80'}`}>
                    {impactData.message}
                </p>
            </div>
        </div>
    );
}

export default RiskImpactCard;
