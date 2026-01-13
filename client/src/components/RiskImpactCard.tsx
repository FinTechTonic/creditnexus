import { AlertTriangle, TrendingUp, DollarSign, ArrowUpRight, TrendingDown, BarChart3, Users, Activity } from 'lucide-react';

interface HistoricalDataPoint {
    date: string;
    ndvi_score: number;
    compliance_status: string;
}

interface PortfolioComparison {
    portfolio_avg_ndvi: number;
    portfolio_avg_spread_bps: number;
    portfolio_breach_rate: number;
    portfolio_avg_impact: number;
}

interface RiskAdjustedMetrics {
    risk_adjusted_return?: number;
    sharpe_ratio?: number;
    volatility?: number;
    value_at_risk?: number;
}

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
    historical_data?: HistoricalDataPoint[];
    portfolio_comparison?: PortfolioComparison;
    risk_metrics?: RiskAdjustedMetrics;
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

                {/* Historical Trends */}
                {impactData.historical_data && impactData.historical_data.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-green-500/20">
                        <div className="flex items-center gap-2 mb-2">
                            <BarChart3 className="w-3 h-3 text-green-400" />
                            <span className="text-xs text-zinc-400 uppercase tracking-wider">Historical Trend</span>
                        </div>
                        <div className="flex items-end gap-1 h-12">
                            {impactData.historical_data.slice(-6).map((point, idx) => {
                                const height = (point.ndvi_score / impactData.spt_threshold) * 100;
                                const isCompliant = point.compliance_status === 'COMPLIANT' || point.compliance_status === 'EXCEEDS_TARGET';
                                return (
                                    <div key={idx} className="flex-1 flex flex-col items-center">
                                        <div
                                            className={`w-full rounded-t ${isCompliant ? 'bg-green-500/60' : 'bg-yellow-500/60'}`}
                                            style={{ height: `${Math.min(height, 100)}%` }}
                                            title={`${point.date}: ${point.ndvi_score.toFixed(2)}`}
                                        />
                                        <span className="text-[10px] text-zinc-500 mt-1">
                                            {new Date(point.date).toLocaleDateString('en-US', { month: 'short' })}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Portfolio Comparison */}
                {impactData.portfolio_comparison && (
                    <div className="mt-4 pt-3 border-t border-green-500/20">
                        <div className="flex items-center gap-2 mb-2">
                            <Users className="w-3 h-3 text-green-400" />
                            <span className="text-xs text-zinc-400 uppercase tracking-wider">Portfolio Comparison</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                                <span className="text-zinc-500 block">vs Portfolio Avg NDVI</span>
                                <span className={`font-mono ${impactData.ndvi_score >= impactData.portfolio_comparison.portfolio_avg_ndvi ? 'text-green-400' : 'text-yellow-400'}`}>
                                    {impactData.ndvi_score >= impactData.portfolio_comparison.portfolio_avg_ndvi ? '+' : ''}
                                    {(impactData.ndvi_score - impactData.portfolio_comparison.portfolio_avg_ndvi).toFixed(2)}
                                </span>
                            </div>
                            <div>
                                <span className="text-zinc-500 block">Portfolio Breach Rate</span>
                                <span className="text-white font-mono">
                                    {(impactData.portfolio_comparison.portfolio_breach_rate * 100).toFixed(1)}%
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Risk-Adjusted Metrics */}
                {impactData.risk_metrics && (
                    <div className="mt-4 pt-3 border-t border-green-500/20">
                        <div className="flex items-center gap-2 mb-2">
                            <Activity className="w-3 h-3 text-green-400" />
                            <span className="text-xs text-zinc-400 uppercase tracking-wider">Risk Metrics</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                            {impactData.risk_metrics.risk_adjusted_return !== undefined && (
                                <div>
                                    <span className="text-zinc-500 block">Risk-Adjusted Return</span>
                                    <span className="text-white font-mono">
                                        {(impactData.risk_metrics.risk_adjusted_return * 100).toFixed(2)}%
                                    </span>
                                </div>
                            )}
                            {impactData.risk_metrics.sharpe_ratio !== undefined && (
                                <div>
                                    <span className="text-zinc-500 block">Sharpe Ratio</span>
                                    <span className="text-white font-mono">
                                        {impactData.risk_metrics.sharpe_ratio.toFixed(2)}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                )}
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

                {/* Historical Trends */}
                {impactData.historical_data && impactData.historical_data.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-red-500/20">
                        <div className="flex items-center gap-2 mb-2">
                            <BarChart3 className="w-3 h-3 text-red-400" />
                            <span className="text-xs text-zinc-400 uppercase tracking-wider">Historical Trend</span>
                        </div>
                        <div className="flex items-end gap-1 h-12">
                            {impactData.historical_data.slice(-6).map((point, idx) => {
                                const height = (point.ndvi_score / impactData.spt_threshold) * 100;
                                const isCompliant = point.compliance_status === 'COMPLIANT' || point.compliance_status === 'EXCEEDS_TARGET';
                                return (
                                    <div key={idx} className="flex-1 flex flex-col items-center">
                                        <div
                                            className={`w-full rounded-t ${isCompliant ? 'bg-green-500/60' : isBreach ? 'bg-red-500/60' : 'bg-yellow-500/60'}`}
                                            style={{ height: `${Math.min(height, 100)}%` }}
                                            title={`${point.date}: ${point.ndvi_score.toFixed(2)}`}
                                        />
                                        <span className="text-[10px] text-zinc-500 mt-1">
                                            {new Date(point.date).toLocaleDateString('en-US', { month: 'short' })}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                        <div className="mt-2 flex items-center gap-2 text-xs">
                            <TrendingDown className={`w-3 h-3 ${isBreach ? 'text-red-400' : 'text-yellow-400'}`} />
                            <span className="text-zinc-400">
                                {isBreach ? 'Declining trend detected' : 'Performance below target'}
                            </span>
                        </div>
                    </div>
                )}

                {/* Portfolio Comparison */}
                {impactData.portfolio_comparison && (
                    <div className={`mt-4 pt-3 border-t ${isBreach ? 'border-red-500/20' : 'border-yellow-500/20'}`}>
                        <div className="flex items-center gap-2 mb-2">
                            <Users className={`w-3 h-3 ${isBreach ? 'text-red-400' : 'text-yellow-400'}`} />
                            <span className="text-xs text-zinc-400 uppercase tracking-wider">Portfolio Comparison</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                                <span className="text-zinc-500 block">vs Portfolio Avg NDVI</span>
                                <span className={`font-mono ${impactData.ndvi_score >= impactData.portfolio_comparison.portfolio_avg_ndvi ? 'text-green-400' : isBreach ? 'text-red-400' : 'text-yellow-400'}`}>
                                    {impactData.ndvi_score >= impactData.portfolio_comparison.portfolio_avg_ndvi ? '+' : ''}
                                    {(impactData.ndvi_score - impactData.portfolio_comparison.portfolio_avg_ndvi).toFixed(2)}
                                </span>
                            </div>
                            <div>
                                <span className="text-zinc-500 block">Portfolio Breach Rate</span>
                                <span className="text-white font-mono">
                                    {(impactData.portfolio_comparison.portfolio_breach_rate * 100).toFixed(1)}%
                                </span>
                            </div>
                            <div>
                                <span className="text-zinc-500 block">vs Portfolio Avg Impact</span>
                                <span className={`font-mono ${Math.abs(impactData.annualized_impact) < Math.abs(impactData.portfolio_comparison.portfolio_avg_impact) ? 'text-green-400' : isBreach ? 'text-red-400' : 'text-yellow-400'}`}>
                                    {Math.abs(impactData.annualized_impact) < Math.abs(impactData.portfolio_comparison.portfolio_avg_impact) ? 'Better' : 'Worse'}
                                </span>
                            </div>
                            <div>
                                <span className="text-zinc-500 block">Portfolio Avg Spread</span>
                                <span className="text-white font-mono">
                                    {impactData.portfolio_comparison.portfolio_avg_spread_bps} bps
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Risk-Adjusted Metrics */}
                {impactData.risk_metrics && (
                    <div className={`mt-4 pt-3 border-t ${isBreach ? 'border-red-500/20' : 'border-yellow-500/20'}`}>
                        <div className="flex items-center gap-2 mb-2">
                            <Activity className={`w-3 h-3 ${isBreach ? 'text-red-400' : 'text-yellow-400'}`} />
                            <span className="text-xs text-zinc-400 uppercase tracking-wider">Risk Metrics</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                            {impactData.risk_metrics.risk_adjusted_return !== undefined && (
                                <div>
                                    <span className="text-zinc-500 block">Risk-Adjusted Return</span>
                                    <span className={`font-mono ${impactData.risk_metrics.risk_adjusted_return > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        {(impactData.risk_metrics.risk_adjusted_return * 100).toFixed(2)}%
                                    </span>
                                </div>
                            )}
                            {impactData.risk_metrics.sharpe_ratio !== undefined && (
                                <div>
                                    <span className="text-zinc-500 block">Sharpe Ratio</span>
                                    <span className={`font-mono ${impactData.risk_metrics.sharpe_ratio > 1 ? 'text-green-400' : impactData.risk_metrics.sharpe_ratio > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                                        {impactData.risk_metrics.sharpe_ratio.toFixed(2)}
                                    </span>
                                </div>
                            )}
                            {impactData.risk_metrics.volatility !== undefined && (
                                <div>
                                    <span className="text-zinc-500 block">Volatility</span>
                                    <span className="text-white font-mono">
                                        {(impactData.risk_metrics.volatility * 100).toFixed(2)}%
                                    </span>
                                </div>
                            )}
                            {impactData.risk_metrics.value_at_risk !== undefined && (
                                <div>
                                    <span className="text-zinc-500 block">Value at Risk (95%)</span>
                                    <span className="text-white font-mono">
                                        ${impactData.risk_metrics.value_at_risk.toLocaleString()}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default RiskImpactCard;
