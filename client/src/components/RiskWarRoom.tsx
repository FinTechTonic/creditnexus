import { useState, useEffect } from 'react';
import { useFDC3 } from '@/context/FDC3Context';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card } from './ui/card';
import { Search, RadioTower, AlertTriangle, ShieldCheck, TrendingUp, Zap } from 'lucide-react';

interface SearchResult {
    score: number;
    event: any;
    narrative: string;
}

export default function RiskWarRoom() {
    const { context } = useFDC3();
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [liveAlert, setLiveAlert] = useState<any>(null);

    // 1. FDC3 LISTENER (The "War Room" reacts to the "Front Line")
    useEffect(() => {
        if (context && context.type === 'finos.cdm.landUse') {
            const landUseCtx = context as any; // Cast for simplicity in demo
            setLiveAlert(landUseCtx);
            // Auto-trigger impactful search on breach
            if (landUseCtx.complianceStatus === 'BREACH') {
                const autoQuery = "Find all trades with forestry covenant breaches or low NDVI scores";
                setQuery(autoQuery);
                performSearch(autoQuery);
            }
        }
    }, [context]);

    const performSearch = async (searchQuery: string) => {
        if (!searchQuery) return;
        setIsSearching(true);
        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(searchQuery)}`);
            const data = await res.json();
            setResults(data);
        } catch (e) {
            console.error("Search failed", e);
        } finally {
            setIsSearching(false);
        }
    };

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        performSearch(query);
    };

    return (
        <div className="h-full flex flex-col bg-black text-white p-6 overflow-hidden relative">

            {/* Background Ambience */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-indigo-900/20 via-black to-black pointer-events-none"></div>

            {/* Header */}
            <div className="flex justify-between items-center mb-8 relative z-10">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-orange-500">
                        RISK WAR ROOM
                    </h1>
                    <p className="text-zinc-500 text-sm font-mono mt-1">GLOBAL PORTFOLIO SURVEILLANCE</p>
                </div>

                {/* Live Feed Status */}
                <div className="flex items-center gap-3 bg-zinc-900 border border-zinc-800 px-4 py-2 rounded-full">
                    <RadioTower className={`w-4 h-4 ${liveAlert ? 'text-red-500 animate-pulse' : 'text-zinc-600'}`} />
                    <span className="text-xs font-mono text-zinc-400">
                        {liveAlert ? 'INCOMING SIGNAL DETECTED' : 'LISTENING FOR FDC3 SIGNALS...'}
                    </span>
                </div>
            </div>

            {/* Live Alert Banner (FDC3 triggered) */}
            {liveAlert && (
                <div className="mb-8 animate-in slide-in-from-top duration-500">
                    <Card className="bg-red-500/10 border-red-500/50 p-4 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="p-2 bg-red-500/20 rounded-full animate-pulse">
                                <AlertTriangle className="w-6 h-6 text-red-500" />
                            </div>
                            <div>
                                <h3 className="font-bold text-white">Security Alert: {liveAlert.id?.internalID || 'Unknown Asset'}</h3>
                                <p className="text-red-300 text-sm">
                                    Breach Detected by Sentinel-2. Yield Adjusted.
                                </p>
                            </div>
                        </div>
                        <div className="text-right">
                            <div className="text-2xl font-mono font-bold text-white">{liveAlert.lastInferenceConfidence ? (liveAlert.lastInferenceConfidence * 100).toFixed(1) : '99.9'}%</div>
                            <div className="text-[10px] text-red-400 uppercase tracking-wider">Confidence</div>
                        </div>
                    </Card>
                </div>
            )}

            {/* Semantic Search Bar */}
            <div className="relative z-10 mb-8 max-w-2xl mx-auto w-full">
                <form onSubmit={handleSearch} className="relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg blur opacity-30 group-hover:opacity-100 transition duration-1000 group-hover:duration-200"></div>
                    <div className="relative flex">
                        <Input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Ask the portfolio: 'Find loans with deforestation risk'..."
                            className="bg-zinc-900 border-zinc-800 text-white placeholder:text-zinc-600 h-14 pl-12 pr-4 text-lg rounded-l-lg focus:ring-0 focus:border-indigo-500 transition-all w-full"
                        />
                        <Button
                            type="submit"
                            disabled={isSearching}
                            className="h-14 px-8 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-r-lg"
                        >
                            {isSearching ? <Zap className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
                        </Button>
                        <Search className="w-5 h-5 text-zinc-500 absolute left-4 top-4.5" />
                    </div>
                </form>
            </div>

            {/* Results Grid */}
            <div className="flex-1 overflow-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 relative z-10 pb-20">
                {results.map((res, idx) => (
                    <Card key={idx} className="bg-zinc-900/50 border-zinc-800 p-6 hover:bg-zinc-900 hover:border-indigo-500/50 transition-all cursor-pointer group">
                        <div className="flex justify-between items-start mb-4">
                            <div className="bg-indigo-500/10 text-indigo-400 text-xs px-2 py-1 rounded font-mono">
                                SCORE: {(res.score * 100).toFixed(0)}%
                            </div>
                            {res.event.eventType === 'TermsChange' ? (
                                <TrendingUp className="w-5 h-5 text-yellow-500" />
                            ) : (
                                <ShieldCheck className="w-5 h-5 text-zinc-600 group-hover:text-indigo-500" />
                            )}
                        </div>

                        <p className="text-sm text-zinc-300 font-light leading-relaxed mb-4">
                            "{res.narrative}"
                        </p>

                        <div className="pt-4 border-t border-zinc-800 flex justify-between items-center text-xs text-zinc-500 font-mono">
                            <span>ID: {res.event.meta?.globalKey?.substring(0, 8) || 'Unknown'}</span>
                            <span>{res.event.eventType}</span>
                        </div>
                    </Card>
                ))}

                {results.length === 0 && !isSearching && (
                    <div className="col-span-full flex flex-col items-center justify-center text-zinc-700 mt-20">
                        <RadioTower className="w-16 h-16 mb-4 opacity-20" />
                        <p className="font-mono text-sm">SECURE CHANNEL ACTIVE. NO SIGNALS.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
