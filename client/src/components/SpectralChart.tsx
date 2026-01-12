import { useMemo } from 'react';
import { Zap, Leaf, AlertTriangle } from 'lucide-react';

interface SpectralProfile {
    detected: Record<string, number>;
    reference_healthy: Record<string, number>;
    wavelengths: Record<string, number>;
    ndvi: number;
    red_edge_slope: number;
    vegetation_health: 'HEALTHY' | 'STRESSED' | 'DEGRADED';
    bands_analyzed: string[];
    sensor: string;
}

interface SpectralChartProps {
    spectralData: SpectralProfile | null;
    isLoading?: boolean;
}

export function SpectralChart({ spectralData, isLoading = false }: SpectralChartProps) {
    // Prepare chart data
    const chartData = useMemo(() => {
        if (!spectralData) return null;

        const bands = Object.keys(spectralData.detected);
        return bands.map((band) => ({
            band,
            wavelength: spectralData.wavelengths[band],
            detected: spectralData.detected[band],
            healthy: spectralData.reference_healthy[band],
            label: band.replace('_', ' '),
        }));
    }, [spectralData]);

    // Calculate max value for scaling
    const maxValue = useMemo(() => {
        if (!chartData) return 1;
        return Math.max(
            ...chartData.map((d) => Math.max(d.detected, d.healthy))
        ) * 1.2;
    }, [chartData]);

    if (isLoading) {
        return (
            <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 animate-pulse">
                <div className="h-4 bg-zinc-700 rounded w-1/3 mb-4"></div>
                <div className="h-48 bg-zinc-800 rounded"></div>
            </div>
        );
    }

    if (!spectralData || !chartData) {
        return (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 text-center">
                <Zap className="w-8 h-8 text-zinc-600 mx-auto mb-2" />
                <p className="text-zinc-500 text-sm">Spectral data will appear after verification</p>
            </div>
        );
    }

    const healthColor = spectralData.vegetation_health === 'HEALTHY'
        ? 'text-green-400'
        : spectralData.vegetation_health === 'STRESSED'
            ? 'text-yellow-400'
            : 'text-red-400';

    const healthBg = spectralData.vegetation_health === 'HEALTHY'
        ? 'bg-green-500/20'
        : spectralData.vegetation_health === 'STRESSED'
            ? 'bg-yellow-500/20'
            : 'bg-red-500/20';

    return (
        <div className="bg-gradient-to-br from-zinc-900 to-slate-900 border border-zinc-700 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 border-b border-zinc-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-indigo-400" />
                    <h3 className="text-sm font-semibold text-white">Spectral Signature Analysis</h3>
                </div>
                <span className="text-xs text-zinc-500 font-mono">{spectralData.sensor}</span>
            </div>

            {/* Chart Area */}
            <div className="p-4">
                {/* Legend */}
                <div className="flex items-center gap-6 mb-4 text-xs">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-cyan-500"></div>
                        <span className="text-zinc-400">Detected</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-green-500 opacity-50"></div>
                        <span className="text-zinc-400">Healthy Reference</span>
                    </div>
                </div>

                {/* Bar Chart */}
                <div className="relative h-48 flex items-end justify-between gap-2">
                    {chartData.map((data, index) => {
                        const isRedEdge = data.wavelength >= 700 && data.wavelength <= 800;
                        const detectedHeight = (data.detected / maxValue) * 100;
                        const healthyHeight = (data.healthy / maxValue) * 100;

                        return (
                            <div key={data.band} className="flex-1 flex flex-col items-center gap-1 relative group">
                                {/* Red Edge Annotation */}
                                {isRedEdge && index === 3 && (
                                    <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 whitespace-nowrap z-10">
                                        <span className="text-[10px] text-amber-400 font-mono bg-amber-400/10 px-1.5 py-0.5 rounded border border-amber-400/30">
                                            RED EDGE →
                                        </span>
                                    </div>
                                )}

                                {/* Bars Container */}
                                <div className="w-full h-40 relative flex items-end justify-center gap-0.5">
                                    {/* Healthy Reference Bar (background) */}
                                    <div
                                        className="w-3 bg-green-500/30 rounded-t transition-all duration-500"
                                        style={{ height: `${healthyHeight}%` }}
                                    />
                                    {/* Detected Bar (foreground) */}
                                    <div
                                        className={`w-3 rounded-t transition-all duration-500 ${isRedEdge ? 'bg-gradient-to-t from-cyan-600 to-cyan-400' : 'bg-cyan-500'
                                            }`}
                                        style={{ height: `${detectedHeight}%` }}
                                    />
                                </div>

                                {/* Band Label */}
                                <span className={`text-[9px] font-mono ${isRedEdge ? 'text-amber-300' : 'text-zinc-500'}`}>
                                    {data.wavelength}nm
                                </span>

                                {/* Tooltip on hover */}
                                <div className="absolute bottom-full mb-2 hidden group-hover:block bg-black/90 text-white text-xs p-2 rounded shadow-lg z-20 whitespace-nowrap">
                                    <div className="font-bold">{data.label}</div>
                                    <div className="text-cyan-400">Detected: {(data.detected * 100).toFixed(1)}%</div>
                                    <div className="text-green-400">Healthy: {(data.healthy * 100).toFixed(1)}%</div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* X-axis label */}
                <div className="text-center mt-2">
                    <span className="text-xs text-zinc-500">Wavelength (nm)</span>
                </div>
            </div>

            {/* Stats Footer */}
            <div className="px-4 py-3 bg-black/30 border-t border-zinc-700 grid grid-cols-3 gap-4">
                <div>
                    <span className="text-zinc-500 text-[10px] uppercase tracking-wider block">NDVI</span>
                    <span className={`font-mono font-bold ${healthColor}`}>
                        {spectralData.ndvi.toFixed(3)}
                    </span>
                </div>
                <div>
                    <span className="text-zinc-500 text-[10px] uppercase tracking-wider block">Red Edge Slope</span>
                    <span className="font-mono text-white">{spectralData.red_edge_slope.toFixed(2)}</span>
                </div>
                <div>
                    <span className="text-zinc-500 text-[10px] uppercase tracking-wider block">Status</span>
                    <div className="flex items-center gap-1">
                        {spectralData.vegetation_health === 'HEALTHY' ? (
                            <Leaf className="w-3 h-3 text-green-400" />
                        ) : (
                            <AlertTriangle className="w-3 h-3 text-yellow-400" />
                        )}
                        <span className={`text-xs font-bold uppercase ${healthColor} ${healthBg} px-1.5 py-0.5 rounded`}>
                            {spectralData.vegetation_health}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default SpectralChart;
