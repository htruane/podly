"""
Unit tests for SegmentManager class.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from app.models import Identification, Post, SegmentOverride, TranscriptSegment
from podcast_processor.segment_manager import SegmentManager
from shared.config import Config
from shared.test_utils import create_standard_test_config


@pytest.fixture
def test_segment_manager(
    mock_db_session: MagicMock,
    test_config: Config,
) -> SegmentManager:
    """Return a SegmentManager instance with mock dependencies for testing."""
    return SegmentManager(db_session=mock_db_session, config=test_config)


@pytest.fixture
def test_post() -> Post:
    """Create a test post."""
    return Post(id=1, guid="test-guid-123", title="Test Podcast Episode")


@pytest.fixture
def test_segments() -> list:
    """Create test transcript segments with identifications."""
    segments = [
        TranscriptSegment(
            id=1,
            post_id=1,
            sequence_num=0,
            start_time=10.0,
            end_time=20.0,
            text="This is an ad for product A"
        ),
        TranscriptSegment(
            id=2,
            post_id=1,
            sequence_num=1,
            start_time=20.0,
            end_time=30.0,
            text="Another ad for product A continues"
        ),
        TranscriptSegment(
            id=3,
            post_id=1,
            sequence_num=2,
            start_time=100.0,
            end_time=110.0,
            text="This is a separate ad for product B"
        ),
    ]
    return segments


class TestMergeContiguousSegments:
    """Test the _merge_contiguous_segments method."""

    def test_merge_contiguous_segments_basic(
        self, test_segment_manager: SegmentManager
    ) -> None:
        """Test merging contiguous segments with default gap threshold."""
        segments = [
            {"id": 1, "start_time": 10.0, "end_time": 20.0},
            {"id": 2, "start_time": 20.0, "end_time": 30.0},
            {"id": 3, "start_time": 100.0, "end_time": 110.0},
        ]

        merged = test_segment_manager._merge_contiguous_segments(segments)

        assert len(merged) == 2
        assert merged[0]["start_time"] == 10.0
        assert merged[0]["end_time"] == 30.0
        assert merged[0]["segment_ids"] == [1, 2]
        assert merged[1]["start_time"] == 100.0
        assert merged[1]["end_time"] == 110.0
        assert merged[1]["segment_ids"] == [3]

    def test_merge_with_small_gap(
        self, test_segment_manager: SegmentManager
    ) -> None:
        """Test merging segments with a small gap (within threshold)."""
        segments = [
            {"id": 1, "start_time": 10.0, "end_time": 20.0},
            {"id": 2, "start_time": 23.0, "end_time": 30.0},  # 3 second gap
        ]

        merged = test_segment_manager._merge_contiguous_segments(
            segments, max_gap_seconds=5.0
        )

        assert len(merged) == 1
        assert merged[0]["start_time"] == 10.0
        assert merged[0]["end_time"] == 30.0
        assert merged[0]["segment_ids"] == [1, 2]

    def test_no_merge_with_large_gap(
        self, test_segment_manager: SegmentManager
    ) -> None:
        """Test that segments with large gap don't merge."""
        segments = [
            {"id": 1, "start_time": 10.0, "end_time": 20.0},
            {"id": 2, "start_time": 30.0, "end_time": 40.0},  # 10 second gap
        ]

        merged = test_segment_manager._merge_contiguous_segments(
            segments, max_gap_seconds=5.0
        )

        assert len(merged) == 2
        assert merged[0]["segment_ids"] == [1]
        assert merged[1]["segment_ids"] == [2]

    def test_empty_segments(
        self, test_segment_manager: SegmentManager
    ) -> None:
        """Test merging with empty segment list."""
        merged = test_segment_manager._merge_contiguous_segments([])
        assert merged == []

    def test_single_segment(
        self, test_segment_manager: SegmentManager
    ) -> None:
        """Test merging with single segment."""
        segments = [{"id": 1, "start_time": 10.0, "end_time": 20.0}]
        merged = test_segment_manager._merge_contiguous_segments(segments)

        assert len(merged) == 1
        assert merged[0]["start_time"] == 10.0
        assert merged[0]["end_time"] == 20.0
        assert merged[0]["segment_ids"] == [1]

    def test_unordered_segments(
        self, test_segment_manager: SegmentManager
    ) -> None:
        """Test that unordered segments are sorted before merging."""
        segments = [
            {"id": 3, "start_time": 100.0, "end_time": 110.0},
            {"id": 1, "start_time": 10.0, "end_time": 20.0},
            {"id": 2, "start_time": 20.0, "end_time": 30.0},
        ]

        merged = test_segment_manager._merge_contiguous_segments(segments)

        assert len(merged) == 2
        assert merged[0]["start_time"] == 10.0
        assert merged[0]["end_time"] == 30.0
        assert merged[0]["segment_ids"] == [1, 2]


class TestApplySegmentOverrides:
    """Test the apply_segment_overrides method."""

    def test_apply_overrides_creates_records(
        self, test_segment_manager: SegmentManager, test_post: Post, app: Flask
    ) -> None:
        """Test that applying overrides creates SegmentOverride records."""
        with app.app_context():
            from app.extensions import db
            test_segment_manager.db_session = db.session

            # Add test post to session
            db.session.add(test_post)
            db.session.commit()

            overrides = [
                {"start_time": 10.0, "end_time": 20.0, "approved": True},
                {"start_time": 30.0, "end_time": 40.0, "approved": True},
            ]

            test_segment_manager.apply_segment_overrides(test_post, overrides)

            # Verify overrides were created
            created_overrides = SegmentOverride.query.filter_by(
                post_id=test_post.id
            ).all()
            assert len(created_overrides) == 2
            assert created_overrides[0].start_time == 10.0
            assert created_overrides[0].end_time == 20.0
            assert created_overrides[0].user_approved is True

    def test_apply_overrides_clears_existing(
        self, test_segment_manager: SegmentManager, test_post: Post, app: Flask
    ) -> None:
        """Test that applying overrides clears existing ones."""
        with app.app_context():
            from app.extensions import db
            test_segment_manager.db_session = db.session

            # Add test post to session
            db.session.add(test_post)
            db.session.commit()

            # Create initial override
            old_override = SegmentOverride(
                post_id=test_post.id,
                start_time=5.0,
                end_time=10.0,
                user_approved=True,
            )
            db.session.add(old_override)
            db.session.commit()

            # Apply new overrides
            overrides = [
                {"start_time": 20.0, "end_time": 30.0, "approved": True},
            ]
            test_segment_manager.apply_segment_overrides(test_post, overrides)

            # Verify old override is gone and new one exists
            created_overrides = SegmentOverride.query.filter_by(
                post_id=test_post.id
            ).all()
            assert len(created_overrides) == 1
            assert created_overrides[0].start_time == 20.0
            assert created_overrides[0].end_time == 30.0

    def test_only_approved_segments_saved(
        self, test_segment_manager: SegmentManager, test_post: Post, app: Flask
    ) -> None:
        """Test that only approved segments are saved."""
        with app.app_context():
            from app.extensions import db
            test_segment_manager.db_session = db.session

            # Add test post to session
            db.session.add(test_post)
            db.session.commit()

            overrides = [
                {"start_time": 10.0, "end_time": 20.0, "approved": True},
                {"start_time": 30.0, "end_time": 40.0, "approved": False},
                {"start_time": 50.0, "end_time": 60.0, "approved": True},
            ]

            test_segment_manager.apply_segment_overrides(test_post, overrides)

            # Verify only approved overrides were created
            created_overrides = SegmentOverride.query.filter_by(
                post_id=test_post.id
            ).all()
            assert len(created_overrides) == 2
            assert created_overrides[0].start_time == 10.0
            assert created_overrides[1].start_time == 50.0


class TestGetApprovedSegmentsForRemoval:
    """Test the get_approved_segments_for_removal method."""

    @patch.object(SegmentManager, "_get_ad_segments_from_db")
    @patch.object(SegmentManager, "_merge_contiguous_segments")
    def test_uses_overrides_when_present(
        self,
        mock_merge: MagicMock,
        mock_get_ads: MagicMock,
        test_segment_manager: SegmentManager,
        test_post: Post,
        app: Flask,
    ) -> None:
        """Test that overrides are used when present."""
        with app.app_context():
            from app.extensions import db
            test_segment_manager.db_session = db.session

            # Add test post to session
            db.session.add(test_post)
            db.session.commit()

            # Create overrides
            override1 = SegmentOverride(
                post_id=test_post.id,
                start_time=10.0,
                end_time=20.0,
                user_approved=True,
            )
            override2 = SegmentOverride(
                post_id=test_post.id,
                start_time=30.0,
                end_time=40.0,
                user_approved=True,
            )
            db.session.add_all([override1, override2])
            db.session.commit()

            result = test_segment_manager.get_approved_segments_for_removal(test_post)

            assert len(result) == 2
            assert result[0]["start_time"] == 10.0
            assert result[0]["end_time"] == 20.0
            assert result[1]["start_time"] == 30.0
            assert result[1]["end_time"] == 40.0

            # Verify LLM methods were not called
            mock_get_ads.assert_not_called()
            mock_merge.assert_not_called()

    @patch.object(SegmentManager, "_get_ad_segments_from_db")
    @patch.object(SegmentManager, "_merge_contiguous_segments")
    def test_falls_back_to_llm_when_no_overrides(
        self,
        mock_merge: MagicMock,
        mock_get_ads: MagicMock,
        test_segment_manager: SegmentManager,
        test_post: Post,
        app: Flask,
    ) -> None:
        """Test that LLM identifications are used when no overrides exist."""
        with app.app_context():
            from app.extensions import db
            test_segment_manager.db_session = db.session

            # Add test post to session
            db.session.add(test_post)
            db.session.commit()

            # Mock the LLM segment retrieval
            mock_get_ads.return_value = [
                {"id": 1, "start_time": 10.0, "end_time": 20.0},
            ]
            mock_merge.return_value = [
                {"start_time": 10.0, "end_time": 20.0, "segment_ids": [1]},
            ]

            result = test_segment_manager.get_approved_segments_for_removal(test_post)

            assert len(result) == 1
            assert result[0]["start_time"] == 10.0
            assert result[0]["end_time"] == 20.0

            # Verify LLM methods were called
            mock_get_ads.assert_called_once_with(test_post)
            mock_merge.assert_called_once()


class TestGetIdentifiedSegments:
    """Test the get_identified_segments method."""

    @patch.object(SegmentManager, "_get_ad_segments_from_db")
    @patch.object(SegmentManager, "_merge_contiguous_segments")
    def test_returns_segments_and_merged_ranges(
        self,
        mock_merge: MagicMock,
        mock_get_ads: MagicMock,
        test_segment_manager: SegmentManager,
        test_post: Post,
    ) -> None:
        """Test that both segments and merged ranges are returned."""
        mock_get_ads.return_value = [
            {
                "id": 1,
                "start_time": 10.0,
                "end_time": 20.0,
                "text": "Ad 1",
                "confidence": 0.95,
                "sequence_num": 0,
            },
            {
                "id": 2,
                "start_time": 20.0,
                "end_time": 30.0,
                "text": "Ad 2",
                "confidence": 0.90,
                "sequence_num": 1,
            },
        ]
        mock_merge.return_value = [
            {
                "start_time": 10.0,
                "end_time": 30.0,
                "segment_ids": [1, 2],
            }
        ]

        result = test_segment_manager.get_identified_segments(test_post)

        assert "segments" in result
        assert "merged_ranges" in result
        assert len(result["segments"]) == 2
        assert len(result["merged_ranges"]) == 1
        assert result["segments"][0]["id"] == 1
        assert result["segments"][0]["start_time"] == 10.0
        assert result["segments"][0]["label"] == "ad"
        assert result["merged_ranges"][0]["start_time"] == 10.0
        assert result["merged_ranges"][0]["end_time"] == 30.0
