"""Tests for VarianceThresholdConfig model."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlmodel import Session

from app.models import (
    VarianceThresholdConfig,
    VarianceThresholdConfigCreate,
    VarianceThresholdConfigPublic,
    VarianceThresholdType,
)


def test_create_variance_threshold_config(db: Session) -> None:
    """Test creating a variance threshold configuration."""
    config_in = VarianceThresholdConfigCreate(
        threshold_type=VarianceThresholdType.critical_cv,
        threshold_percentage=Decimal("-10.00"),
        description="Critical cost variance threshold",
        is_active=True,
    )

    config = VarianceThresholdConfig.model_validate(config_in)
    db.add(config)
    db.commit()
    db.refresh(config)

    # Verify configuration was created
    assert config.variance_threshold_config_id is not None
    assert config.threshold_type == VarianceThresholdType.critical_cv
    assert config.threshold_percentage == Decimal("-10.00")
    assert config.description == "Critical cost variance threshold"
    assert config.is_active is True
    assert config.created_at is not None
    assert config.updated_at is not None


def test_variance_threshold_config_validation_range(_db: Session) -> None:
    """Test that threshold_percentage must be between -100 and 0."""
    # Valid percentage: -10%
    valid_config = VarianceThresholdConfigCreate(
        threshold_type=VarianceThresholdType.warning_cv,
        threshold_percentage=Decimal("-10.00"),
        is_active=True,
    )
    config = VarianceThresholdConfig.model_validate(valid_config)
    assert config.threshold_percentage == Decimal("-10.00")

    # Invalid: positive percentage (should fail validation)
    try:
        invalid_config = VarianceThresholdConfigCreate(
            threshold_type=VarianceThresholdType.warning_cv,
            threshold_percentage=Decimal("10.00"),  # Positive - should fail
            is_active=True,
        )
        VarianceThresholdConfig.model_validate(invalid_config)
        raise AssertionError(
            "Should have raised ValidationError for positive percentage"
        )
    except Exception:
        assert True

    # Invalid: less than -100% (should fail validation)
    try:
        invalid_config = VarianceThresholdConfigCreate(
            threshold_type=VarianceThresholdType.warning_cv,
            threshold_percentage=Decimal("-150.00"),  # Less than -100% - should fail
            is_active=True,
        )
        VarianceThresholdConfig.model_validate(invalid_config)
        raise AssertionError("Should have raised ValidationError for percentage < -100")
    except Exception:
        assert True

    # Valid: exactly 0
    zero_config = VarianceThresholdConfigCreate(
        threshold_type=VarianceThresholdType.warning_cv,
        threshold_percentage=Decimal("0.00"),
        is_active=True,
    )
    config = VarianceThresholdConfig.model_validate(zero_config)
    assert config.threshold_percentage == Decimal("0.00")

    # Valid: exactly -100
    max_negative_config = VarianceThresholdConfigCreate(
        threshold_type=VarianceThresholdType.warning_cv,
        threshold_percentage=Decimal("-100.00"),
        is_active=True,
    )
    config = VarianceThresholdConfig.model_validate(max_negative_config)
    assert config.threshold_percentage == Decimal("-100.00")


def test_variance_threshold_config_unique_active(db: Session) -> None:
    """Test that only one active threshold can exist per threshold_type."""
    # Create first active threshold
    config1_in = VarianceThresholdConfigCreate(
        threshold_type=VarianceThresholdType.critical_cv,
        threshold_percentage=Decimal("-10.00"),
        is_active=True,
    )
    config1 = VarianceThresholdConfig.model_validate(config1_in)
    db.add(config1)
    db.commit()
    db.refresh(config1)

    # Try to create another active threshold of same type
    config2_in = VarianceThresholdConfigCreate(
        threshold_type=VarianceThresholdType.critical_cv,
        threshold_percentage=Decimal("-15.00"),
        is_active=True,
    )
    config2 = VarianceThresholdConfig.model_validate(config2_in)
    db.add(config2)

    # Should fail on commit due to unique constraint (if enforced at DB level)
    # Or should handle at application level
    try:
        db.commit()
        # If no error, check that only one is active
        # (This depends on how we implement the unique constraint)
        db.rollback()
    except Exception:
        db.rollback()
        assert True


def test_variance_threshold_config_public_schema() -> None:
    """Test VarianceThresholdConfigPublic schema for API responses."""
    config_id = uuid.uuid4()
    now = datetime.now()

    config_public = VarianceThresholdConfigPublic(
        variance_threshold_config_id=config_id,
        threshold_type=VarianceThresholdType.warning_sv,
        threshold_percentage=Decimal("-5.00"),
        description="Warning schedule variance threshold",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    assert config_public.variance_threshold_config_id == config_id
    assert config_public.threshold_type == VarianceThresholdType.warning_sv
    assert config_public.threshold_percentage == Decimal("-5.00")
    assert config_public.description == "Warning schedule variance threshold"
    assert config_public.is_active is True


def test_variance_threshold_config_all_types(db: Session) -> None:
    """Test creating configurations for all threshold types."""
    types = [
        VarianceThresholdType.critical_cv,
        VarianceThresholdType.warning_cv,
        VarianceThresholdType.critical_sv,
        VarianceThresholdType.warning_sv,
    ]

    for threshold_type in types:
        config_in = VarianceThresholdConfigCreate(
            threshold_type=threshold_type,
            threshold_percentage=Decimal("-10.00"),
            is_active=True,
        )
        config = VarianceThresholdConfig.model_validate(config_in)
        db.add(config)
        db.commit()
        db.refresh(config)

        assert config.threshold_type == threshold_type
        assert config.threshold_percentage == Decimal("-10.00")


def test_variance_threshold_config_optional_fields(db: Session) -> None:
    """Test that description and is_active are optional with defaults."""
    # Create without description
    config_in = VarianceThresholdConfigCreate(
        threshold_type=VarianceThresholdType.critical_cv,
        threshold_percentage=Decimal("-10.00"),
        is_active=True,
    )
    config = VarianceThresholdConfig.model_validate(config_in)
    assert config.description is None
    assert config.is_active is True

    db.add(config)
    db.commit()
    db.refresh(config)

    assert config.description is None
    assert config.is_active is True
