/**
 * Audio Recorder Component
 * 
 * Real-time audio recording component using MediaRecorder API.
 * Records audio, transcribes it, and optionally extracts CDM data.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, Square, Loader2, AlertCircle, CheckCircle2, Play, Pause } from 'lucide-react';
import { fetchWithAuth } from '../../context/AuthContext';

interface TranscriptionResult {
  status: string;
  transcription: string;
  transcription_length: number;
  source_filename: string;
  source_lang?: string;
  target_lang?: string;
  agreement?: Record<string, unknown>;
  extraction_status?: string;
  extraction_message?: string;
}

interface AudioRecorderProps {
  onTranscriptionComplete?: (result: TranscriptionResult) => void;
  onError?: (error: string) => void;
  sourceLang?: string;
  targetLang?: string;
  extractCdm?: boolean;
  className?: string;
  theme?: 'light' | 'dark';
}

export function AudioRecorder({
  onTranscriptionComplete,
  onError,
  sourceLang,
  targetLang,
  extractCdm = true,
  className = '',
  theme = 'light',
}: AudioRecorderProps) {
  const isDark = theme === 'dark';
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [transcriptionResult, setTranscriptionResult] = useState<TranscriptionResult | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current = null;
      }
    };
  }, [audioUrl]);

  const formatTime = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  const startRecording = useCallback(async () => {
    try {
      setError(null);
      setTranscriptionResult(null);
      setAudioBlob(null);
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);
      }

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus', // Fallback to webm
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioBlob(audioBlob);
        
        // Create audio URL for playback
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);

        // Stop all tracks to release microphone
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.onerror = (event) => {
        setError('Recording error occurred');
        console.error('MediaRecorder error:', event);
        stream.getTracks().forEach((track) => track.stop());
      };

      // Start recording
      mediaRecorder.start(1000); // Collect data every second
      setIsRecording(true);
      setRecordingTime(0);

      // Start timer
      timerRef.current = window.setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start recording';
      setError(`Microphone access denied or unavailable: ${errorMessage}`);
      if (onError) {
        onError(errorMessage);
      }
    }
  }, [onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);
  }, []);

  const handleTranscribe = useCallback(async () => {
    if (!audioBlob) {
      setError('No audio recorded');
      return;
    }

    try {
      setIsProcessing(true);
      setError(null);

      // Create FormData for file upload
      const formData = new FormData();
      const audioFile = new File([audioBlob], 'recording.webm', { type: 'audio/webm' });
      formData.append('file', audioFile);

      // Add query parameters
      const params = new URLSearchParams();
      if (sourceLang) params.append('source_lang', sourceLang);
      if (targetLang) params.append('target_lang', targetLang);
      params.append('extract_cdm', extractCdm.toString());

      const url = `/api/audio/transcribe${params.toString() ? `?${params.toString()}` : ''}`;

      const response = await fetchWithAuth(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail?.message || errorData.detail || 'Transcription failed';
        throw new Error(errorMessage);
      }

      const result: TranscriptionResult = await response.json();
      setTranscriptionResult(result);

      if (onTranscriptionComplete) {
        onTranscriptionComplete(result);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Transcription failed';
      setError(errorMessage);
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setIsProcessing(false);
    }
  }, [audioBlob, sourceLang, targetLang, extractCdm, onTranscriptionComplete, onError]);

  const handlePlayPause = useCallback(() => {
    if (!audioUrl) return;

    if (!audioPlayerRef.current) {
      audioPlayerRef.current = new Audio(audioUrl);
      audioPlayerRef.current.onended = () => {
        setIsPlaying(false);
      };
      audioPlayerRef.current.onerror = () => {
        setError('Failed to play audio');
        setIsPlaying(false);
      };
    }

    if (isPlaying) {
      audioPlayerRef.current.pause();
      setIsPlaying(false);
    } else {
      audioPlayerRef.current.play().catch((err) => {
        setError('Failed to play audio');
        console.error('Audio play error:', err);
      });
      setIsPlaying(true);
    }
  }, [audioUrl, isPlaying]);

  return (
    <div className={`${isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-gray-200'} rounded-lg border p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <Mic className={`w-5 h-5 ${isDark ? 'text-slate-400' : 'text-gray-600'}`} />
        <h3 className={`text-lg font-semibold ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>Audio Recording</h3>
      </div>

      {/* Error Display */}
      {error && (
        <div className={`mb-4 ${isDark ? 'bg-red-500/10 border-red-500/20' : 'bg-red-50 border-red-200'} rounded-lg p-3`}>
          <div className="flex items-center gap-2">
            <AlertCircle className={`w-4 h-4 ${isDark ? 'text-red-400' : 'text-red-600'}`} />
            <p className={`text-sm ${isDark ? 'text-red-400' : 'text-red-700'}`}>{error}</p>
          </div>
        </div>
      )}

      {/* Recording Controls */}
      <div className="space-y-4">
        {!isRecording && !audioBlob && (
          <button
            onClick={startRecording}
            className={`w-full flex items-center justify-center gap-2 px-6 py-3 ${isDark ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-lg font-medium transition-colors`}
          >
            <Mic className="w-5 h-5" />
            Start Recording
          </button>
        )}

        {isRecording && (
          <div className="space-y-3">
            <div className="flex items-center justify-center gap-3">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-600 rounded-full animate-pulse" />
                <span className={`text-lg font-mono ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>{formatTime(recordingTime)}</span>
              </div>
            </div>
            <button
              onClick={stopRecording}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-colors"
            >
              <Square className="w-5 h-5" />
              Stop Recording
            </button>
          </div>
        )}

        {audioBlob && !isRecording && (
          <div className="space-y-3">
            <div className={`flex items-center justify-between p-3 ${isDark ? 'bg-slate-900/50' : 'bg-gray-50'} rounded-lg`}>
              <div className="flex items-center gap-2">
                <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-gray-600'}`}>Recording:</span>
                <span className={`text-sm font-medium ${isDark ? 'text-slate-100' : 'text-gray-900'}`}>
                  {formatTime(recordingTime)} • {(audioBlob.size / 1024).toFixed(1)} KB
                </span>
              </div>
              {audioUrl && (
                <button
                  onClick={handlePlayPause}
                  className={`p-2 ${isDark ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'} rounded-lg transition-colors`}
                  title={isPlaying ? 'Pause' : 'Play'}
                >
                  {isPlaying ? (
                    <Pause className="w-4 h-4" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                </button>
              )}
            </div>

            <div className="flex gap-2">
              <button
                onClick={startRecording}
                className={`flex-1 px-4 py-2 ${isDark ? 'bg-slate-700 text-slate-200 hover:bg-slate-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'} rounded-lg font-medium transition-colors`}
              >
                Record Again
              </button>
              <button
                onClick={handleTranscribe}
                disabled={isProcessing}
                className={`flex-1 px-4 py-2 ${isDark ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2`}
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Transcribing...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Transcribe
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Transcription Result */}
        {transcriptionResult && (
          <div className="mt-4 space-y-3">
            <div className={`${isDark ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-green-50 border-green-200'} rounded-lg p-3`}>
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className={`w-4 h-4 ${isDark ? 'text-emerald-400' : 'text-green-600'}`} />
                <span className={`text-sm font-medium ${isDark ? 'text-emerald-300' : 'text-green-800'}`}>Transcription Complete</span>
              </div>
              <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-green-700'}`}>
                {transcriptionResult.transcription_length} characters transcribed
              </p>
            </div>

            <div className={`${isDark ? 'bg-slate-900/50' : 'bg-gray-50'} rounded-lg p-3 max-h-48 overflow-y-auto`}>
              <p className={`text-sm ${isDark ? 'text-slate-300' : 'text-gray-700'} whitespace-pre-wrap`}>
                {transcriptionResult.transcription}
              </p>
            </div>

            {transcriptionResult.agreement && (
              <div className={`${isDark ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-blue-50 border-blue-200'} rounded-lg p-3`}>
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className={`w-4 h-4 ${isDark ? 'text-emerald-400' : 'text-blue-600'}`} />
                  <span className={`text-sm font-medium ${isDark ? 'text-emerald-300' : 'text-blue-800'}`}>CDM Data Extracted</span>
                </div>
                <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-blue-700'}`}>
                  Status: {transcriptionResult.extraction_status || 'success'}
                </p>
                {transcriptionResult.extraction_message && (
                  <p className={`text-xs ${isDark ? 'text-emerald-400' : 'text-blue-600'} mt-1`}>
                    {transcriptionResult.extraction_message}
                  </p>
                )}
              </div>
            )}

            {transcriptionResult.extraction_status === 'error' && (
              <div className={`${isDark ? 'bg-yellow-500/10 border-yellow-500/20' : 'bg-yellow-50 border-yellow-200'} rounded-lg p-3`}>
                <p className={`text-xs ${isDark ? 'text-yellow-400' : 'text-yellow-700'}`}>
                  CDM extraction failed: {transcriptionResult.extraction_message}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}















