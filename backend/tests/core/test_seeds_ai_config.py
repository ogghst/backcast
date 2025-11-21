"""Tests for AI configuration seed function."""

import os
from unittest.mock import patch

from sqlmodel import Session, delete, select

from app.core.seeds import _seed_ai_default_config
from app.models import AppConfiguration


def test_seed_ai_default_config_creates_configs(db: Session) -> None:
    """Test that _seed_ai_default_config creates default AI configuration entries."""
    # Clear any existing AI configs
    statement = delete(AppConfiguration)
    db.execute(statement)
    db.commit()

    # Run seed function
    _seed_ai_default_config(db)

    # Verify base URL config was created
    base_url_config = db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key == "ai_default_openai_base_url"
        )
    ).first()

    assert base_url_config is not None
    assert base_url_config.config_key == "ai_default_openai_base_url"
    assert base_url_config.description is not None
    assert base_url_config.is_active is True

    # Verify API key config was created
    api_key_config = db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key == "ai_default_openai_api_key_encrypted"
        )
    ).first()

    assert api_key_config is not None
    assert api_key_config.config_key == "ai_default_openai_api_key_encrypted"
    assert api_key_config.config_value == ""  # Should be empty by default
    assert api_key_config.description is not None
    assert api_key_config.is_active is True


def test_seed_ai_default_config_idempotent(db: Session) -> None:
    """Test that _seed_ai_default_config doesn't create duplicates on re-run."""
    # Clear any existing AI configs
    statement = delete(AppConfiguration)
    db.execute(statement)
    db.commit()

    # Run seed function first time
    _seed_ai_default_config(db)
    count_first = len(
        db.exec(
            select(AppConfiguration).where(
                AppConfiguration.config_key.in_(
                    [
                        "ai_default_openai_base_url",
                        "ai_default_openai_api_key_encrypted",
                    ]
                )
            )
        ).all()
    )

    # Run seed function second time
    _seed_ai_default_config(db)
    count_second = len(
        db.exec(
            select(AppConfiguration).where(
                AppConfiguration.config_key.in_(
                    [
                        "ai_default_openai_base_url",
                        "ai_default_openai_api_key_encrypted",
                    ]
                )
            )
        ).all()
    )

    assert count_second == count_first, "Should not create duplicate configs"
    assert count_first == 2, "Should have exactly 2 config entries"


def test_seed_ai_default_config_base_url_from_env(db: Session) -> None:
    """Test that _seed_ai_default_config uses environment variable for base URL if set."""
    # Clear any existing AI configs
    statement = delete(AppConfiguration)
    db.execute(statement)
    db.commit()

    # Set environment variable
    with patch.dict(
        os.environ, {"AI_DEFAULT_OPENAI_BASE_URL": "https://custom.api.com/v1"}
    ):
        # Patch settings to read from environment
        with patch("app.core.seeds.settings") as mock_settings:
            mock_settings.AI_DEFAULT_OPENAI_BASE_URL = "https://custom.api.com/v1"

            # Run seed function
            _seed_ai_default_config(db)

            # Verify base URL config was created with value from env
            base_url_config = db.exec(
                select(AppConfiguration).where(
                    AppConfiguration.config_key == "ai_default_openai_base_url"
                )
            ).first()

            assert base_url_config is not None
            assert base_url_config.config_value == "https://custom.api.com/v1"


def test_seed_ai_default_config_empty_base_url(db: Session) -> None:
    """Test that _seed_ai_default_config creates empty base URL if env var not set."""
    # Clear any existing AI configs
    statement = delete(AppConfiguration)
    db.execute(statement)
    db.commit()

    # Ensure environment variable is not set
    with patch.dict(os.environ, {}, clear=False):
        if "AI_DEFAULT_OPENAI_BASE_URL" in os.environ:
            del os.environ["AI_DEFAULT_OPENAI_BASE_URL"]

        # Patch settings to return None for base URL
        with patch("app.core.seeds.settings") as mock_settings:
            mock_settings.AI_DEFAULT_OPENAI_BASE_URL = None

            # Run seed function
            _seed_ai_default_config(db)

            # Verify base URL config was created with empty value
            base_url_config = db.exec(
                select(AppConfiguration).where(
                    AppConfiguration.config_key == "ai_default_openai_base_url"
                )
            ).first()

            assert base_url_config is not None
            assert base_url_config.config_value == ""  # Should be empty


def test_seed_ai_default_config_api_key_empty(db: Session) -> None:
    """Test that _seed_ai_default_config creates empty API key (users must configure)."""
    # Clear any existing AI configs
    statement = delete(AppConfiguration)
    db.execute(statement)
    db.commit()

    # Run seed function
    _seed_ai_default_config(db)

    # Verify API key config was created with empty value
    api_key_config = db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key == "ai_default_openai_api_key_encrypted"
        )
    ).first()

    assert api_key_config is not None
    assert api_key_config.config_value == "", "API key should be empty by default"
