import { useState, useCallback } from 'react';
import type { MergedSegmentRange } from '../types';

export function useWaveform(initialSegments: MergedSegmentRange[]) {
  const [segments, setSegments] = useState<MergedSegmentRange[]>(initialSegments);
  const [selectedSegmentIndex, setSelectedSegmentIndex] = useState<number | null>(null);

  const handleSegmentClick = useCallback((index: number) => {
    setSelectedSegmentIndex(index);
  }, []);

  const handleSegmentUpdate = useCallback((index: number, startTime: number, endTime: number) => {
    setSegments(prev => prev.map((seg, idx) =>
      idx === index ? { ...seg, start_time: startTime, end_time: endTime } : seg
    ));
  }, []);

  const resetSegments = useCallback(() => {
    setSegments(initialSegments);
    setSelectedSegmentIndex(null);
  }, [initialSegments]);

  return {
    segments,
    selectedSegmentIndex,
    handleSegmentClick,
    handleSegmentUpdate,
    resetSegments,
    setSegments
  };
}
