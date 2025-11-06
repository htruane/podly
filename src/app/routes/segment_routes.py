import logging

import flask
from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from app.extensions import db
from app.jobs_manager import get_jobs_manager
from app.models import Post, ProcessingJob
from podcast_processor.segment_manager import SegmentManager

logger = logging.getLogger("global_logger")

segment_bp = Blueprint("segment", __name__)


@segment_bp.route("/api/posts/<string:p_guid>/identified-segments", methods=["GET"])
def api_get_identified_segments(p_guid: str) -> ResponseReturnValue:
    """
    Get all identified ad segments for a post.
    Returns both individual segments and merged ranges.
    """
    post = Post.query.filter_by(guid=p_guid).first()
    if not post:
        return flask.jsonify({"error": "Post not found"}), 404

    segment_manager = SegmentManager(db.session)
    result = segment_manager.get_identified_segments(post)

    return flask.jsonify(result), 200


@segment_bp.route("/api/posts/<string:p_guid>/approve-segments", methods=["POST"])
def api_approve_segments(p_guid: str) -> ResponseReturnValue:
    """
    Approve segment overrides and continue processing.

    Expected payload:
    {
        "segments": [
            {
                "start_time": 45.2,
                "end_time": 125.8,
                "approved": true
            }
        ]
    }
    """
    post = Post.query.filter_by(guid=p_guid).first()
    if not post:
        return flask.jsonify({"error": "Post not found"}), 404

    data = request.get_json()
    if not data or "segments" not in data:
        return flask.jsonify({"error": "Missing segments field"}), 400

    segment_manager = SegmentManager(db.session)

    # Apply overrides
    approved_segments = [s for s in data["segments"] if s.get("approved", True)]
    segment_manager.apply_segment_overrides(post, approved_segments)

    # Find the pending review job
    pending_job = ProcessingJob.query.filter_by(
        post_guid=p_guid,
        status="pending_review"
    ).order_by(ProcessingJob.created_at.desc()).first()

    if pending_job:
        # Mark segments as approved
        pending_job.segments_approved = True
        db.session.commit()

        # Resume processing by re-triggering the job
        try:
            result = get_jobs_manager().start_post_processing(p_guid, priority="interactive")
            return flask.jsonify(result), 200
        except Exception as e:
            logger.error(f"Failed to resume processing for {p_guid}: {e}")
            return flask.jsonify({
                "error": "Failed to resume processing",
                "message": str(e)
            }), 500

    return flask.jsonify({
        "message": "Segments approved",
        "approved_count": len(approved_segments)
    }), 200


@segment_bp.route("/api/posts/<string:p_guid>/override-segments", methods=["POST"])
def api_override_segments(p_guid: str) -> ResponseReturnValue:
    """
    Manually override segment times or add new segments.

    Expected payload:
    {
        "segments": [
            {
                "start_time": 45.2,
                "end_time": 125.8,
                "approved": true
            }
        ]
    }
    """
    post = Post.query.filter_by(guid=p_guid).first()
    if not post:
        return flask.jsonify({"error": "Post not found"}), 404

    data = request.get_json()
    if not data or "segments" not in data:
        return flask.jsonify({"error": "Missing segments field"}), 400

    segment_manager = SegmentManager(db.session)
    segment_manager.apply_segment_overrides(post, data["segments"])

    return flask.jsonify({
        "message": "Segments overridden successfully",
        "segment_count": len(data["segments"])
    }), 200
