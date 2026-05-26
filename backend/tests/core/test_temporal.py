"""Tests for temporal data formatting utilities.

Tests the format_temporal_range_for_api function which converts
PostgreSQL TSTZRANGE values to display-ready format for API responses.
Also tests the Pydantic validators that convert Range objects to strings.
"""

from datetime import UTC, datetime

from app.core.temporal import format_temporal_range_for_api
from app.models.schemas.temporal_validators import (
    convert_range_to_iso,
    convert_range_to_str,
)


class TestFormatTemporalRangeForApi:
    """Test format_temporal_range_for_api function."""

    def test_unbounded_range(self):
        """Test currently valid range (unbounded upper bound)."""
        # PostgreSQL range with escaped quotes (JSON serialization)
        range_str = '[\\"2026-01-15 10:00:00+00\\",)'
        result = format_temporal_range_for_api(range_str)

        assert result["lower"] == "2026-01-15T10:00:00+00:00"
        assert result["upper"] is None
        assert result["lower_formatted"] == "January 15, 2026"
        assert result["upper_formatted"] == "Present"
        assert result["is_currently_valid"] is True

    def test_bounded_range(self):
        """Test historical range with both bounds."""
        range_str = '[\\"2026-01-15 10:00:00+00\\",\\"2026-02-15 10:00:00+00\\")]'
        result = format_temporal_range_for_api(range_str)

        assert result["lower"] == "2026-01-15T10:00:00+00:00"
        assert result["upper"] == "2026-02-15T10:00:00+00:00"
        assert result["lower_formatted"] == "January 15, 2026"
        assert result["upper_formatted"] == "February 15, 2026"
        assert result["is_currently_valid"] is False

    def test_iso_timestamp_string(self):
        """Test pre-formatted ISO timestamp string (from convert_range_to_iso)."""
        iso_str = "2026-01-15T10:00:00+00:00"
        result = format_temporal_range_for_api(iso_str)

        assert result["lower"] == iso_str
        assert result["upper"] is None
        assert result["lower_formatted"] == "January 15, 2026"
        assert result["upper_formatted"] == "Present"
        assert result["is_currently_valid"] is True

    def test_empty_string(self):
        """Test empty string returns empty range."""
        result = format_temporal_range_for_api("")

        assert result["lower"] is None
        assert result["upper"] is None
        assert result["lower_formatted"] == "Unknown"
        assert result["upper_formatted"] == "Unknown"
        assert result["is_currently_valid"] is False

    def test_none_value(self):
        """Test None value returns empty range."""
        result = format_temporal_range_for_api(None)

        assert result["lower"] is None
        assert result["upper"] is None
        assert result["lower_formatted"] == "Unknown"
        assert result["upper_formatted"] == "Unknown"
        assert result["is_currently_valid"] is False

    def test_range_without_escaped_quotes(self):
        """Test range string without escaped quotes."""
        range_str = "[2026-01-15 10:00:00+00,)"
        result = format_temporal_range_for_api(range_str)

        assert result["lower"] == "2026-01-15T10:00:00+00:00"
        assert result["upper"] is None
        assert result["lower_formatted"] == "January 15, 2026"
        assert result["upper_formatted"] == "Present"
        assert result["is_currently_valid"] is True

    def test_invalid_range_string(self):
        """Test invalid range string returns empty range."""
        result = format_temporal_range_for_api("invalid range")

        assert result["lower"] is None
        assert result["upper"] is None
        assert result["lower_formatted"] == "Unknown"
        assert result["upper_formatted"] == "Unknown"
        assert result["is_currently_valid"] is False

    def test_range_with_infinity(self):
        """Test range with explicit infinity marker."""
        range_str = "[2026-01-15 10:00:00+00,infinity)"
        result = format_temporal_range_for_api(range_str)

        assert result["lower"] == "2026-01-15T10:00:00+00:00"
        assert result["upper"] is None
        assert result["lower_formatted"] == "January 15, 2026"
        assert result["upper_formatted"] == "Present"
        assert result["is_currently_valid"] is True

    def test_future_range(self):
        """Test range starting in the future."""
        range_str = '[\\"2026-12-31 23:59:59+00\\",\\"2027-01-01 00:00:00+00\\")]'
        result = format_temporal_range_for_api(range_str)

        assert result["lower"] == "2026-12-31T23:59:59+00:00"
        assert result["upper"] == "2027-01-01T00:00:00+00:00"
        assert result["lower_formatted"] == "December 31, 2026"
        assert result["upper_formatted"] == "January 01, 2027"
        assert result["is_currently_valid"] is False

    def test_midnight_timestamp(self):
        """Test timestamp at midnight (boundary case)."""
        range_str = '[\\"2026-01-01 00:00:00+00\\",)'
        result = format_temporal_range_for_api(range_str)

        assert result["lower"] == "2026-01-01T00:00:00+00:00"
        assert result["lower_formatted"] == "January 01, 2026"
        assert result["is_currently_valid"] is True

    def test_range_string_from_converter_unbounded(self):
        """Test range string produced by convert_range_to_str (unbounded)."""
        range_str = '["2026-01-15T10:00:00+00:00",)'
        result = format_temporal_range_for_api(range_str)

        assert result["lower"] == "2026-01-15T10:00:00+00:00"
        assert result["upper"] is None
        assert result["is_currently_valid"] is True

    def test_range_string_from_converter_bounded(self):
        """Test range string produced by convert_range_to_str (bounded)."""
        range_str = '["2026-01-15T10:00:00+00:00","2026-02-15T10:00:00+00:00")'
        result = format_temporal_range_for_api(range_str)

        assert result["lower"] == "2026-01-15T10:00:00+00:00"
        assert result["upper"] == "2026-02-15T10:00:00+00:00"
        assert result["upper_formatted"] == "February 15, 2026"
        assert result["is_currently_valid"] is False


class FakeRange:
    """Simulates a PostgreSQL TSTZRANGE object with lower/upper attributes."""

    def __init__(self, lower: datetime | None, upper: datetime | None):
        self.lower = lower
        self.upper = upper


class TestConvertRangeToStr:
    """Test convert_range_to_str preserves full range information."""

    def test_none(self):
        assert convert_range_to_str(None) is None

    def test_string_passthrough(self):
        assert (
            convert_range_to_str("2026-01-15T10:00:00+00:00")
            == "2026-01-15T10:00:00+00:00"
        )

    def test_range_string_passthrough(self):
        assert (
            convert_range_to_str('["2026-01-15T10:00:00+00:00",)')
            == '["2026-01-15T10:00:00+00:00",)'
        )

    def test_unbounded_range_object(self):
        """Range object with no upper bound produces unbounded range string."""
        lower = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
        result = convert_range_to_str(FakeRange(lower, None))

        assert result == '["2026-01-15T10:00:00+00:00",)'
        # Verify format_temporal_range_for_api correctly parses it
        parsed = format_temporal_range_for_api(result)
        assert parsed["is_currently_valid"] is True
        assert parsed["upper"] is None

    def test_bounded_range_object(self):
        """Range object with upper bound preserves both bounds."""
        lower = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
        upper = datetime(2026, 2, 15, 10, 0, tzinfo=UTC)
        result = convert_range_to_str(FakeRange(lower, upper))

        assert result == '["2026-01-15T10:00:00+00:00","2026-02-15T10:00:00+00:00")'
        # Verify format_temporal_range_for_api correctly parses it
        parsed = format_temporal_range_for_api(result)
        assert parsed["is_currently_valid"] is False
        assert parsed["upper"] == "2026-02-15T10:00:00+00:00"
        assert parsed["upper_formatted"] == "February 15, 2026"


class TestConvertRangeToIso:
    """Test convert_range_to_iso produces same format as convert_range_to_str."""

    def test_none(self):
        assert convert_range_to_iso(None) is None

    def test_bounded_range_object(self):
        """After fix, convert_range_to_iso preserves upper bound."""
        lower = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
        upper = datetime(2026, 3, 1, 8, 30, tzinfo=UTC)
        result = convert_range_to_iso(FakeRange(lower, upper))

        assert result == '["2026-01-15T10:00:00+00:00","2026-03-01T08:30:00+00:00")'
        parsed = format_temporal_range_for_api(result)
        assert parsed["is_currently_valid"] is False
        assert parsed["upper"] == "2026-03-01T08:30:00+00:00"

    def test_unbounded_range_object(self):
        """Unbounded range still shows is_currently_valid as True."""
        lower = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
        result = convert_range_to_iso(FakeRange(lower, None))

        assert result == '["2026-05-20T12:00:00+00:00",)'
        parsed = format_temporal_range_for_api(result)
        assert parsed["is_currently_valid"] is True
