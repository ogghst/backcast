"""Tests for temporal data formatting utilities.

Tests the format_temporal_range_for_api function which converts
PostgreSQL TSTZRANGE values to display-ready format for API responses.
"""

from app.core.temporal import format_temporal_range_for_api


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
