"""Unit tests for config dataclasses."""

from wavexis.config import (
    DEVICE_PRESETS,
    PAPER_SIZES,
    BrowserOptions,
    CookieParams,
    DOMParams,
    EvalParams,
    HarParams,
    NetworkParams,
    PDFParams,
    ScrapeParams,
    ScreencastParams,
    ScreenshotParams,
    WaitStrategy,
)


class TestBrowserOptions:
    """Tests for BrowserOptions dataclass."""

    def test_defaults(self):
        """Test defaults."""
        opts = BrowserOptions()
        assert opts.headless is True
        assert opts.width == 1280
        assert opts.height == 800
        assert opts.user_agent is None
        assert opts.extra_headers == {}

    def test_custom(self):
        """Test custom."""
        opts = BrowserOptions(headless=False, width=1920, height=1080)
        assert opts.headless is False
        assert opts.width == 1920
        assert opts.height == 1080


class TestWaitStrategy:
    """Tests for WaitStrategy dataclass."""

    def test_defaults(self):
        """Test defaults."""
        ws = WaitStrategy()
        assert ws.strategy == "load"
        assert ws.selector is None
        assert ws.url_pattern is None
        assert ws.timeout == 30000

    def test_custom(self):
        """Test custom."""
        ws = WaitStrategy(strategy="selector", selector="#app", timeout=5000)
        assert ws.strategy == "selector"
        assert ws.selector == "#app"
        assert ws.timeout == 5000

    def test_from_url(self):
        """Test from url."""
        ws = WaitStrategy.from_url("https://example.com")
        assert ws.strategy == "load"


class TestScreenshotParams:
    """Tests for ScreenshotParams dataclass."""

    def test_defaults(self):
        """Test defaults."""
        params = ScreenshotParams(url="https://example.com")
        assert params.url == "https://example.com"
        assert params.full_page is True
        assert params.format == "png"
        assert params.quality == 80
        assert params.js is None
        assert params.selector is None
        assert params.device is None
        assert isinstance(params.wait, WaitStrategy)
        assert isinstance(params.browser, BrowserOptions)

    def test_custom(self):
        """Test custom."""
        params = ScreenshotParams(
            url="https://example.com",
            full_page=False,
            format="jpeg",
            quality=50,
            selector="#hero",
            device="iphone-15",
        )
        assert params.full_page is False
        assert params.format == "jpeg"
        assert params.quality == 50
        assert params.selector == "#hero"
        assert params.device == "iphone-15"


class TestPDFParams:
    """Tests for PDFParams dataclass."""

    def test_defaults(self):
        """Test defaults."""
        params = PDFParams(url="https://example.com")
        assert params.url == "https://example.com"
        assert params.paper == "letter"
        assert params.landscape is False
        assert params.margin == "0.4in"
        assert params.no_header_footer is False
        assert params.media == "print"
        assert params.js is None
        assert isinstance(params.wait, WaitStrategy)
        assert isinstance(params.browser, BrowserOptions)

    def test_custom(self):
        """Test custom."""
        params = PDFParams(
            url="https://example.com",
            paper="a4",
            landscape=True,
            margin="0.5in",
            no_header_footer=True,
            media="screen",
        )
        assert params.paper == "a4"
        assert params.landscape is True
        assert params.margin == "0.5in"
        assert params.no_header_footer is True
        assert params.media == "screen"


class TestEvalParams:
    """Tests for EvalParams dataclass."""

    def test_defaults(self):
        """Test defaults."""
        params = EvalParams(url="https://example.com")
        assert params.url == "https://example.com"
        assert params.expression == ""
        assert params.await_promise is False
        assert params.file is None
        assert isinstance(params.wait, WaitStrategy)
        assert isinstance(params.browser, BrowserOptions)

    def test_custom(self):
        """Test custom."""
        params = EvalParams(
            url="https://example.com",
            expression="document.title",
            await_promise=True,
            file="script.js",
        )
        assert params.expression == "document.title"
        assert params.await_promise is True
        assert params.file == "script.js"


class TestScreencastParams:
    """Tests for ScreencastParams dataclass."""

    def test_defaults(self):
        """Test defaults."""
        params = ScreencastParams(url="https://example.com")
        assert params.url == "https://example.com"
        assert params.format == "png"
        assert params.quality == 80
        assert params.duration == 5.0
        assert isinstance(params.wait, WaitStrategy)


class TestDevicePresets:
    """Tests for DEVICE_PRESETS dict."""

    def test_all_presets_present(self):
        """Test all presets present."""
        expected = {
            "iphone-15", "iphone-se", "pixel-8", "ipad-pro",
            "galaxy-s23", "desktop-1080p", "desktop-1440p",
        }
        assert set(DEVICE_PRESETS.keys()) == expected

    def test_preset_has_required_keys(self):
        """Test preset has required keys."""
        for name, preset in DEVICE_PRESETS.items():
            assert "width" in preset, f"{name} missing width"
            assert "height" in preset, f"{name} missing height"
            assert "device_scale_factor" in preset, f"{name} missing device_scale_factor"
            assert "user_agent" in preset, f"{name} missing user_agent"
            assert "touch" in preset, f"{name} missing touch"
            assert "mobile" in preset, f"{name} missing mobile"

    def test_iphone_15_values(self):
        """Test iphone 15 values."""
        p = DEVICE_PRESETS["iphone-15"]
        assert p["width"] == 393
        assert p["height"] == 852
        assert p["device_scale_factor"] == 3
        assert p["touch"] is True
        assert p["mobile"] is True


class TestPaperSizes:
    """Tests for PAPER_SIZES dict."""

    def test_all_sizes_present(self):
        """Test all sizes present."""
        expected = {"a4", "letter", "legal", "a3", "a5"}
        assert set(PAPER_SIZES.keys()) == expected

    def test_size_has_width_height(self):
        """Test size has width height."""
        for name, dims in PAPER_SIZES.items():
            assert "width" in dims, f"{name} missing width"
            assert "height" in dims, f"{name} missing height"

    def test_letter_values(self):
        """Test letter values."""
        assert PAPER_SIZES["letter"]["width"] == 8.5
        assert PAPER_SIZES["letter"]["height"] == 11.0

    def test_a4_values(self):
        """Test a4 values."""
        assert PAPER_SIZES["a4"]["width"] == 8.27
        assert PAPER_SIZES["a4"]["height"] == 11.69


class TestDOMParams:
    """Tests for DOMParams dataclass."""

    def test_defaults(self):
        """Test defaults."""
        params = DOMParams()
        assert params.action == "get"
        assert params.selector == ""
        assert params.outer is True
        assert params.all is False

    def test_with_values(self):
        """Test with values."""
        params = DOMParams(
            url="https://example.com",
            action="query",
            selector="#main",
            all=True,
        )
        assert params.url == "https://example.com"
        assert params.action == "query"
        assert params.all is True


class TestScrapeParams:
    """Tests for ScrapeParams dataclass."""

    def test_defaults(self):
        """Test defaults."""
        params = ScrapeParams()
        assert params.urls == []
        assert params.expression == ""
        assert params.output_format == "json"

    def test_with_urls(self):
        """Test with urls."""
        params = ScrapeParams(
            urls=["https://a.com", "https://b.com"],
            expression="document.title",
        )
        assert len(params.urls) == 2
        assert params.expression == "document.title"


class TestHarParams:
    """Tests for HarParams dataclass."""

    def test_defaults(self):
        """Test defaults."""
        params = HarParams()
        assert params.wait == 3000
        assert params.filter is None
        assert params.timeout == 30000

    def test_with_filter(self):
        """Test with filter."""
        params = HarParams(url="https://example.com", filter="api.example.com")
        assert params.filter == "api.example.com"


class TestCookieParams:
    """Tests for CookieParams dataclass."""

    def test_defaults(self):
        """Test defaults."""
        params = CookieParams()
        assert params.name == ""
        assert params.path == "/"
        assert params.secure is True
        assert params.http_only is False
        assert params.same_site == "Lax"

    def test_with_values(self):
        """Test with values."""
        params = CookieParams(
            name="session", value="abc123", domain=".example.com"
        )
        assert params.name == "session"
        assert params.domain == ".example.com"


class TestNetworkParams:
    """Tests for NetworkParams dataclass."""

    def test_defaults(self):
        """Test defaults."""
        params = NetworkParams()
        assert params.action == "cookies_get"
        assert params.headers is None
        assert params.user_agent is None

    def test_with_headers(self):
        """Test with headers."""
        params = NetworkParams(
            action="headers", headers={"X-Test": "val"}
        )
        assert params.headers == {"X-Test": "val"}
