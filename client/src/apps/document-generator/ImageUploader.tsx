/**
 * Image Uploader Component
 * 
 * Drag-and-drop image upload with preview, webcam capture, and extraction progress.
 * Supports multiple images and extracts CDM data from OCR text.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Upload, Camera, X, Loader2, AlertCircle, CheckCircle2, Image as ImageIcon } from 'lucide-react';
import { fetchWithAuth } from '../../context/AuthContext';

interface ImageFile {
  file: File;
  preview: string;
  id: string;
}

interface ExtractionResult {
  status: string;
  ocr_text: string;
  ocr_text_length: number;
  source_filenames: string[];
  images_processed: number;
  ocr_texts_per_image: Array<{
    filename: string;
    text: string;
    length: number;
  }>;
  agreement?: Record<string, unknown>;
  extraction_status?: string;
  extraction_message?: string;
}

interface ImageUploaderProps {
  onExtractionComplete?: (result: ExtractionResult) => void;
  onError?: (error: string) => void;
  extractCdm?: boolean;
  className?: string;
  theme?: 'light' | 'dark';
}

export function ImageUploader({
  onExtractionComplete,
  onError,
  extractCdm = true,
  className = '',
  theme = 'light',
}: ImageUploaderProps) {
  const isDark = theme === 'dark';
  const [images, setImages] = useState<ImageFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null);
  
  // Webcam state
  const [isWebcamActive, setIsWebcamActive] = useState(false);
  const [webcamError, setWebcamError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Cleanup image preview URLs
      images.forEach((img) => {
        URL.revokeObjectURL(img.preview);
      });
      // Stop webcam stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [images]);

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
    const imageFiles = files.filter((file) => 
      file.type.startsWith('image/') || 
      /\.(png|jpg|jpeg|webp|gif|bmp|tiff|tif)$/i.test(file.name)
    );

    if (imageFiles.length === 0) {
      setError('No valid image files found. Supported formats: PNG, JPEG, WEBP, GIF, BMP, TIFF');
      return;
    }

    addImages(imageFiles);
  }, []);

  const addImages = useCallback((files: File[]) => {
    const newImages: ImageFile[] = files.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      id: `${Date.now()}-${Math.random()}`,
    }));

    setImages((prev) => [...prev, ...newImages]);
    setError(null);
    setExtractionResult(null);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      addImages(Array.from(files));
    }
    // Reset input to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [addImages]);

  const removeImage = useCallback((id: string) => {
    setImages((prev) => {
      const image = prev.find((img) => img.id === id);
      if (image) {
        URL.revokeObjectURL(image.preview);
      }
      return prev.filter((img) => img.id !== id);
    });
    setExtractionResult(null);
  }, []);

  const startWebcam = useCallback(async () => {
    try {
      setWebcamError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }, // Prefer back camera on mobile
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsWebcamActive(true);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to access webcam';
      setWebcamError(`Webcam access denied or unavailable: ${errorMessage}`);
      if (onError) {
        onError(errorMessage);
      }
    }
  }, [onError]);

  const stopWebcam = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsWebcamActive(false);
    setWebcamError(null);
  }, []);

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');

    if (!context) return;

    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw video frame to canvas
    context.drawImage(video, 0, 0);

    // Convert canvas to blob
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `webcam-${Date.now()}.png`, { type: 'image/png' });
        addImages([file]);
      }
    }, 'image/png');
  }, [addImages]);

  const handleExtract = useCallback(async () => {
    if (images.length === 0) {
      setError('Please add at least one image');
      return;
    }

    try {
      setIsProcessing(true);
      setError(null);
      setExtractionResult(null);

      // Create FormData with all images
      const formData = new FormData();
      images.forEach((img) => {
        formData.append('files', img.file);
      });

      // Add query parameters
      const params = new URLSearchParams();
      params.append('extract_cdm', extractCdm.toString());

      const url = `/api/image/extract${params.toString() ? `?${params.toString()}` : ''}`;

      const response = await fetchWithAuth(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail?.message || errorData.detail || 'Extraction failed';
        throw new Error(errorMessage);
      }

      const result: ExtractionResult = await response.json();
      setExtractionResult(result);

      if (onExtractionComplete) {
        onExtractionComplete(result);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Extraction failed';
      setError(errorMessage);
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setIsProcessing(false);
    }
  }, [images, extractCdm, onExtractionComplete, onError]);

  return (
    <div className={`${isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-gray-200'} rounded-lg border p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <ImageIcon className={`w-5 h-5 ${isDark ? 'text-slate-400' : 'text-gray-600'}`} />
        <h3 className={`text-lg font-semibold ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>Image Upload</h3>
      </div>

      {/* Error Display */}
      {(error || webcamError) && (
        <div className={`mb-4 ${isDark ? 'bg-red-500/10 border-red-500/20' : 'bg-red-50 border-red-200'} rounded-lg p-3`}>
          <div className="flex items-center gap-2">
            <AlertCircle className={`w-4 h-4 ${isDark ? 'text-red-400' : 'text-red-600'}`} />
            <p className={`text-sm ${isDark ? 'text-red-400' : 'text-red-700'}`}>{error || webcamError}</p>
          </div>
        </div>
      )}

      {/* Drag and Drop Zone */}
      <div
        className={`
          border-2 border-dashed rounded-lg p-8 text-center transition-all
          ${isDragOver 
            ? (isDark ? 'border-emerald-500 bg-emerald-500/10' : 'border-blue-500 bg-blue-50')
            : (isDark ? 'border-slate-600 hover:border-emerald-500/50' : 'border-gray-300 hover:border-gray-400')
          }
          ${isProcessing ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept="image/*"
          multiple
          onChange={handleFileInput}
        />

        <div className="flex flex-col items-center gap-4">
          <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
            isDragOver 
              ? (isDark ? 'bg-emerald-500/20' : 'bg-blue-100')
              : (isDark ? 'bg-slate-700' : 'bg-gray-100')
          }`}>
            <Upload className={`w-8 h-8 ${
              isDragOver 
                ? (isDark ? 'text-emerald-400' : 'text-blue-600')
                : (isDark ? 'text-slate-400' : 'text-gray-600')
            }`} />
          </div>

          <div className="space-y-1">
            <p className={`text-lg font-medium ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>
              {images.length > 0 
                ? `${images.length} image${images.length > 1 ? 's' : ''} selected`
                : 'Drop images here or click to upload'
              }
            </p>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>
              Supports PNG, JPEG, WEBP, GIF, BMP, TIFF
            </p>
          </div>
        </div>
      </div>

      {/* Webcam Section */}
      <div className="mt-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Camera className={`w-5 h-5 ${isDark ? 'text-slate-400' : 'text-gray-600'}`} />
            <span className={`text-sm font-medium ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>Webcam Capture</span>
          </div>
          {!isWebcamActive ? (
            <button
              onClick={startWebcam}
              className={`px-4 py-2 ${isDark ? 'bg-slate-700 text-slate-200 hover:bg-slate-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'} rounded-lg font-medium text-sm transition-colors`}
            >
              Start Webcam
            </button>
          ) : (
            <button
              onClick={stopWebcam}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium text-sm transition-colors"
            >
              Stop Webcam
            </button>
          )}
        </div>

        {isWebcamActive && (
          <div className="relative bg-gray-900 rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              className="w-full h-auto max-h-64 object-contain"
            />
            <canvas ref={canvasRef} className="hidden" />
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2">
              <button
                onClick={capturePhoto}
                className="w-16 h-16 rounded-full bg-white border-4 border-gray-300 hover:border-gray-400 transition-colors flex items-center justify-center"
                title="Capture Photo"
              >
                <Camera className="w-8 h-8 text-gray-700" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Image Preview Grid */}
      {images.length > 0 && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className={`text-sm font-medium ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>
              Selected Images ({images.length})
            </h4>
            <button
              onClick={handleExtract}
              disabled={isProcessing}
              className={`px-4 py-2 ${isDark ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2`}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Extracting...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  Extract CDM Data
                </>
              )}
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {images.map((image) => (
              <div key={image.id} className="relative group">
                <div className={`aspect-square rounded-lg overflow-hidden border-2 ${isDark ? 'border-slate-700 bg-slate-800' : 'border-gray-200 bg-gray-100'}`}>
                  <img
                    src={image.preview}
                    alt={image.file.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <button
                  onClick={() => removeImage(image.id)}
                  className="absolute top-1 right-1 w-6 h-6 bg-red-600 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                  title="Remove image"
                >
                  <X className="w-4 h-4" />
                </button>
                <p className="mt-1 text-xs text-gray-600 truncate" title={image.file.name}>
                  {image.file.name}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Extraction Result */}
      {extractionResult && (
        <div className="mt-4 space-y-3">
          <div className={`${isDark ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-green-50 border-green-200'} rounded-lg p-3`}>
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className={`w-4 h-4 ${isDark ? 'text-emerald-400' : 'text-green-600'}`} />
              <span className={`text-sm font-medium ${isDark ? 'text-emerald-300' : 'text-green-800'}`}>Extraction Complete</span>
            </div>
            <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-green-700'}`}>
              {extractionResult.ocr_text_length} characters extracted from {extractionResult.images_processed} image(s)
            </p>
          </div>

          {/* OCR Text Preview */}
          <div className={`${isDark ? 'bg-slate-900/50' : 'bg-gray-50'} rounded-lg p-3 max-h-48 overflow-y-auto`}>
            <p className={`text-xs font-medium ${isDark ? 'text-slate-300' : 'text-gray-700'} mb-2`}>OCR Text:</p>
            <p className={`text-sm ${isDark ? 'text-slate-300' : 'text-gray-700'} whitespace-pre-wrap`}>
              {extractionResult.ocr_text}
            </p>
          </div>

          {/* Per-Image OCR Results */}
          {extractionResult.ocr_texts_per_image && extractionResult.ocr_texts_per_image.length > 1 && (
            <div className={`${isDark ? 'bg-slate-900/50' : 'bg-gray-50'} rounded-lg p-3`}>
              <p className={`text-xs font-medium ${isDark ? 'text-slate-300' : 'text-gray-700'} mb-2`}>Per-Image Results:</p>
              <div className="space-y-2">
                {extractionResult.ocr_texts_per_image.map((item, idx) => (
                  <div key={idx} className={`text-xs ${isDark ? 'text-slate-400' : 'text-gray-600'}`}>
                    <span className="font-medium">{item.filename}:</span> {item.length} characters
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* CDM Data Result */}
          {extractionResult.agreement && (
            <div className={`${isDark ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-blue-50 border-blue-200'} rounded-lg p-3`}>
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className={`w-4 h-4 ${isDark ? 'text-emerald-400' : 'text-blue-600'}`} />
                <span className={`text-sm font-medium ${isDark ? 'text-emerald-300' : 'text-blue-800'}`}>CDM Data Extracted</span>
              </div>
              <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-blue-700'}`}>
                Status: {extractionResult.extraction_status || 'success'}
              </p>
              {extractionResult.extraction_message && (
                <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-blue-600'} mt-1`}>
                  {extractionResult.extraction_message}
                </p>
              )}
            </div>
          )}

          {extractionResult.extraction_status === 'error' && (
            <div className={`${isDark ? 'bg-yellow-500/10 border-yellow-500/20' : 'bg-yellow-50 border-yellow-200'} rounded-lg p-3`}>
              <p className={`text-xs ${isDark ? 'text-yellow-400' : 'text-yellow-700'}`}>
                CDM extraction failed: {extractionResult.extraction_message}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}















