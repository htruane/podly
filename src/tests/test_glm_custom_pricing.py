from unittest.mock import MagicMock

import pytest
from flask import Flask

from app.extensions import db
from app.models import ModelCall
from podcast_processor.ad_classifier import AdClassifier
from shared.config import Config
from shared.test_utils import create_standard_test_config


@pytest.fixture
def app() -> Flask:
    """Create and configure a Flask app for testing."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield app


@pytest.fixture
def test_config() -> Config:
    return create_standard_test_config()


def test_glm_4_5_air_custom_pricing(test_config: Config, app: Flask) -> None:
    """Test that glm-4.5-air model gets custom pricing configuration."""
    with app.app_context():
        classifier = AdClassifier(config=test_config)

        # Test various glm-4.5-air model name formats
        test_models = [
            "glm-4.5-air",
            "GLM-4.5-AIR",
            "zhipu/glm-4.5-air",
            "glm-4-5-air",
        ]

        for model_name in test_models:
            model_call = ModelCall(
                post_id=1,
                model_name=model_name,
                prompt="test prompt",
                first_segment_sequence_num=0,
                last_segment_sequence_num=0,
                status="pending",
            )

            completion_args = classifier._prepare_api_call(
                model_call, "test system prompt"
            )

            assert completion_args is not None
            assert "input_cost_per_token" in completion_args
            assert "output_cost_per_token" in completion_args
            assert completion_args["input_cost_per_token"] == 0.0000002
            assert completion_args["output_cost_per_token"] == 0.0000011


def test_non_glm_model_no_custom_pricing(test_config: Config, app: Flask) -> None:
    """Test that non-glm models do not get custom pricing parameters."""
    with app.app_context():
        classifier = AdClassifier(config=test_config)

        model_call = ModelCall(
            post_id=1,
            model_name="gpt-4o-mini",
            prompt="test prompt",
            first_segment_sequence_num=0,
            last_segment_sequence_num=0,
            status="pending",
        )

        completion_args = classifier._prepare_api_call(
            model_call, "test system prompt"
        )

        assert completion_args is not None
        assert "input_cost_per_token" not in completion_args
        assert "output_cost_per_token" not in completion_args
