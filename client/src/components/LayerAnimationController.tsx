/**
 * Layer Animation Controller Component.
 * 
 * Provides playback controls for animating through layers:
 * - Play/pause functionality
 * - Speed control (slow, normal, fast)
 * - Timeline scrubber
 * - Loop option
 * - Keyboard shortcuts
 */

import { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Play, Pause, SkipBack, SkipForward, RotateCcw, Settings } from 'lucide-react';
import { useLayerStore } from '@/stores/layerStore';

interface LayerAnimationControllerProps {
  assetId: number;
  className?: string;
  compact?: boolean;
}

export function LayerAnimationController({
  assetId,
  className = '',
  compact = false
}: LayerAnimationControllerProps) {
  const {
    animation,
    getLayersForAsset,
    playAnimation,
    pauseAnimation,
    nextLayer,
    previousLayer,
    setAnimationSpeed,
    toggleLoop,
    setAnimationState,
    selectLayer
  } = useLayerStore();

  const [isPlaying, setIsPlaying] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const layers = getLayersForAsset(assetId);
  const currentLayer = layers[animation.currentIndex];

  // Speed intervals (milliseconds between layer changes)
  const speedIntervals: Record<'slow' | 'normal' | 'fast', number> = {
    slow: 2000,
    normal: 1000,
    fast: 500
  };

  // Auto-advance layers when playing
  useEffect(() => {
    if (isPlaying && layers.length > 0) {
      intervalRef.current = setInterval(() => {
        if (animation.loop) {
          // Loop: go to next, wrap around
          nextLayer();
        } else {
          // No loop: stop at end
          if (animation.currentIndex < layers.length - 1) {
            nextLayer();
          } else {
            setIsPlaying(false);
            pauseAnimation();
          }
        }
      }, speedIntervals[animation.speed]);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [isPlaying, animation.speed, animation.loop, animation.currentIndex, layers.length]);

  // Update animation state when layers change
  useEffect(() => {
    if (layers.length > 0) {
      setAnimationState({ layers });
      
      // Select current layer
      if (currentLayer) {
        selectLayer(String(currentLayer.id));
      }
    }
  }, [layers, currentLayer]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Only handle if component is visible/focused
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case ' ':
          e.preventDefault();
          handlePlayPause();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          previousLayer();
          break;
        case 'ArrowRight':
          e.preventDefault();
          nextLayer();
          break;
        case 'l':
        case 'L':
          e.preventDefault();
          toggleLoop();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  const handlePlayPause = () => {
    if (isPlaying) {
      setIsPlaying(false);
      pauseAnimation();
    } else {
      setIsPlaying(true);
      playAnimation();
    }
  };

  const handlePrevious = () => {
    previousLayer();
    if (isPlaying) {
      // Restart interval
      setIsPlaying(false);
      setIsPlaying(true);
    }
  };

  const handleNext = () => {
    nextLayer();
    if (isPlaying) {
      // Restart interval
      setIsPlaying(false);
      setIsPlaying(true);
    }
  };

  const handleSpeedChange = (speed: 'slow' | 'normal' | 'fast') => {
    setAnimationSpeed(speed);
    if (isPlaying) {
      // Restart interval with new speed
      setIsPlaying(false);
      setIsPlaying(true);
    }
  };

  const handleTimelineChange = (value: number[]) => {
    const newIndex = Math.floor((value[0] / 100) * (layers.length - 1));
    setAnimationState({ currentIndex: newIndex });
    selectLayer(String(layers[newIndex]?.id || ''));
    
    if (isPlaying) {
      // Restart interval
      setIsPlaying(false);
      setIsPlaying(true);
    }
  };

  if (layers.length === 0) {
    return null; // Don't show if no layers
  }

  const timelineValue = layers.length > 1 
    ? (animation.currentIndex / (layers.length - 1)) * 100 
    : 0;

  if (compact) {
    return (
      <div className={`absolute bottom-4 left-4 z-[1001] ${className}`}>
        <Card className="bg-black/80 backdrop-blur border-zinc-700">
          <CardContent className="p-2">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handlePlayPause}
                className="h-8 w-8 p-0"
              >
                {isPlaying ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
              </Button>
              <div className="text-xs text-white">
                {animation.currentIndex + 1} / {layers.length}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <Card className={`absolute bottom-4 left-4 z-[1001] bg-black/80 backdrop-blur border-zinc-700 ${className}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Layer Animation
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Playback Controls */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrevious}
            disabled={!animation.loop && animation.currentIndex === 0}
            className="h-8 w-8 p-0 border-zinc-700"
          >
            <SkipBack className="w-4 h-4" />
          </Button>
          
          <Button
            variant="default"
            size="sm"
            onClick={handlePlayPause}
            className="h-8 px-4 bg-indigo-600 hover:bg-indigo-700"
          >
            {isPlaying ? (
              <>
                <Pause className="w-4 h-4 mr-2" />
                Pause
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Play
              </>
            )}
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={handleNext}
            disabled={!animation.loop && animation.currentIndex === layers.length - 1}
            className="h-8 w-8 p-0 border-zinc-700"
          >
            <SkipForward className="w-4 h-4" />
          </Button>
        </div>

        {/* Timeline Scrubber */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-zinc-400">
              Layer {animation.currentIndex + 1} of {layers.length}
            </span>
            {currentLayer && (
              <span className="text-white font-medium truncate max-w-[200px]">
                {currentLayer.metadata.name || currentLayer.type}
              </span>
            )}
          </div>
          <Slider
            value={[timelineValue]}
            onValueChange={handleTimelineChange}
            min={0}
            max={100}
            step={100 / Math.max(1, layers.length - 1)}
            className="w-full"
          />
        </div>

        {/* Speed Control */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400 w-12">Speed:</span>
          <div className="flex gap-1 flex-1">
            {(['slow', 'normal', 'fast'] as const).map((speed) => (
              <Button
                key={speed}
                variant={animation.speed === speed ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleSpeedChange(speed)}
                className={`flex-1 text-xs h-7 ${
                  animation.speed === speed
                    ? 'bg-indigo-600 hover:bg-indigo-700'
                    : 'border-zinc-700'
                }`}
              >
                {speed.charAt(0).toUpperCase() + speed.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        {/* Loop Toggle */}
        <div className="flex items-center justify-between">
          <label className="text-xs text-zinc-400 flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={animation.loop}
              onChange={toggleLoop}
              className="w-4 h-4 rounded border-zinc-700 bg-zinc-800 text-indigo-600 focus:ring-indigo-500"
            />
            Loop
          </label>
          <div className="text-xs text-zinc-500">
            <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded border border-zinc-700">Space</kbd> Play/Pause
            {' '}
            <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded border border-zinc-700">←</kbd>
            <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded border border-zinc-700">→</kbd> Navigate
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
