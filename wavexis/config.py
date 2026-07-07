"""Dataclasses for wavexis configuration and parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PAPER_SIZES: dict[str, dict[str, float]] = {
    "a4": {"width": 8.27, "height": 11.69},
    "letter": {"width": 8.5, "height": 11.0},
    "legal": {"width": 8.5, "height": 14.0},
    "a3": {"width": 11.69, "height": 16.54},
    "a5": {"width": 5.83, "height": 8.27},
}

WAIT_PRESETS: dict[str, int] = {
    "fast": 1000,
    "normal": 3000,
    "slow": 10000,
}

THROTTLE_PRESETS: dict[str, dict[str, Any]] = {
    "none": {
        "offline": False,
        "download_throughput": 0,
        "upload_throughput": 0,
        "latency_ms": 0,
    },
    "2g": {
        "offline": False,
        "download_throughput": 28000,
        "upload_throughput": 25600,
        "latency_ms": 400,
    },
    "3g": {
        "offline": False,
        "download_throughput": 160000,
        "upload_throughput": 75000,
        "latency_ms": 150,
    },
    "4g": {
        "offline": False,
        "download_throughput": 4000000,
        "upload_throughput": 3000000,
        "latency_ms": 20,
    },
}

DEVICE_PRESETS: dict[str, dict[str, Any]] = {
    "iphone-15": {
        "width": 393,
        "height": 852,
        "device_scale_factor": 3,
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        ),
        "touch": True,
        "mobile": True,
    },
    "iphone-se": {
        "width": 375,
        "height": 667,
        "device_scale_factor": 2,
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Mobile/15E148 Safari/604.1"
        ),
        "touch": True,
        "mobile": True,
    },
    "pixel-8": {
        "width": 412,
        "height": 915,
        "device_scale_factor": 2.625,
        "user_agent": (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Mobile Safari/537.36"
        ),
        "touch": True,
        "mobile": True,
    },
    "ipad-pro": {
        "width": 834,
        "height": 1194,
        "device_scale_factor": 2,
        "user_agent": (
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        ),
        "touch": True,
        "mobile": False,
    },
    "galaxy-s23": {
        "width": 360,
        "height": 780,
        "device_scale_factor": 3,
        "user_agent": (
            "Mozilla/5.0 (Linux; Android 14; SM-S911B) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Mobile Safari/537.36"
        ),
        "touch": True,
        "mobile": True,
    },
    "desktop-1080p": {
        "width": 1920,
        "height": 1080,
        "device_scale_factor": 1,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        ),
        "touch": False,
        "mobile": False,
    },
    "desktop-1440p": {
        "width": 2560,
        "height": 1440,
        "device_scale_factor": 1,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        ),
        "touch": False,
        "mobile": False,
    },
}


@dataclass
class BrowserOptions:
    """Options for launching a browser instance.

    Attributes:
        headless: Run browser in headless mode.
        width: Browser window width in pixels.
        height: Browser window height in pixels.
        user_agent: Custom User-Agent string.
        extra_headers: Extra HTTP headers to send with every request.
        proxy: Proxy server URL (e.g. http://proxy:8080 or socks5://proxy:1080).
        timeout: Default navigation timeout in milliseconds.
        user_data_dir: Path to a persistent user data directory for browser profiles.
    """

    headless: bool = True
    width: int = 1280
    height: int = 800
    user_agent: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    proxy: str | None = None
    timeout: int = 30000
    user_data_dir: str | None = None


@dataclass
class WaitStrategy:
    """Strategy for waiting after navigation.

    Attributes:
        strategy: Wait type — "load", "domcontentloaded", "networkidle",
            "selector", or "url".
        selector: CSS selector to wait for (required when strategy="selector").
        url_pattern: URL substring to wait for (required when strategy="url").
        timeout: Maximum wait time in milliseconds.
    """

    strategy: str = "load"
    selector: str | None = None
    url_pattern: str | None = None
    timeout: int = 30000

    @classmethod
    def from_url(cls, url: str) -> WaitStrategy:
        """Create a load wait strategy from a URL.

        Args:
            url: The URL to navigate to (used for context only).

        Returns:
            A WaitStrategy with strategy="load".
        """
        return cls(strategy="load")


@dataclass
class ScreenshotParams:
    """Parameters for taking a screenshot."""

    url: str
    full_page: bool = True
    format: str = "png"
    quality: int = 80
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    js: str | None = None
    selector: str | None = None
    device: str | None = None
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class PDFParams:
    """Parameters for generating a PDF.

    Attributes:
        url: URL to navigate to before generating the PDF.
        paper: Paper size name (a4, letter, legal, a3, a5).
        landscape: Use landscape orientation.
        margin: Margin string (e.g. "0.4in").
        no_header_footer: Omit header and footer.
        media: CSS media type to emulate ("print" or "screen").
        wait: Wait strategy after navigation.
        js: Optional JavaScript to execute before PDF generation.
        browser: Browser launch options.
    """

    url: str
    paper: str = "letter"
    landscape: bool = False
    margin: str = "0.4in"
    no_header_footer: bool = False
    media: str = "print"
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    js: str | None = None
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class EvalParams:
    """Parameters for evaluating a JavaScript expression.

    Attributes:
        url: URL to navigate to before evaluation.
        expression: JavaScript expression to evaluate.
        await_promise: Whether to await a returned Promise.
        file: Path to a file containing the expression (prefixed with @).
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str
    expression: str = ""
    await_promise: bool = False
    file: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class DOMParams:
    """Parameters for DOM operations.

    Attributes:
        url: URL to navigate to before DOM operation.
        action: DOM action — "get", "query", "attr", "remove", "focus", "scroll".
        selector: CSS selector for the target element.
        outer: Use outerHTML (True) or innerHTML (False) for "get" action.
        all: Query all matching elements (True) or first only (False).
        attribute: Attribute name for get/set/remove attr actions.
        value: Attribute value for set attr action.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "get"
    selector: str = ""
    outer: bool = True
    all: bool = False
    attribute: str | None = None
    value: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class ScrapeParams:
    """Parameters for scraping multiple URLs.

    Attributes:
        urls: List of URLs to scrape.
        expression: JavaScript expression to evaluate on each page.
        file: Path to a file containing the expression (prefixed with @).
        output_format: Output format — "json" or "csv".
        selector: Optional CSS selector to wait for on each page.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    urls: list[str] = field(default_factory=list)
    expression: str = ""
    file: str | None = None
    output_format: str = "json"
    selector: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class HarParams:
    """Parameters for HAR capture.

    Attributes:
        url: URL to navigate to for HAR capture.
        wait: Time to wait after navigation in milliseconds.
        filter: Optional URL filter pattern to include only matching entries.
        timeout: Maximum capture timeout in milliseconds.
        browser: Browser launch options.
    """

    url: str = ""
    wait: int = 3000
    filter: str | None = None
    timeout: int = 30000
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class CookieParams:
    """Parameters for setting a cookie.

    Attributes:
        name: Cookie name.
        value: Cookie value.
        domain: Cookie domain.
        path: Cookie path.
        secure: Whether cookie is secure-only.
        http_only: Whether cookie is HTTP-only.
        same_site: SameSite attribute — "Lax", "Strict", or "None".
    """

    name: str = ""
    value: str = ""
    domain: str = ""
    path: str = "/"
    secure: bool = True
    http_only: bool = False
    same_site: str = "Lax"


@dataclass
class NetworkParams:
    """Parameters for network operations.

    Attributes:
        url: URL to navigate to (for cookies get).
        action: Network action — "cookies_get", "cookies_set", "cookies_delete",
            "cookies_clear", "headers", "user_agent".
        headers: Dict of HTTP headers to set.
        user_agent: User-Agent string to set.
        cookies: List of cookie dicts to set.
        cookie: Single CookieParams for set/delete.
        name: Cookie name for delete.
        domain: Cookie domain for delete.
        browser: Browser launch options.
    """

    url: str | None = None
    action: str = "cookies_get"
    headers: dict[str, str] | None = None
    user_agent: str | None = None
    cookies: list[dict[str, str]] | None = None
    cookie: CookieParams | None = None
    name: str | None = None
    domain: str | None = None
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class EmulationParams:
    """Parameters for emulation operations.

    Attributes:
        action: Emulation action — 'device', 'viewport', 'geolocation',
            'timezone', 'dark_mode'.
        device: Device preset name for 'device' action.
        width: Viewport width for 'viewport' action.
        height: Viewport height for 'viewport' action.
        device_scale_factor: Device pixel scale factor for 'viewport' action.
        latitude: Latitude for 'geolocation' action.
        longitude: Longitude for 'geolocation' action.
        accuracy: Accuracy in meters for 'geolocation' action.
        timezone: IANA timezone ID for 'timezone' action.
        dark_mode: Enable dark mode for 'dark_mode' action.
        url: URL to navigate to before emulation (optional).
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    action: str = "device"
    device: str | None = None
    width: int = 0
    height: int = 0
    device_scale_factor: float = 1.0
    latitude: float = 0.0
    longitude: float = 0.0
    accuracy: float = 100.0
    timezone: str = ""
    dark_mode: bool = False
    url: str = ""
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class InputParams:
    """Parameters for input interactions.

    Attributes:
        url: URL to navigate to before the input action.
        selector: CSS selector for the target element.
        action: Input action — "click", "type", "fill", "select", "hover",
            "key", "drag", "tap", "scroll", "upload".
        text: Text to type (for "type" action).
        value: Value to fill or select (for "fill" and "select" actions).
        key: Key to press (for "key" action, e.g. "Enter", "Tab").
        button: Mouse button for click — "left", "right", "middle".
        click_count: Number of clicks for click action.
        delay: Delay between keystrokes in milliseconds (for "type" action).
        source: Source CSS selector for "drag" action.
        target: Target CSS selector for "drag" action.
        scroll_x: Horizontal scroll offset (for "scroll" action).
        scroll_y: Vertical scroll offset (for "scroll" action).
        files: List of file paths to upload (for "upload" action).
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    selector: str = ""
    action: str = "click"
    text: str | None = None
    value: str | None = None
    key: str | None = None
    button: str = "left"
    click_count: int = 1
    delay: int = 0
    source: str | None = None
    target: str | None = None
    scroll_x: int = 0
    scroll_y: int = 0
    files: list[str] | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class ThrottleParams:
    """Parameters for network throttling.

    Attributes:
        offline: If True, emulate network offline state.
        latency_ms: Emulated latency in milliseconds.
        download_bps: Max download throughput in bytes/sec (-1 for unlimited).
        upload_bps: Max upload throughput in bytes/sec (-1 for unlimited).
    """

    offline: bool = False
    latency_ms: int = 0
    download_bps: int = -1
    upload_bps: int = -1


@dataclass
class SensorParams:
    """Parameters for sensor emulation.

    Attributes:
        type: Sensor type — "geolocation", "device-orientation", "ambient-light".
        values: Dict of sensor-specific values (e.g. latitude, longitude, accuracy).
    """

    type: str = ""
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreencastParams:
    """Parameters for capturing a screencast.

    Attributes:
        url: URL to navigate to before screencast.
        format: Image format for each frame ("png" or "jpeg").
        quality: JPEG quality (0-100).
        max_width: Max frame width in pixels.
        max_height: Max frame height in pixels.
        duration: Maximum capture duration in seconds.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    format: str = "png"
    quality: int = 80
    max_width: int = 1280
    max_height: int = 800
    duration: float = 5.0
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class StorageParams:
    """Parameters for storage operations.

    Attributes:
        url: URL to navigate to before storage operations.
        key: Storage key for get/set actions.
        value: Value for set action.
        storage_type: "local" or "session" for DOM storage.
        cache_name: Cache name for cache storage actions.
        database: IndexedDB database name.
        store: IndexedDB object store name.
        action: Storage action — "get", "set", "clear", "list",
            "cache-list", "cache-entries", "cache-delete",
            "indexeddb-list", "indexeddb-get", "indexeddb-clear".
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    key: str | None = None
    value: str | None = None
    storage_type: str = "local"
    cache_name: str | None = None
    database: str | None = None
    store: str | None = None
    action: str = "get"
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class AnimationParams:
    """Parameters for animation operations.

    Attributes:
        url: URL to navigate to before animation operations.
        animation_id: Animation ID for pause/play/seek actions.
        time_ms: Target time in milliseconds for seek action.
        action: Animation action — "list", "pause", "play", "seek".
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    animation_id: str | None = None
    time_ms: int | None = None
    action: str = "list"
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class CSSParams:
    """Parameters for CSS inspection operations.

    Attributes:
        url: URL to navigate to before CSS inspection.
        selector: CSS selector for the target element.
        node_id: Node ID (alternative to selector).
        stylesheet_id: Stylesheet ID for rules action.
        action: CSS action — "styles", "stylesheets", "rules", "computed".
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    selector: str | None = None
    node_id: str | None = None
    stylesheet_id: str | None = None
    action: str = "styles"
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class DebugParams:
    """Parameters for debugging operations.

    Attributes:
        url: URL to navigate to before debugging (optional for step/pause/resume).
        line: Line number for breakpoint (0-based).
        function_name: Function name for function breakpoint.
        condition: Optional condition expression for breakpoint.
        action: Debug action — "breakpoint", "function_breakpoint",
            "remove_breakpoint", "step_over", "step_into", "step_out",
            "pause", "resume", "listeners".
        breakpoint_id: Breakpoint ID for remove_breakpoint.
        selector: CSS selector for listeners action.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str | None = None
    line: int | None = None
    function_name: str | None = None
    condition: str | None = None
    action: str = "breakpoint"
    breakpoint_id: str | None = None
    selector: str | None = None
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class CookieActionParams:
    """Parameters for cookie operations.

    Attributes:
        url: URL to navigate to before cookie operations.
        action: Cookie action — "get", "set", "delete", "clear".
        cookie: Cookie parameters for set action.
        name: Cookie name for delete action.
        domain: Cookie domain for delete action.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "get"
    cookie: CookieParams = field(default_factory=CookieParams)
    name: str = ""
    domain: str = ""
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)


@dataclass
class HeaderParams:
    """Parameters for header and user-agent operations.

    Attributes:
        url: URL to navigate to before setting headers.
        action: Header action — "set-headers", "set-user-agent".
        headers: Extra HTTP headers for set-headers action.
        user_agent: User-Agent string for set-user-agent action.
        wait: Wait strategy after navigation.
        browser: Browser launch options.
    """

    url: str = ""
    action: str = "set-headers"
    headers: dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
    wait: WaitStrategy = field(default_factory=WaitStrategy)
    browser: BrowserOptions = field(default_factory=BrowserOptions)
