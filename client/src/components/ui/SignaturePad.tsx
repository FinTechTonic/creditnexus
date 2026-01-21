/**
 * SignaturePad Component
 * 
 * HTML5 Canvas-based signature pad for capturing user signatures with:
 * - Smooth line drawing
 * - Touch and mouse support
 * - Clear and undo functionality
 * - Typed signature option
 * - Export to base64 PNG
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Eraser, Undo2, Download } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SignaturePadProps {
  /** Callback when signature is saved */
  onSave?: (signature: string) => void;
  /** Callback when signature is cleared */
  onClear?: () => void;
  /** Initial signature data (base64) */
  initialSignature?: string;
  /** Width of the canvas */
  width?: number;
  /** Height of the canvas */
  height?: number;
  /** Background color */
  backgroundColor?: string;
  /** Pen color */
  penColor?: string;
  /** Pen width */
  penWidth?: number;
  /** Custom className */
  className?: string;
  /** Disabled state */
  disabled?: boolean;
}

interface Point {
  x: number;
  y: number;
}

export function SignaturePad({
  onSave,
  onClear,
  initialSignature,
  width = 600,
  height = 300,
  backgroundColor = '#ffffff',
  penColor = '#000000',
  penWidth = 2,
  className,
  disabled = false,
}: SignaturePadProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [lastPoint, setLastPoint] = useState<Point | null>(null);
  const [history, setHistory] = useState<ImageData[]>([]);
  const [typedSignature, setTypedSignature] = useState('');
  const [activeTab, setActiveTab] = useState<'draw' | 'type'>('draw');

  // Initialize canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = width;
    canvas.height = height;

    // Set drawing styles
    ctx.strokeStyle = penColor;
    ctx.lineWidth = penWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Fill background
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, width, height);

    // Load initial signature if provided
    if (initialSignature) {
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0, width, height);
        saveState();
      };
      img.src = initialSignature;
    } else {
      saveState();
    }
  }, [width, height, backgroundColor, penColor, penWidth, initialSignature]);

  // Save canvas state for undo
  const saveState = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    setHistory((prev) => [...prev, imageData]);
  }, []);

  // Get coordinates relative to canvas
  const getCoordinates = useCallback((e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement> | MouseEvent | TouchEvent): Point | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    if ('touches' in e) {
      // Touch event
      const touch = e.touches[0] || e.changedTouches[0];
      if (!touch) return null;
      return {
        x: (touch.clientX - rect.left) * scaleX,
        y: (touch.clientY - rect.top) * scaleY,
      };
    } else {
      // Mouse event
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
      };
    }
  }, []);

  // Start drawing
  const startDrawing = useCallback((e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (disabled) return;
    
    e.preventDefault();
    const point = getCoordinates(e);
    if (!point) return;

    setIsDrawing(true);
    setLastPoint(point);
    saveState();
  }, [disabled, getCoordinates, saveState]);

  // Draw
  const draw = useCallback((e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDrawing || disabled) return;

    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const currentPoint = getCoordinates(e);
    if (!currentPoint || !lastPoint) return;

    // Draw smooth line
    ctx.beginPath();
    ctx.moveTo(lastPoint.x, lastPoint.y);
    ctx.lineTo(currentPoint.x, currentPoint.y);
    ctx.stroke();

    setLastPoint(currentPoint);
  }, [isDrawing, disabled, getCoordinates, lastPoint]);

  // Stop drawing
  const stopDrawing = useCallback(() => {
    if (isDrawing) {
      setIsDrawing(false);
      setLastPoint(null);
      saveState();
    }
  }, [isDrawing, saveState]);

  // Clear canvas
  const handleClear = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || disabled) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    setHistory([]);
    setLastPoint(null);
    setIsDrawing(false);
    onClear?.();
  }, [disabled, backgroundColor, onClear]);

  // Undo last stroke
  const handleUndo = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || disabled || history.length <= 1) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Remove last state
    const newHistory = [...history];
    newHistory.pop();

    // Restore previous state
    const previousState = newHistory[newHistory.length - 1];
    ctx.putImageData(previousState, 0, 0);

    setHistory(newHistory);
    setLastPoint(null);
    setIsDrawing(false);
  }, [disabled, history]);

  // Render typed signature
  const renderTypedSignature = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (typedSignature.trim()) {
      // Set font
      ctx.fillStyle = penColor;
      ctx.font = 'bold 48px "Brush Script MT", "Lucida Handwriting", cursive, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Draw text
      ctx.fillText(typedSignature, canvas.width / 2, canvas.height / 2);
    }

    saveState();
  }, [typedSignature, backgroundColor, penColor, saveState]);

  // Update typed signature rendering
  useEffect(() => {
    if (activeTab === 'type') {
      renderTypedSignature();
    }
  }, [activeTab, typedSignature, renderTypedSignature]);

  // Export to base64 PNG
  const handleExport = useCallback((): string | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;

    return canvas.toDataURL('image/png');
  }, []);

  // Handle save
  const handleSave = useCallback(() => {
    const signature = handleExport();
    if (signature) {
      onSave?.(signature);
    }
  }, [handleExport, onSave]);

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'draw' | 'type')}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="draw" disabled={disabled}>
            Draw
          </TabsTrigger>
          <TabsTrigger value="type" disabled={disabled}>
            Type
          </TabsTrigger>
        </TabsList>

        <TabsContent value="draw" className="mt-4">
          <div className="border rounded-lg overflow-hidden bg-white">
            <canvas
              ref={canvasRef}
              className="cursor-crosshair touch-none"
              onMouseDown={startDrawing}
              onMouseMove={draw}
              onMouseUp={stopDrawing}
              onMouseLeave={stopDrawing}
              onTouchStart={startDrawing}
              onTouchMove={draw}
              onTouchEnd={stopDrawing}
              style={{
                width: '100%',
                maxWidth: `${width}px`,
                height: 'auto',
                aspectRatio: `${width} / ${height}`,
                display: 'block',
                touchAction: 'none',
              }}
            />
          </div>
        </TabsContent>

        <TabsContent value="type" className="mt-4">
          <div className="space-y-4">
            <Input
              type="text"
              placeholder="Enter your name"
              value={typedSignature}
              onChange={(e) => setTypedSignature(e.target.value)}
              disabled={disabled}
              className="text-center text-lg"
            />
            <div className="border rounded-lg overflow-hidden bg-white">
              <canvas
                ref={canvasRef}
                className="w-full"
                style={{
                  width: '100%',
                  maxWidth: `${width}px`,
                  height: 'auto',
                  aspectRatio: `${width} / ${height}`,
                  display: 'block',
                  touchAction: 'none',
                }}
              />
            </div>
          </div>
        </TabsContent>
      </Tabs>

      <div className="flex flex-wrap gap-2">
        {activeTab === 'draw' && (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={handleUndo}
              disabled={disabled || history.length <= 1}
              className="flex items-center gap-2"
            >
              <Undo2 className="h-4 w-4" />
              Undo
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleClear}
              disabled={disabled}
              className="flex items-center gap-2"
            >
              <Eraser className="h-4 w-4" />
              Clear
            </Button>
          </>
        )}
        <Button
          variant="default"
          size="sm"
          onClick={handleSave}
          disabled={disabled}
          className="flex items-center gap-2 ml-auto"
        >
          <Download className="h-4 w-4" />
          Save Signature
        </Button>
      </div>
    </div>
  );
}

// Export hook for programmatic access
export function useSignaturePad() {
  const [signature, setSignature] = useState<string | null>(null);

  const handleSave = useCallback((sig: string) => {
    setSignature(sig);
  }, []);

  return {
    signature,
    setSignature,
    handleSave,
  };
}
