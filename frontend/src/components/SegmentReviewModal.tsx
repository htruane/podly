import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { segmentsApi } from '../services/api';
import WaveformTimeline from './WaveformTimeline';
import type { SegmentData, IdentifiedSegment, MergedSegmentRange, SegmentOverride } from '../types';

interface SegmentReviewModalProps {
  episodeGuid: string;
  episodeTitle: string;
  audioUrl: string;
  onClose: () => void;
  onApproved?: () => void;
}

interface SegmentState {
  id: number;
  startTime: number;
  endTime: number;
  text: string;
  approved: boolean;
  isManuallyEdited: boolean;
}

export default function SegmentReviewModal({
  episodeGuid,
  episodeTitle,
  audioUrl,
  onClose,
  onApproved
}: SegmentReviewModalProps) {
  const queryClient = useQueryClient();
  const [segmentStates, setSegmentStates] = useState<SegmentState[]>([]);
  const [mergedRanges, setMergedRanges] = useState<MergedSegmentRange[]>([]);
  const [showWaveform, setShowWaveform] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['identified-segments', episodeGuid],
    queryFn: () => segmentsApi.getIdentifiedSegments(episodeGuid),
  });

  useEffect(() => {
    if (data) {
      const initialStates = data.segments.map(seg => ({
        id: seg.id,
        startTime: seg.start_time,
        endTime: seg.end_time,
        text: seg.text,
        approved: true,
        isManuallyEdited: false
      }));
      setSegmentStates(initialStates);
      setMergedRanges(data.merged_ranges);
    }
  }, [data]);

  const approveMutation = useMutation({
    mutationFn: async () => {
      const overrides: SegmentOverride[] = segmentStates.map(seg => ({
        start_time: seg.startTime,
        end_time: seg.endTime,
        approved: seg.approved
      }));
      return segmentsApi.approveSegments(episodeGuid, overrides);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['episodes'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Segments approved and processing resumed');
      if (onApproved) {
        onApproved();
      }
      onClose();
    },
    onError: (err) => {
      console.error('Failed to approve segments', err);
      toast.error('Failed to approve segments');
    }
  });

  const toggleSegmentApproval = (segmentId: number) => {
    setSegmentStates(prev => prev.map(seg =>
      seg.id === segmentId ? { ...seg, approved: !seg.approved } : seg
    ));
  };

  const updateSegmentTime = (segmentId: number, field: 'startTime' | 'endTime', value: number) => {
    setSegmentStates(prev => prev.map(seg =>
      seg.id === segmentId ? { ...seg, [field]: value, isManuallyEdited: true } : seg
    ));
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDuration = (startTime: number, endTime: number): string => {
    const duration = endTime - startTime;
    return `${duration.toFixed(1)}s`;
  };

  const handleApprove = () => {
    approveMutation.mutate();
  };

  const approvedCount = segmentStates.filter(seg => seg.approved).length;
  const totalCount = segmentStates.length;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-bold text-gray-900 text-left">Review Identified Ad Segments</h2>
            <p className="text-sm text-gray-600 text-left mt-1 truncate">{episodeTitle}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 ml-4 flex-shrink-0"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Info Banner */}
        <div className="bg-blue-50 border-b border-blue-200 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <div className="text-sm text-blue-800 text-left">
                <p className="font-medium mb-1">Review the identified ad segments below</p>
                <p>Toggle segments on/off or adjust times before approving. Approved segments will be removed from the audio.</p>
              </div>
            </div>
            <button
              onClick={() => setShowWaveform(!showWaveform)}
              className="text-xs font-medium text-blue-700 hover:text-blue-900 flex items-center gap-1 whitespace-nowrap"
            >
              {showWaveform ? 'Hide' : 'Show'} Waveform
              <svg className={`w-4 h-4 transition-transform ${showWaveform ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Waveform Section */}
        {showWaveform && mergedRanges.length > 0 && (
          <div className="border-b p-4">
            <WaveformTimeline
              audioUrl={audioUrl}
              segments={mergedRanges}
            />
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-3 text-gray-600">Loading segments...</span>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600">Failed to load segments</p>
            </div>
          ) : segmentStates.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No ad segments identified</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Merged Ranges Summary */}
              {mergedRanges.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-3 text-left">Merged Ad Ranges ({mergedRanges.length})</h3>
                  <p className="text-sm text-gray-600 mb-3 text-left">
                    Contiguous ad segments have been merged into {mergedRanges.length} range{mergedRanges.length !== 1 ? 's' : ''} for removal:
                  </p>
                  <div className="space-y-2">
                    {mergedRanges.map((range, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-white p-3 rounded border">
                        <div className="text-left">
                          <span className="text-sm font-medium text-gray-900">
                            Range {idx + 1}: {formatTime(range.start_time)} - {formatTime(range.end_time)}
                          </span>
                          <span className="ml-2 text-xs text-gray-500">
                            ({formatDuration(range.start_time, range.end_time)})
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">
                          {range.segment_ids.length} segment{range.segment_ids.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Individual Segments */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3 text-left">
                  Individual Segments ({approvedCount}/{totalCount} approved)
                </h3>
                <div className="space-y-3">
                  {segmentStates.map((segment) => (
                    <div
                      key={segment.id}
                      className={`border rounded-lg p-4 transition-all ${
                        segment.approved
                          ? 'bg-red-50 border-red-200'
                          : 'bg-gray-50 border-gray-200 opacity-60'
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        {/* Toggle Checkbox */}
                        <div className="flex-shrink-0 pt-1">
                          <input
                            type="checkbox"
                            checked={segment.approved}
                            onChange={() => toggleSegmentApproval(segment.id)}
                            className="w-5 h-5 text-red-600 border-gray-300 rounded focus:ring-red-500"
                          />
                        </div>

                        {/* Segment Details */}
                        <div className="flex-1 min-w-0 space-y-3">
                          {/* Time Controls */}
                          <div className="flex flex-wrap items-center gap-4">
                            <div className="flex items-center gap-2">
                              <label className="text-sm font-medium text-gray-700">Start:</label>
                              <input
                                type="number"
                                step="0.1"
                                value={segment.startTime}
                                onChange={(e) => updateSegmentTime(segment.id, 'startTime', parseFloat(e.target.value))}
                                className="w-24 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                              />
                              <span className="text-sm text-gray-600">{formatTime(segment.startTime)}</span>
                            </div>

                            <div className="flex items-center gap-2">
                              <label className="text-sm font-medium text-gray-700">End:</label>
                              <input
                                type="number"
                                step="0.1"
                                value={segment.endTime}
                                onChange={(e) => updateSegmentTime(segment.id, 'endTime', parseFloat(e.target.value))}
                                className="w-24 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                              />
                              <span className="text-sm text-gray-600">{formatTime(segment.endTime)}</span>
                            </div>

                            <div className="text-sm text-gray-600">
                              Duration: {formatDuration(segment.startTime, segment.endTime)}
                            </div>

                            {segment.isManuallyEdited && (
                              <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                                Edited
                              </span>
                            )}
                          </div>

                          {/* Transcript Text */}
                          <div className="bg-white p-3 rounded border border-gray-200">
                            <p className="text-sm text-gray-700 text-left line-clamp-3">
                              {segment.text}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-6 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              {approvedCount} of {totalCount} segments will be removed
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                disabled={approveMutation.isPending}
                className={`px-6 py-2 text-sm font-medium text-white rounded-lg ${
                  approveMutation.isPending
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {approveMutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Approving...
                  </span>
                ) : (
                  'Approve & Continue Processing'
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
