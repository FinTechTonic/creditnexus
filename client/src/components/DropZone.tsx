import { useCallback, useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';

interface DropZoneProps {
    onFileSelect: (file: File) => void;
    isProcessing?: boolean;
}

export function DropZone({ onFileSelect, isProcessing = false }: DropZoneProps) {
    const [isDragOver, setIsDragOver] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        setError(null);

        const files = Array.from(e.dataTransfer.files);
        if (files.length === 0) return;

        const file = files[0];
        if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
            setError('Only PDF files are supported.');
            return;
        }

        setSelectedFile(file);
        onFileSelect(file);
    }, [onFileSelect]);

    const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            setSelectedFile(files[0]);
            onFileSelect(files[0]);
        }
    }, [onFileSelect]);

    return (
        <div
            className={`
        border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 cursor-pointer
        ${isDragOver
                    ? 'border-indigo-500 bg-indigo-500/10 scale-[1.02]'
                    : 'border-zinc-700 hover:border-zinc-600 bg-zinc-900/50'
                }
        ${isProcessing ? 'opacity-50 pointer-events-none' : ''}
      `}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('hidden-file-input')?.click()}
        >
            <input
                type="file"
                id="hidden-file-input"
                className="hidden"
                accept=".pdf"
                onChange={handleFileInput}
            />

            <div className="flex flex-col items-center gap-4">
                {selectedFile ? (
                    <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center animate-in zoom-in spin-in-12 duration-500">
                        <CheckCircle className="w-8 h-8 text-green-500" />
                    </div>
                ) : (
                    <div className={`w-16 h-16 rounded-full flex items-center justify-center transition-colors ${isDragOver ? 'bg-indigo-500/20' : 'bg-zinc-800'}`}>
                        <Upload className={`w-8 h-8 ${isDragOver ? 'text-indigo-400' : 'text-zinc-400'}`} />
                    </div>
                )}

                <div className="space-y-1">
                    <p className="text-lg font-medium text-white">
                        {selectedFile ? selectedFile.name : "Drop Loan Agreement PDF"}
                    </p>
                    <p className="text-sm text-zinc-400">
                        {selectedFile ? `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB` : "or click to upload"}
                    </p>
                </div>

                {error && (
                    <div className="flex items-center gap-2 text-red-400 text-sm bg-red-900/20 px-3 py-1 rounded-full">
                        <AlertCircle className="w-4 h-4" />
                        {error}
                    </div>
                )}
            </div>
        </div>
    );
}
