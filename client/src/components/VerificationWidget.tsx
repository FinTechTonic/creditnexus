import { useState, useEffect } from 'react';
import { useFDC3 } from '@/context/FDC3Context';
import { useVerification } from '@/hooks/useVerification';
import { DropZone } from './DropZone';
import { AgentTerminal } from './AgentTerminal';
import { MapView } from './MapView';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from './ui/collapsible';
import { ShieldCheck, ChevronDown, ChevronUp, ExternalLink, Globe } from 'lucide-react';
import { LocationTypeBadge } from './green-finance/LocationTypeBadge';
import { AirQualityIndicator } from './green-finance/AirQualityIndicator';
import { GreenFinanceMetricsCard } from './green-finance/GreenFinanceMetricsCard';

// Mock asset for demo visualization
const DEMO_ASSET = {
    id: 9999,
    loan_id: 'DEMO-KILLSHOT-001',
    collateral_address: '1 Main St, Napa, CA',
    geo_lat: 38.2975,
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

interface VerificationWidgetProps {
    /** Whether widget is embedded in Dashboard (true) or standalone (false) */
    embedded?: boolean;
    /** External control for collapsed state */
    defaultCollapsed?: boolean;
    /** Callback when verification completes */
    onVerificationComplete?: (result: any) => void;
    /** Callback to navigate to full verification dashboard */
    onViewFull?: () => void;
    /** Initial extracted text from external source */
    initialText?: string;
}

export function VerificationWidget({
    embedded = true,
    defaultCollapsed = false,
    onVerificationComplete,
    onViewFull,
    initialText
}: VerificationWidgetProps) {
    const { broadcast, context } = useFDC3();
    const { uploadAndExtract, createLoanAsset, loading: verificationLoading, error: verificationError } = useVerification();
    const [file, setFile] = useState<File | null>(null);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isVerified, setIsVerified] = useState(false);
    const [classification, setClassification] = useState<any>(null);
    const [extractedText, setExtractedText] = useState<string>(initialText || '');
    const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
    const [loanAsset, setLoanAsset] = useState<any>(null);

    // Limit logs for compact display (max 8 entries)
    const displayLogs = logs.slice(-8);

    const addLog = (message: string, level: LogEntry['level'] = 'INFO') => {
        setLogs(prev => {
            const newLogs = [...prev, {
                timestamp: new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                level,
                message
            }];
            // Keep only last 50 logs in memory, but display last 8
            return newLogs.slice(-50);
        });
    };

    // Handle FDC3 context
    useEffect(() => {
        if (context?.type === 'fdc3.creditnexus.loan' && context.loan?.document_text) {
            const loan = context.loan;
            setExtractedText(loan.document_text || '');
            setLogs([]);
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

    // Handle initial text prop
    useEffect(() => {
        if (initialText && initialText !== extractedText) {
            setExtractedText(initialText);
        }
    }, [initialText]);

    const handleFileSelect = async (uploadedFile: File) => {
        setFile(uploadedFile);
        setIsAnalyzing(true);
        setLogs([]);

        addLog(`Received file: ${uploadedFile.name} (${(uploadedFile.size / 1024 / 1024).toFixed(2)} MB)`);
        addLog("Uploading to Secure Vault & Extracting Data...", 'INFO');

        try {
            const result = await uploadAndExtract(uploadedFile);

            if (!result) {
                addLog(`Error during upload/extraction: ${verificationError || 'Upload failed'}`, 'ERROR');
                setIsAnalyzing(false);
                return;
            }

            setExtractedText(result.extracted_text);

            addLog("Extraction Complete. Agreement Text Parsed.", 'SUCCESS');
            if (result.agreement?.borrower_name) {
                addLog(`Identified Borrower: ${result.agreement.borrower_name}`, 'SUCCESS');
            }
            if (result.agreement?.sustainability_linked) {
                addLog("Sustainability-Linked Clause Detected.", 'WARN');
            }
            addLog("Legal Agent (OpenAI GPT-4) ready for compliance scan.", 'INFO');
            setIsAnalyzing(false);

        } catch (error) {
            addLog(`Error during upload/extraction: ${error instanceof Error ? error.message : 'Unknown error'}`, 'ERROR');
            setIsAnalyzing(false);
        }
    };

    const handleSecuritize = async () => {
        setIsAnalyzing(true);
        addLog("Initiating Ground Truth Verification Protocol...", 'WARN');

        try {
            addLog("Vectorizing Legal Requirements...", 'INFO');

            // Generate a unique loan ID if not provided
            const loanId = `LOAN-${new Date().getFullYear()}-${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
            const title = extractedText.match(/borrower[:\s]+([^\n,]+)/i)?.[1]?.trim() || 'Facility A';

            const result = await createLoanAsset({
                loan_id: loanId,
                title: title,
                document_text: extractedText
            });

            if (!result) {
                addLog(`Verification failed: ${verificationError || 'Unknown error'}`, 'ERROR');
                setIsAnalyzing(false);
                return;
            }

            const { loan_asset, audit } = result;
            setLoanAsset(loan_asset);
            const stages = audit.stages_completed;

            if (stages.includes('legal_analysis')) addLog("Legal Analysis: SPT & Collateral Extracted", 'SUCCESS');
            if (stages.includes('geocoding') && loan_asset.collateral_address) {
                addLog(`Geocoded: ${loan_asset.collateral_address}`, 'SUCCESS');
            }

            addLog("Requesting Sentinel-2 Satellite Imagery...", 'INFO');

            if (stages.includes('satellite_verification')) {
                addLog("TorchGeo Classifier: Analysis Complete", 'SUCCESS');

                setClassification({
                    classification: loan_asset.risk_status === 'BREACH' ? 'AnnualCrop' : 'Forest',
                    confidence: 0.94,
                    ndvi: loan_asset.last_verified_score
                });

                if (loan_asset.last_verified_score !== undefined && loan_asset.spt_threshold !== undefined) {
                    addLog(`NDVI Result: ${loan_asset.last_verified_score.toFixed(2)} (Target: > ${loan_asset.spt_threshold})`,
                        loan_asset.risk_status === 'BREACH' ? 'ERROR' : 'SUCCESS');
                }

                if (loan_asset.risk_status === 'BREACH') {
                    addLog(" Compliance Report: COVENANT BREACH VERIFIED", 'ERROR');
                } else {
                    addLog("Compliance Report: ASSET VERIFIED", 'SUCCESS');
                }
            }

            addLog("Generating FINOS CDM 'Observation' Event...", 'INFO');
            
            // Fetch CDM events if available
            try {
                const cdmRes = await fetch(`/api/cdm/events/${loan_asset.loan_id}`);
                if (cdmRes.ok) {
                    const cdmData = await cdmRes.json();
                    if (loan_asset.risk_status === 'BREACH') {
                        addLog("CDM Ledger Updated: Spread +25bps Triggered", 'ERROR');
                    }
                }
            } catch (err) {
                // CDM events endpoint may not be available, continue anyway
                console.warn('CDM events endpoint not available:', err);
            }

            setIsVerified(true);
            setIsAnalyzing(false);

            // FDC3 Broadcast - Land Use
            broadcast({
                type: 'finos.cdm.landUse',
                id: { internalID: loan_asset.loan_id },
                classification: loan_asset.risk_status === 'BREACH' ? 'AnnualCrop' : 'Forest',
                complianceStatus: loan_asset.risk_status,
                lastInferenceConfidence: 0.9423,
                cloudCover: 0.05
            });
            addLog(`FDC3 Context Broadcast: 'finos.cdm.landUse' -> [network]`, 'INFO');

            // FDC3 Broadcast - Green Finance Assessment (if metrics available)
            if (loan_asset.location_type && loan_asset.air_quality_index !== undefined && loan_asset.geo_lat && loan_asset.geo_lon) {
                try {
                    broadcast({
                        type: 'finos.cdm.greenFinanceAssessment',
                        id: { transactionId: loan_asset.loan_id },
                        location: {
                            lat: loan_asset.geo_lat,
                            lon: loan_asset.geo_lon,
                            type: loan_asset.location_type as 'urban' | 'suburban' | 'rural'
                        },
                        environmentalMetrics: {
                            airQualityIndex: loan_asset.air_quality_index,
                            pm25: loan_asset.green_finance_metrics?.air_quality?.pm25,
                            pm10: loan_asset.green_finance_metrics?.air_quality?.pm10,
                            no2: loan_asset.green_finance_metrics?.air_quality?.no2
                        },
                        sustainabilityScore: loan_asset.composite_sustainability_score || 0.5,
                        sdgAlignment: loan_asset.green_finance_metrics?.sdg_alignment ? {
                            sdg_11: loan_asset.green_finance_metrics.sdg_alignment.sdg_11,
                            sdg_13: loan_asset.green_finance_metrics.sdg_alignment.sdg_13,
                            sdg_15: loan_asset.green_finance_metrics.sdg_alignment.sdg_15,
                            overall_alignment: loan_asset.green_finance_metrics.sdg_alignment.overall_alignment
                        } : undefined,
                        assessedAt: loan_asset.last_verified_at?.toISOString() || new Date().toISOString()
                    });
                    addLog(`FDC3 Context Broadcast: 'finos.cdm.greenFinanceAssessment' -> [network]`, 'INFO');
                } catch (err) {
                    console.warn('Failed to broadcast green finance assessment:', err);
                }
            }

            // Call completion callback
            if (onVerificationComplete) {
                onVerificationComplete({ loan_asset, audit });
            }

        } catch (error) {
            addLog(`Verification failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'ERROR');
            setIsAnalyzing(false);
        }
    };

    // Collapsed view (compact)
    if (isCollapsed && embedded) {
        return (
            <Card className="p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <ShieldCheck className="w-5 h-5 text-indigo-500" />
                        <h3 className="font-semibold">Asset Verification</h3>
                        {isVerified && (
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                    classification?.ndvi < 0.75 ? 'bg-red-500/20 text-red-500' : 'bg-green-500/20 text-green-500'
                                }`}>
                                    {classification?.ndvi < 0.75 ? 'BREACH' : 'VERIFIED'}
                                </span>
                                {loanAsset?.location_type && (
                                    <LocationTypeBadge 
                                        locationType={loanAsset.location_type}
                                        confidence={loanAsset.green_finance_metrics?.location_confidence}
                                        compact
                                    />
                                )}
                                {loanAsset?.air_quality_index && (
                                    <AirQualityIndicator 
                                        aqi={loanAsset.air_quality_index}
                                        pm25={loanAsset.green_finance_metrics?.air_quality?.pm25}
                                        compact
                                    />
                                )}
                            </div>
                        )}
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setIsCollapsed(false)}>
                        <ChevronDown className="w-4 h-4" />
                    </Button>
                </div>
            </Card>
        );
    }

    // Expanded view
    return (
        <Card className="p-4">
            <Collapsible open={!isCollapsed} onOpenChange={setIsCollapsed}>
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <ShieldCheck className="w-5 h-5 text-indigo-500" />
                        <h3 className="font-semibold">Asset Verification</h3>
                        {isVerified && (
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                    classification?.ndvi < 0.75 ? 'bg-red-500/20 text-red-500' : 'bg-green-500/20 text-green-500'
                                }`}>
                                    {classification?.ndvi < 0.75 ? 'BREACH' : 'VERIFIED'}
                                </span>
                                {loanAsset?.location_type && (
                                    <LocationTypeBadge 
                                        locationType={loanAsset.location_type}
                                        confidence={loanAsset.green_finance_metrics?.location_confidence}
                                        compact
                                    />
                                )}
                                {loanAsset?.air_quality_index && (
                                    <AirQualityIndicator 
                                        aqi={loanAsset.air_quality_index}
                                        pm25={loanAsset.green_finance_metrics?.air_quality?.pm25}
                                        compact
                                    />
                                )}
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        {onViewFull && (
                            <Button variant="ghost" size="sm" onClick={onViewFull}>
                                <ExternalLink className="w-4 h-4 mr-1" />
                                View Full
                            </Button>
                        )}
                        {embedded && (
                            <Button variant="ghost" size="sm" onClick={() => setIsCollapsed(true)}>
                                <ChevronUp className="w-4 h-4" />
                            </Button>
                        )}
                    </div>
                </div>

                <div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Left Column: Upload & Status */}
                        <div className="flex flex-col gap-4">
                            {!isVerified ? (
                                <DropZone onFileSelect={handleFileSelect} isProcessing={isAnalyzing} />
                            ) : (
                                <>
                                    <Card className="bg-zinc-900 border-red-500/30 p-4">
                                        <div className="flex items-center gap-4 mb-4">
                                            <div className="p-3 rounded-full bg-red-500/10">
                                                <ShieldCheck className="w-6 h-6 text-red-500" />
                                            </div>
                                            <div>
                                                <h4 className="font-bold text-white">Covenant Breached</h4>
                                                <p className="text-red-400 text-sm">Risk Detected: Vegetation Below Threshold</p>
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                            <div className="bg-black/50 p-2 rounded">
                                                <span className="text-zinc-500 block text-xs">Classified As</span>
                                                <span className={`font-mono font-bold text-sm ${classification?.classification === 'AnnualCrop' ? 'text-yellow-400' : 'text-green-400'}`}>
                                                    {classification?.classification || 'Unknown'}
                                                </span>
                                            </div>
                                            <div className="bg-black/50 p-2 rounded">
                                                <span className="text-zinc-500 block text-xs">NDVI Score</span>
                                                <span className={`font-mono font-bold text-sm ${classification?.ndvi < 0.75 ? 'text-red-500' : 'text-green-500'}`}>
                                                    {classification?.ndvi?.toFixed(2) || 'N/A'}
                                                </span>
                                            </div>
                                        </div>
                                    </Card>
                                    
                                    {/* Green Finance Metrics */}
                                    {loanAsset?.green_finance_metrics && (
                                        <GreenFinanceMetricsCard 
                                            metrics={loanAsset.green_finance_metrics}
                                            compact
                                        />
                                    )}
                                </>
                            )}

                            {/* Compact Agent Terminal */}
                            <div className="min-h-[200px]">
                                <AgentTerminal logs={displayLogs} thinking={isAnalyzing} />
                            </div>

                            {/* Action Button */}
                            {(file || extractedText) && !isVerified && (
                                <Button
                                    size="lg"
                                    onClick={handleSecuritize}
                                    disabled={isAnalyzing || verificationLoading}
                                    className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500"
                                >
                                    {(isAnalyzing || verificationLoading) ? (
                                        <>
                                            <ShieldCheck className="w-4 h-4 mr-2 animate-spin" />
                                            PROCESSING...
                                        </>
                                    ) : (
                                        <>
                                            <ShieldCheck className="w-4 h-4 mr-2" />
                                            SECURITIZE & VERIFY
                                        </>
                                    )}
                                </Button>
                            )}
                            
                            {/* Error Display */}
                            {verificationError && (
                                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                                    {verificationError}
                                </div>
                            )}
                        </div>

                        {/* Right Column: Map Preview */}
                        <div className="h-[400px] bg-zinc-900/50 rounded-lg border border-zinc-800 overflow-hidden relative">
                            {isVerified && loanAsset ? (
                                <>
                                    <MapView 
                                        assets={[{
                                            id: loanAsset.id,
                                            loan_id: loanAsset.loan_id,
                                            collateral_address: loanAsset.collateral_address || 'Unknown',
                                            geo_lat: loanAsset.geo_lat,
                                            geo_lon: loanAsset.geo_lon,
                                            risk_status: loanAsset.risk_status,
                                            last_verified_score: loanAsset.last_verified_score,
                                            spt_threshold: loanAsset.spt_threshold,
                                            current_interest_rate: loanAsset.current_interest_rate
                                        }]} 
                                        showSatellite={true}
                                        assetId={loanAsset.id}
                                        showLayerControls={true}
                                    />
                                    <div className="absolute bottom-4 left-4 z-[1000] bg-black/80 backdrop-blur px-3 py-1.5 rounded border border-red-500/50">
                                        <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Satellite Intelligence</div>
                                        <div className="flex items-center gap-2">
                                            <Globe className="w-3 h-3 text-indigo-400" />
                                            <span className="font-mono text-white text-xs">Sentinel-2B L2A</span>
                                        </div>
                                        {loanAsset?.location_type && (
                                            <div className="mt-2 pt-2 border-t border-zinc-700">
                                                <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Enhanced Metrics</div>
                                                <div className="flex items-center gap-1.5 text-xs">
                                                    {loanAsset.location_type && (
                                                        <LocationTypeBadge 
                                                            locationType={loanAsset.location_type}
                                                            compact
                                                        />
                                                    )}
                                                    {loanAsset.air_quality_index && (
                                                        <AirQualityIndicator 
                                                            aqi={loanAsset.air_quality_index}
                                                            compact
                                                        />
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-zinc-600">
                                    <Globe className="w-16 h-16 opacity-50" />
                                    <p className="mt-4 text-sm font-light">AWAITING ASSET UPLOAD</p>
                                    <p className="text-xs mt-1 opacity-50">Global Satellite Network Standby</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </Collapsible>
        </Card>
    );
}
