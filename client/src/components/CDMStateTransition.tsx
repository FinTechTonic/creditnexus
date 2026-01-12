import { useState, useEffect } from 'react';
import { FileCode2, ArrowRight, Clock, CheckCircle2, AlertCircle } from 'lucide-react';

interface SpreadSchedule {
    initialValue: number;
    type: string;
    effectiveDate?: string | null;
    step?: {
        triggerEvent: string;
        adjustmentBps: number;
        evidence?: {
            source: string;
            metric: string;
            verified: boolean;
        };
    } | null;
}

interface CDMState {
    spreadSchedule: SpreadSchedule;
}

interface CDMDiff {
    field: string;
    oldValue: number;
    newValue: number;
    changeType: string;
    trigger: string;
}

interface CDMTransitionData {
    before: CDMState;
    after: CDMState;
    diff: CDMDiff;
}

interface CDMStateTransitionProps {
    transitionData: CDMTransitionData | null;
    isLoading?: boolean;
    onTransitionComplete?: () => void;
}

export function CDMStateTransition({
    transitionData,
    isLoading = false,
    onTransitionComplete
}: CDMStateTransitionProps) {
    const [showAfter, setShowAfter] = useState(false);
    const [animating, setAnimating] = useState(false);

    // Animate transition when data changes
    useEffect(() => {
        if (transitionData && !isLoading) {
            setAnimating(true);
            setShowAfter(false);

            // Animate the transition
            const timer = setTimeout(() => {
                setShowAfter(true);
                setAnimating(false);
                onTransitionComplete?.();
            }, 1500);

            return () => clearTimeout(timer);
        }
    }, [transitionData, isLoading, onTransitionComplete]);

    if (isLoading) {
        return (
            <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 animate-pulse">
                <div className="h-4 bg-zinc-700 rounded w-1/3 mb-4"></div>
                <div className="h-32 bg-zinc-800 rounded"></div>
            </div>
        );
    }

    if (!transitionData) {
        return (
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 text-center">
                <FileCode2 className="w-8 h-8 text-zinc-600 mx-auto mb-2" />
                <p className="text-zinc-500 text-sm">CDM state transitions will appear after verification</p>
            </div>
        );
    }

    const formatValue = (value: number) => `${(value * 100).toFixed(2)}%`;

    const renderJsonWithHighlight = (state: CDMState, isAfter: boolean) => {
        const schedule = state.spreadSchedule;
        const valueChanged = isAfter && transitionData.diff.changeType === 'INCREASE';

        return (
            <pre className="text-xs font-mono leading-relaxed">
                <span className="text-zinc-500">{'{'}</span>{'\n'}
                <span className="text-purple-400 ml-4">"spreadSchedule"</span>
                <span className="text-zinc-500">: {'{'}</span>{'\n'}

                <span className="text-purple-400 ml-8">"initialValue"</span>
                <span className="text-zinc-500">: </span>
                <span className={`${valueChanged ? 'bg-red-500/30 text-red-300 px-1 rounded animate-pulse' : 'text-cyan-400'}`}>
                    {schedule.initialValue}
                </span>
                <span className="text-zinc-500">,</span>
                {valueChanged && (
                    <span className="text-red-400 ml-2 text-[10px]">
            // {formatValue(schedule.initialValue)} {transitionData.diff.changeType === 'INCREASE' ? '↑' : '↓'}
                    </span>
                )}
                {'\n'}

                <span className="text-purple-400 ml-8">"type"</span>
                <span className="text-zinc-500">: </span>
                <span className="text-green-400">"{schedule.type}"</span>
                {isAfter && schedule.effectiveDate && (
                    <>
                        <span className="text-zinc-500">,</span>{'\n'}
                        <span className="text-purple-400 ml-8">"effectiveDate"</span>
                        <span className="text-zinc-500">: </span>
                        <span className="text-yellow-400 bg-yellow-500/10 px-1 rounded">"{schedule.effectiveDate}"</span>
                    </>
                )}
                {isAfter && schedule.step && (
                    <>
                        <span className="text-zinc-500">,</span>{'\n'}
                        <span className="text-purple-400 ml-8">"step"</span>
                        <span className="text-zinc-500">: {'{'}</span>{'\n'}
                        <span className="text-purple-400 ml-12">"triggerEvent"</span>
                        <span className="text-zinc-500">: </span>
                        <span className="text-red-400 bg-red-500/10 px-1 rounded">"{schedule.step.triggerEvent}"</span>
                        <span className="text-zinc-500">,</span>{'\n'}
                        <span className="text-purple-400 ml-12">"adjustmentBps"</span>
                        <span className="text-zinc-500">: </span>
                        <span className="text-red-400 font-bold">{schedule.step.adjustmentBps}</span>
                        {schedule.step.evidence && (
                            <>
                                <span className="text-zinc-500">,</span>{'\n'}
                                <span className="text-purple-400 ml-12">"evidence"</span>
                                <span className="text-zinc-500">: {'{'}</span>{'\n'}
                                <span className="text-purple-400 ml-16">"source"</span>
                                <span className="text-zinc-500">: </span>
                                <span className="text-blue-400">"{schedule.step.evidence.source}"</span>
                                <span className="text-zinc-500">,</span>{'\n'}
                                <span className="text-purple-400 ml-16">"metric"</span>
                                <span className="text-zinc-500">: </span>
                                <span className="text-blue-400">"{schedule.step.evidence.metric}"</span>
                                <span className="text-zinc-500">,</span>{'\n'}
                                <span className="text-purple-400 ml-16">"verified"</span>
                                <span className="text-zinc-500">: </span>
                                <span className="text-green-400">{schedule.step.evidence.verified.toString()}</span>{'\n'}
                                <span className="text-zinc-500 ml-12">{'}'}</span>
                            </>
                        )}
                        {'\n'}
                        <span className="text-zinc-500 ml-8">{'}'}</span>
                    </>
                )}
                {'\n'}
                <span className="text-zinc-500 ml-4">{'}'}</span>{'\n'}
                <span className="text-zinc-500">{'}'}</span>
            </pre>
        );
    };

    return (
        <div className="bg-gradient-to-br from-zinc-900 to-slate-900 border border-zinc-700 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 border-b border-zinc-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <FileCode2 className="w-4 h-4 text-indigo-400" />
                    <h3 className="text-sm font-semibold text-white">CDM Smart Contract State</h3>
                </div>
                <div className="flex items-center gap-2">
                    <Clock className="w-3 h-3 text-zinc-500" />
                    <span className="text-xs text-zinc-500 font-mono">FINOS CDM v3.0</span>
                </div>
            </div>

            {/* Transition Cards */}
            <div className="p-4">
                <div className="grid grid-cols-2 gap-4">
                    {/* BEFORE State */}
                    <div className={`relative ${animating && !showAfter ? 'opacity-100' : showAfter ? 'opacity-50' : 'opacity-100'} transition-opacity duration-500`}>
                        <div className="flex items-center gap-2 mb-2">
                            <CheckCircle2 className="w-4 h-4 text-green-400" />
                            <span className="text-xs font-bold text-green-400 uppercase tracking-wider">State A: Compliant</span>
                        </div>
                        <div className="bg-black/50 rounded-lg border border-zinc-700 p-3 overflow-auto max-h-48">
                            {renderJsonWithHighlight(transitionData.before, false)}
                        </div>
                    </div>

                    {/* Arrow & Animation */}
                    <div className={`absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10 ${animating ? 'scale-125' : 'scale-100'} transition-transform duration-300`}>
                        {/* This is positioned between the two cards */}
                    </div>

                    {/* AFTER State */}
                    <div className={`relative ${showAfter ? 'opacity-100' : 'opacity-30'} transition-opacity duration-500`}>
                        <div className="flex items-center gap-2 mb-2">
                            <AlertCircle className="w-4 h-4 text-red-400" />
                            <span className="text-xs font-bold text-red-400 uppercase tracking-wider">State B: Breach</span>
                        </div>
                        <div className={`bg-black/50 rounded-lg border p-3 overflow-auto max-h-48 ${showAfter ? 'border-red-500/50' : 'border-zinc-700'} transition-colors duration-500`}>
                            {renderJsonWithHighlight(transitionData.after, true)}
                        </div>
                    </div>
                </div>

                {/* Transition Arrow */}
                <div className="flex items-center justify-center my-4">
                    <div className={`flex items-center gap-2 ${animating ? 'animate-pulse' : ''}`}>
                        <div className="h-px w-16 bg-gradient-to-r from-green-500 to-zinc-500"></div>
                        <ArrowRight className={`w-6 h-6 ${showAfter ? 'text-red-400' : 'text-zinc-500'} transition-colors duration-500`} />
                        <div className="h-px w-16 bg-gradient-to-r from-zinc-500 to-red-500"></div>
                    </div>
                </div>

                {/* Diff Summary */}
                {showAfter && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 animate-in fade-in slide-in-from-bottom duration-500">
                        <div className="flex items-center gap-2 mb-2">
                            <AlertCircle className="w-4 h-4 text-red-400" />
                            <span className="text-xs font-bold text-red-400">TERMS CHANGE EVENT</span>
                        </div>
                        <div className="grid grid-cols-3 gap-4 text-xs">
                            <div>
                                <span className="text-zinc-500 block">Field</span>
                                <span className="text-white font-mono">{transitionData.diff.field}</span>
                            </div>
                            <div>
                                <span className="text-zinc-500 block">Change</span>
                                <span className="text-red-400 font-mono font-bold">
                                    {formatValue(transitionData.diff.oldValue)} → {formatValue(transitionData.diff.newValue)}
                                </span>
                            </div>
                            <div>
                                <span className="text-zinc-500 block">Trigger</span>
                                <span className="text-amber-400 font-mono">{transitionData.diff.trigger}</span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default CDMStateTransition;
