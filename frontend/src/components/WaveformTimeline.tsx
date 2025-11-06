import { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js';
import type { MergedSegmentRange } from '../types';

interface WaveformTimelineProps {
  audioUrl: string;
  segments: MergedSegmentRange[];
  onSegmentClick?: (segmentIndex: number) => void;
  onSegmentUpdate?: (segmentIndex: number, startTime: number, endTime: number) => void;
  className?: string;
}

export default function WaveformTimeline({
  audioUrl,
  segments,
  onSegmentClick,
  onSegmentUpdate,
  className = ''
}: WaveformTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const regionsPluginRef = useRef<RegionsPlugin | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;

    const regionsPlugin = RegionsPlugin.create();
    regionsPluginRef.current = regionsPlugin;

    const wavesurfer = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#9ca3af',
      progressColor: '#3b82f6',
      cursorColor: '#1f2937',
      barWidth: 2,
      barGap: 1,
      height: 100,
      normalize: true,
      plugins: [regionsPlugin]
    });

    wavesurferRef.current = wavesurfer;

    wavesurfer.on('ready', () => {
      setIsLoading(false);
      setDuration(wavesurfer.getDuration());

      segments.forEach((segment, idx) => {
        regionsPlugin.addRegion({
          start: segment.start_time,
          end: segment.end_time,
          color: 'rgba(239, 68, 68, 0.3)',
          drag: true,
          resize: true,
          id: `segment-${idx}`
        });
      });
    });

    wavesurfer.on('error', (err) => {
      console.error('WaveSurfer error:', err);
      setError('Failed to load audio waveform');
      setIsLoading(false);
    });

    wavesurfer.on('play', () => setIsPlaying(true));
    wavesurfer.on('pause', () => setIsPlaying(false));
    wavesurfer.on('audioprocess', (time) => setCurrentTime(time));
    wavesurfer.on('seeking', (time) => setCurrentTime(time));

    regionsPlugin.on('region-clicked', (region, e) => {
      e.stopPropagation();
      const idx = parseInt(region.id.replace('segment-', ''));
      if (onSegmentClick) {
        onSegmentClick(idx);
      }
    });

    regionsPlugin.on('region-updated', (region) => {
      const idx = parseInt(region.id.replace('segment-', ''));
      if (onSegmentUpdate) {
        onSegmentUpdate(idx, region.start, region.end);
      }
    });

    wavesurfer.load(audioUrl);

    return () => {
      wavesurfer.destroy();
    };
  }, [audioUrl]);

  useEffect(() => {
    if (!wavesurferRef.current || !regionsPluginRef.current) return;

    regionsPluginRef.current.clearRegions();

    segments.forEach((segment, idx) => {
      regionsPluginRef.current?.addRegion({
        start: segment.start_time,
        end: segment.end_time,
        color: 'rgba(239, 68, 68, 0.3)',
        drag: true,
        resize: true,
        id: `segment-${idx}`
      });
    });
  }, [segments]);

  const togglePlayPause = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause();
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900 text-left">Audio Waveform</h4>
        <div className="text-sm text-gray-600">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 mb-3">
          <p className="text-sm text-red-800 text-left">{error}</p>
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-sm text-gray-600">Loading waveform...</span>
        </div>
      )}

      <div ref={containerRef} className={`mb-3 ${isLoading ? 'hidden' : ''}`} />

      <div className="flex items-center gap-3">
        <button
          onClick={togglePlayPause}
          disabled={isLoading}
          className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
            isLoading
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {isPlaying ? (
            <>
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              Pause
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
              </svg>
              Play
            </>
          )}
        </button>

        <div className="text-sm text-gray-600 text-left">
          <span className="font-medium text-red-600">{segments.length}</span> ad region{segments.length !== 1 ? 's' : ''} marked for removal
        </div>
      </div>

      <div className="mt-3 text-xs text-gray-500 text-left">
        Click and drag regions to adjust segment boundaries
      </div>
    </div>
  );
}
