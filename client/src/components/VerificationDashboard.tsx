import { useState, useEffect } from 'react';
import { useFDC3 } from '@/context/FDC3Context';
import { fetchWithAuth } from '@/context/AuthContext';
import { DropZone } from './DropZone';
import { AgentTerminal } from './AgentTerminal';
import { MapView } from './MapView';
import { Button } from './ui/button';
import { ShieldCheck, Activity, Code, Map as MapIcon, Globe } from 'lucide-react';
import { Card } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

// Mock asset for demo visualization (Napa Valley) - Aligned with LoanAsset interface
const DEMO_ASSET = {
    id: 9999, // Must be a number for MapView
    loan_id: 'DEMO-KILLSHOT-001',
    collateral_address: '1 Main St, Napa, CA',
    geo_lat: 38.2975, // Napa
    geo_lon: -122.2869,
    risk_status: 'BREACH',
    last_verified_score: 0.65,
    spt_threshold: 0.75,
    current_interest_rate: 5.25
};

interface LogEntry {
    timestamp: string;
    level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS';
    message: string;
}

export default function VerificationDashboard() {
    const { broadcast, context } = useFDC3();
    const [file, setFile] = useState<File | null>(null);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isVerified, setIsVerified] = useState(false);
    const [cdmEvents, setCdmEvents] = useState<any>(null);
    const [classification, setClassification] = useState<any>(null);

    const [extractedText, setExtractedText] = useState<string>('');

    const addLog = (message: string, level: LogEntry['level'] = 'INFO') => {
        setLogs(prev => [...prev, {
            timestamp: new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            level,
            message
        }]);
    };

    useEffect(() => {
        if (context?.type === 'fdc3.creditnexus.loan' && context.loan?.document_text) {
            const loan = context.loan;
            setExtractedText(loan.document_text || '');
            setLogs([]); // Clear previous logs
            addLog("Received Loan Context from Peer Application (FDC3).", 'INFO');

            const borrower = loan.parties?.find(p => p.role.toLowerCase().includes('borrower'))?.name;
            if (borrower) {
                addLog(`Target Borrower Identified: ${borrower}`, 'SUCCESS');
            }

            if (loan.facilities && loan.facilities.length > 0) {
                const total = loan.facilities.reduce((sum, f) => sum + (f.commitment_amount?.amount || 0), 0);
                addLog(`Facility Amount: ${loan.facilities[0].commitment_amount?.currency} ${total.toLocaleString()}`, 'INFO');
            }

            addLog("Verification Protocol Prepared. Ready for Securitization.", 'WARN');
        }
    }, [context]);

    const handleFileSelect = async (uploadedFile: File) => {
        setFile(uploadedFile);
        setIsAnalyzing(true);
        setLogs([]);

        addLog(`Received file: ${uploadedFile.name} (${(uploadedFile.size / 1024 / 1024).toFixed(2)} MB)`);
        addLog("Uploading to Secure Vault & Extracting Data...", 'INFO');

        try {
            const formData = new FormData();
            formData.append('file', uploadedFile);

            const response = await fetchWithAuth('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Upload failed');

            const data = await response.json();
            setExtractedText(data.extracted_text);

            addLog("Extraction Complete. Agreement Text Parsed.", 'SUCCESS');
            if (data.agreement?.borrower_name) {
                addLog(`Identified Borrower: ${data.agreement.borrower_name}`, 'SUCCESS');
            }
            if (data.agreement?.sustainability_linked) {
                addLog("Sustainability-Linked Clause Detected.", 'WARN');
            }
            addLog("Legal Agent (OpenAI GPT-4) ready for compliance scan.", 'INFO');
            setIsAnalyzing(false);

        } catch (error) {
            addLog(`Error during upload/extraction: ${error}`, 'ERROR');
            setIsAnalyzing(false);
        }
    };

    const handleSecuritize = async () => {
        setIsAnalyzing(true);
        addLog("Initiating Ground Truth Verification Protocol...", 'WARN');

        try {
            // 1. Trigger Full Audit Workflow
            addLog("Vectorizing Legal Requirements...", 'INFO');

            const response = await fetchWithAuth('/api/loan-assets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    loan_id: 'LOAN-2024-KILLSHOT',
                    title: 'Napa Valley Vineyards Facility A',
                    document_text: extractedText
                })
            });

            const data = await response.json();

            if (!response.ok) throw new Error(data.detail?.message || 'Verification failed');

            const { loan_asset, audit } = data;
            const stages = audit.stages_completed;

            if (stages.includes('legal_analysis')) addLog("Legal Analysis: SPT & Collateral Extracted", 'SUCCESS');
            if (stages.includes('geocoding')) addLog(`Geocoded: ${loan_asset.collateral_address}`, 'SUCCESS');

            addLog("Requesting Sentinel-2 Satellite Imagery...", 'INFO');

            if (stages.includes('satellite_verification')) {
                addLog("TorchGeo Classifier: Analysis Complete", 'SUCCESS');

                // Update UI state with REAL data
                setClassification({
                    classification: loan_asset.risk_status === 'BREACH' ? 'AnnualCrop' : 'Forest', // Simplification for UI demo based on status
                    confidence: 0.94, // Hardcoded for demo consistency or could be added to API response
                    ndvi: loan_asset.last_verified_score
                });

                addLog(`NDVI Result: ${loan_asset.last_verified_score?.toFixed(2)} (Target: > ${loan_asset.spt_threshold})`,
                    loan_asset.risk_status === 'BREACH' ? 'ERROR' : 'SUCCESS');

                if (loan_asset.risk_status === 'BREACH') {
                    addLog(" Compliance Report: COVENANT BREACH VERIFIED", 'ERROR');
                } else {
                    addLog("Compliance Report: ASSET VERIFIED", 'SUCCESS');
                }
            }

            // 2. CDM Event Generation (Mock for visualization, triggered by success)
            addLog("Generating FINOS CDM 'Observation' Event...", 'INFO');
            setTimeout(async () => {
                // We'll keep this mock or connect to real event endpoint if time permits, 
                // but for now the audit workflow is the key.
                const cdmRes = await fetch('/api/cdm/events/LOAN-2024-KILLSHOT');
                const cdmData = await cdmRes.json();
                setCdmEvents(cdmData);

                if (loan_asset.risk_status === 'BREACH') {
                    addLog("CDM Ledger Updated: Spread +25bps Triggered", 'ERROR');
                }

                setIsVerified(true);
                setIsAnalyzing(false);

                // 3. FDC3 Broadcast with REAL data
                broadcast({
                    type: 'finos.cdm.landUse',
                    id: { internalID: loan_asset.loan_id },
                    classification: 'AnnualCrop',
                    complianceStatus: loan_asset.risk_status,
                    lastInferenceConfidence: 0.9423,
                    cloudCover: 0.05
                });
                addLog(`FDC3 Context Broadcast: 'finos.cdm.landUse' -> [network]`, 'INFO');

            }, 1000);

        } catch (error) {
            addLog(`Verification failed: ${error}`, 'ERROR');
            setIsAnalyzing(false);
        }
    };

    return (
        <div className="h-full bg-black text-white p-6 grid grid-cols-12 gap-6 overflow-hidden rounded-xl border border-zinc-800 shadow-2xl">

            {/* LEFT COLUMN: Input & Legal & Code */}
            <div className="col-span-5 flex flex-col gap-6 h-full">

                {/* Header */}
                <div>
                    <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
                        CreditNexus <span className="text-zinc-500 font-mono text-sm ml-2">v2.0.4-KILLSHOT</span>
                    </h1>
                    <p className="text-zinc-500 text-sm">Algorithmic Nature-Finance Platform</p>
                </div>

                {/* Drop Zone (Hero) */}
                {!isVerified ? (
                    <div className={isVerified ? 'hidden' : 'block animate-in fade-in zoom-in duration-500'}>
                        <DropZone onFileSelect={handleFileSelect} isProcessing={isAnalyzing} />
                    </div>
                ) : (
                    // Result Card (Replaces DropZone)
                    <Card className="bg-zinc-900 border-red-500/30 p-4 animate-in slide-in-from-top duration-700">
                        <div className="flex items-center gap-4 mb-4">
                            <div className="p-3 rounded-full bg-red-500/10">
                                <ShieldCheck className="w-8 h-8 text-red-500" />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-white">Covenant Breached</h3>
                                <p className="text-red-400 text-sm">Risk Detected: Vegetation Below Threshold</p>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div className="bg-black/50 p-2 rounded">
                                <span className="text-zinc-500 block">Classified As</span>
                                <span className={`font-mono font-bold ${classification?.classification === 'AnnualCrop' ? 'text-yellow-400' : 'text-green-400'}`}>
                                    {classification?.classification || 'Unknown'}
                                </span>
                            </div>
                            <div className="bg-black/50 p-2 rounded">
                                <span className="text-zinc-500 block">NDVI Score</span>
                                <span className={`font-mono font-bold ${classification?.ndvi < 0.75 ? 'text-red-500' : 'text-green-500'}`}>
                                    {classification?.ndvi?.toFixed(2) || 'N/A'}
                                </span>
                            </div>
                        </div>
                    </Card>
                )}

                {/* Agent Terminal (The "Thinking" Brain) */}
                <div className="flex-1 min-h-[300px]">
                    <AgentTerminal logs={logs} thinking={isAnalyzing} />
                </div>

                {/* Primary Action Button */}
                {(file || extractedText) && !isVerified && (
                    <Button
                        size="lg"
                        onClick={handleSecuritize}
                        disabled={isAnalyzing}
                        className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-6 text-lg tracking-wide shadow-lg shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isAnalyzing ? (
                            <>
                                <Activity className="w-5 h-5 mr-2 animate-spin" />
                                PROCESSING ASSET...
                            </>
                        ) : (
                            <>
                                <ShieldCheck className="w-5 h-5 mr-2" />
                                SECURITIZE & VERIFY
                            </>
                        )}
                    </Button>
                )}
            </div>

            {/* RIGHT COLUMN: Map & JSON (Split View) */}
            <div className="col-span-7 h-full bg-zinc-900/50 rounded-2xl border border-zinc-800 overflow-hidden relative">

                {/* Visualizer Tabs */}
                {isVerified ? (
                    <Tabs defaultValue="map" className="h-full flex flex-col">
                        <div className="absolute top-4 right-4 z-10 bg-black/80 backdrop-blur rounded p-1 border border-zinc-700">
                            <TabsList className="bg-transparent h-8">
                                <TabsTrigger value="map" className="data-[state=active]:bg-zinc-800 text-xs px-3 py-1"><MapIcon className="w-3 h-3 mr-1" /> Geospatial</TabsTrigger>
                                <TabsTrigger value="cdm" className="data-[state=active]:bg-zinc-800 text-xs px-3 py-1"><Code className="w-3 h-3 mr-1" /> CDM JSON</TabsTrigger>
                            </TabsList>
                        </div>

                        <TabsContent value="map" className="flex-1 m-0 h-full p-0">
                            <div className="w-full h-full relative">
                                <MapView assets={[DEMO_ASSET]} showSatellite={true} />

                                {/* Overlay Stats */}
                                <div className="absolute bottom-6 left-6 z-[1000] bg-black/80 backdrop-blur px-4 py-2 rounded border border-red-500/50">
                                    <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Satellite Intelligence</div>
                                    <div className="flex items-center gap-2">
                                        <Globe className="w-4 h-4 text-indigo-400" />
                                        <span className="font-mono text-white text-sm">Sentinel-2B L2A</span>
                                    </div>
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="cdm" className="flex-1 m-0 h-full overflow-hidden">
                            <div className="h-full bg-[#1e1e1e] p-6 overflow-auto font-mono text-xs text-blue-300">
                                <pre>{JSON.stringify(cdmEvents, null, 2)}</pre>
                            </div>
                        </TabsContent>
                    </Tabs>
                ) : (
                    // Placeholder State
                    <div className="h-full flex flex-col items-center justify-center text-zinc-600">
                        <div className="relative">
                            <div className="absolute inset-0 bg-indigo-500/20 blur-3xl rounded-full"></div>
                            <Globe className="w-32 h-32 relative z-10 opacity-50" />
                        </div>
                        <p className="mt-8 text-lg font-light tracking-widest">AWAITING ASSET UPLOAD</p>
                        <p className="text-sm mt-2 opacity-50">Global Satellite Network Standby</p>

                        <div className="mt-12 grid grid-cols-3 gap-8 text-center opacity-30">
                            <div><div className="font-mono text-2xl font-bold">13</div><div className="text-[10px]">SPECTRAL BANDS</div></div>
                            <div><div className="font-mono text-2xl font-bold">5d</div><div className="text-[10px]">REVISIT RATE</div></div>
                            <div><div className="font-mono text-2xl font-bold">10m</div><div className="text-[10px]">RESOLUTION</div></div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
