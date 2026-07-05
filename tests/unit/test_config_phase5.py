"""Unit tests for Phase 5 config dataclasses."""

import pytest

from browsix.config import (
    BrowserOptions,
    InputParams,
    ScreencastParams,
    SensorParams,
    ThrottleParams,
    WaitStrategy,
)


@pytest.mark.unit
class TestInputParams:
    """Test suite for inputparams."""
    def test_defaults(self) -> None:
        """Test defaults."""
        p = InputParams()
        assert p.url == ""
        assert p.selector == ""
        assert p.action == "click"
        assert p.text is None
        assert p.value is None
        assert p.key is None
        assert p.button == "left"
        assert p.click_count == 1
        assert p.delay == 0
        assert p.source is None
        assert p.target is None
        assert isinstance(p.wait, WaitStrategy)
        assert isinstance(p.browser, BrowserOptions)

    def test_custom_values(self) -> None:
        """Test custom values."""
        p = InputParams(
            url="https://example.com",
            selector="#btn",
            action="type",
            text="hello",
            delay=50,
            button="right",
            click_count=3,
        )
        assert p.url == "https://example.com"
        assert p.selector == "#btn"
        assert p.action == "type"
        assert p.text == "hello"
        assert p.delay == 50
        assert p.button == "right"
        assert p.click_count == 3


@pytest.mark.unit
class TestThrottleParams:
    """Test suite for throttleparams."""
    def test_defaults(self) -> None:
        """Test defaults."""
        p = ThrottleParams()
        assert p.offline is False
        assert p.latency_ms == 0
        assert p.download_bps == -1
        assert p.upload_bps == -1

    def test_custom(self) -> None:
        """Test custom."""
        p = ThrottleParams(offline=True, latency_ms=200, download_bps=1000, upload_bps=500)
        assert p.offline is True
        assert p.latency_ms == 200
        assert p.download_bps == 1000
        assert p.upload_bps == 500


@pytest.mark.unit
class TestSensorParams:
    """Test suite for sensorparams."""
    def test_defaults(self) -> None:
        """Test defaults."""
        p = SensorParams()
        assert p.type == ""
        assert p.values == {}

    def test_custom(self) -> None:
        """Test custom."""
        p = SensorParams(type="geolocation", values={"latitude": 37.77, "longitude": -122.41})
        assert p.type == "geolocation"
        assert p.values["latitude"] == 37.77
        assert p.values["longitude"] == -122.41


@pytest.mark.unit
class TestScreencastParams:
    """Test suite for screencastparams."""
    def test_defaults(self) -> None:
        """Test defaults."""
        p = ScreencastParams()
        assert p.url == ""
        assert p.format == "png"
        assert p.quality == 80
        assert p.max_width == 1280
        assert p.max_height == 800
        assert p.duration == 5.0
        assert isinstance(p.wait, WaitStrategy)

    def test_custom(self) -> None:
        """Test custom."""
        p = ScreencastParams(
            url="https://example.com",
            format="jpeg",
            quality=90,
            duration=10.0,
        )
        assert p.url == "https://example.com"
        assert p.format == "jpeg"
        assert p.quality == 90
        assert p.duration == 10.0
