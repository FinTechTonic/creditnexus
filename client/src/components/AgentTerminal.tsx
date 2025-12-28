import { useEffect, useRef } from 'react';

interface LogEntry {
    timestamp: string;
    level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS';
    message: string;
}

interface AgentTerminalProps {
    logs: LogEntry[];
    thinking?: boolean;
}

export function AgentTerminal({ logs, thinking = false }: AgentTerminalProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    return (
        <div className="w-full h-full bg-black border border-zinc-800 rounded-lg overflow-hidden flex flex-col font-mono text-xs shadow-2xl">
            {/* Terminal Bar */}
            <div className="bg-zinc-900 px-4 py-2 flex items-center gap-2 border-b border-zinc-800">
                <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
                </div>
                <span className="text-zinc-500 ml-2">agent_executor.exe — TorchGeo</span>
            </div>

            {/* Logs Area */}
            <div className="flex-1 p-4 bg-black/95 text-green-500/90 font-mono overflow-auto">
                <div className="flex flex-col gap-1">
                    {logs.map((log, i) => (
                        <div key={i} className="flex gap-3 animate-in fade-in slide-in-from-left-2 duration-300">
                            <span className="text-zinc-600 shrink-0">[{log.timestamp}]</span>
                            <span className={
                                log.level === 'ERROR' ? 'text-red-500' :
                                    log.level === 'WARN' ? 'text-yellow-500' :
                                        log.level === 'SUCCESS' ? 'text-neon-cyan font-bold' :
                                            'text-green-500'
                            }>
                                {log.level === 'SUCCESS' ? '✅ ' : log.level === 'ERROR' ? '❌ ' : '> '}
                                {log.message}
                            </span>
                        </div>
                    ))}

                    {thinking && (
                        <div className="flex gap-3 mt-2 animate-pulse">
                            <span className="text-zinc-600">[{new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>
                            <span className="text-green-500">_</span>
                        </div>
                    )}
                    <div ref={bottomRef} />
                </div>
            </div>
        </div>
    );
}
