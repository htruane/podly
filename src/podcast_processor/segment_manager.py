import logging
from typing import Dict, List, Optional, Union

from sqlalchemy.orm import Session, scoped_session

from app.models import (
    Identification,
    Post,
    SegmentOverride,
    TranscriptSegment,
)

logger = logging.getLogger("global_logger")


class SegmentManager:
    """
    Manages segment identification, merging, and user overrides for ad removal.
    """

    def __init__(
        self,
        db_session: Union[Session, scoped_session],
        config: Optional[object] = None,
    ):
        self.db_session = db_session
        self.config = config

    def get_identified_segments(self, post: Post) -> Dict:
        """
        Get all identified ad segments for a post, including merged ranges and full transcript.

        Args:
            post: The Post object to get segments for

        Returns:
            Dictionary with ad segments, merged ranges, and full transcript
        """
        ad_segments = self._get_ad_segments_from_db(post)
        merged_ranges = self._merge_contiguous_segments(ad_segments)
        all_transcript = self._get_all_transcript_segments(post)

        segments_data = []
        for segment in ad_segments:
            segments_data.append(
                {
                    "id": segment["id"],
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "text": segment["text"],
                    "label": "ad",
                    "confidence": segment["confidence"],
                    "sequence_num": segment["sequence_num"],
                }
            )

        return {
            "segments": segments_data,
            "merged_ranges": merged_ranges,
            "transcript": all_transcript,
        }

    def _get_ad_segments_from_db(self, post: Post) -> List[Dict]:
        """
        Query database for all segments identified as ads.

        Returns:
            List of dictionaries with segment information
        """
        ad_identifications = (
            Identification.query.join(TranscriptSegment)
            .filter(TranscriptSegment.post_id == post.id, Identification.label == "ad")
            .order_by(TranscriptSegment.sequence_num)
            .all()
        )

        segments = []
        seen_segment_ids = set()

        for ident in ad_identifications:
            segment = ident.transcript_segment
            if segment.id in seen_segment_ids:
                continue
            seen_segment_ids.add(segment.id)

            segments.append(
                {
                    "id": segment.id,
                    "sequence_num": segment.sequence_num,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "text": segment.text,
                    "confidence": ident.confidence,
                }
            )

        return segments

    def _get_all_transcript_segments(self, post: Post) -> List[Dict]:
        """
        Get all transcript segments with their labels.

        Returns:
            List of all transcript segments with labels
        """
        transcript_segments = (
            TranscriptSegment.query.filter(TranscriptSegment.post_id == post.id)
            .order_by(TranscriptSegment.sequence_num)
            .all()
        )

        result = []
        for segment in transcript_segments:
            identification = Identification.query.filter(
                Identification.transcript_segment_id == segment.id
            ).first()

            result.append(
                {
                    "id": segment.id,
                    "sequence_num": segment.sequence_num,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "text": segment.text,
                    "label": identification.label if identification else "unknown",
                    "confidence": identification.confidence if identification else 0.0,
                }
            )

        return result

    def _merge_contiguous_segments(
        self, segments: List[Dict], max_gap_seconds: float = 5.0
    ) -> List[Dict]:
        """
        Merge contiguous ad segments into ranges.

        Args:
            segments: List of segment dictionaries
            max_gap_seconds: Maximum gap between segments to merge

        Returns:
            List of merged range dictionaries
        """
        if not segments:
            return []

        sorted_segments = sorted(segments, key=lambda s: s["start_time"])
        merged_ranges = []
        current_range = {
            "start_time": sorted_segments[0]["start_time"],
            "end_time": sorted_segments[0]["end_time"],
            "segment_ids": [sorted_segments[0]["id"]],
        }

        for segment in sorted_segments[1:]:
            gap = segment["start_time"] - current_range["end_time"]

            if gap <= max_gap_seconds:
                current_range["end_time"] = segment["end_time"]
                current_range["segment_ids"].append(segment["id"])
            else:
                merged_ranges.append(current_range)
                current_range = {
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                    "segment_ids": [segment["id"]],
                }

        merged_ranges.append(current_range)
        return merged_ranges

    def apply_segment_overrides(self, post: Post, overrides: List[Dict]) -> None:
        """
        Apply user overrides for segments and save to database.

        Args:
            post: The Post object
            overrides: List of override dictionaries with structure:
                {
                    "start_time": float,
                    "end_time": float,
                    "approved": bool
                }
        """
        # Clear existing overrides for this post
        SegmentOverride.query.filter_by(post_id=post.id).delete()

        # Create new overrides
        for override_data in overrides:
            if override_data.get("approved", True):
                override = SegmentOverride(
                    post_id=post.id,
                    start_time=override_data["start_time"],
                    end_time=override_data["end_time"],
                    user_approved=True,
                )
                self.db_session.add(override)

        self.db_session.commit()
        logger.info(f"Applied {len(overrides)} segment overrides for post {post.guid}")

    def get_approved_segments_for_removal(self, post: Post) -> List[Dict]:
        """
        Get all approved segments that should be removed from audio.
        Checks for user overrides first, falls back to LLM identifications.

        Args:
            post: The Post object

        Returns:
            List of segment dictionaries with start_time and end_time
        """
        overrides = SegmentOverride.query.filter_by(
            post_id=post.id, user_approved=True
        ).all()

        if overrides:
            logger.info(
                f"Using {len(overrides)} user-approved segments for post {post.guid}"
            )
            return [
                {
                    "start_time": override.start_time,
                    "end_time": override.end_time,
                }
                for override in overrides
            ]

        # Fall back to LLM identifications
        logger.info(
            f"No overrides found, using LLM identifications for post {post.guid}"
        )
        ad_segments = self._get_ad_segments_from_db(post)
        merged_ranges = self._merge_contiguous_segments(ad_segments)

        return [
            {
                "start_time": r["start_time"],
                "end_time": r["end_time"],
            }
            for r in merged_ranges
        ]
