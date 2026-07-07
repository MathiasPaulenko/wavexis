"""Abstract backend interface for browser automation.

``AbstractBackend`` is composed from domain-specific protocol mixins
defined in :mod:`wavexis.backend.mixins`.  Each mixin covers a single
concern (navigation, DOM, network, etc.) so that the 1 000+ line
monolith is split into manageable, focused pieces.

Backwards compatibility: ``AbstractBackend`` still lives in this
module and exposes every method it did before the split.
"""

from __future__ import annotations

from wavexis.backend.mixins import (
    AccessibilityBackend,
    AnimationBackend,
    CSSBackend,
    DebugBackend,
    DialogBackend,
    DOMBackend,
    EmulationBackend,
    EventsBackend,
    ExperimentalBackend,
    InputBackend,
    NavigationBackend,
    NetworkBackend,
    PerformanceBackend,
    ScreenshotBackend,
    ServiceWorkerBackend,
    StorageBackend,
)


class AbstractBackend(
    NavigationBackend,
    ScreenshotBackend,
    DOMBackend,
    InputBackend,
    NetworkBackend,
    EmulationBackend,
    PerformanceBackend,
    DebugBackend,
    CSSBackend,
    StorageBackend,
    EventsBackend,
    AccessibilityBackend,
    DialogBackend,
    ServiceWorkerBackend,
    AnimationBackend,
    ExperimentalBackend,
):
    """Unified abstract interface for browser automation backends.

    Composed from domain-specific mixins:

    - :class:`NavigationBackend` - launch, navigate, tabs, contexts, eval, raw
    - :class:`ScreenshotBackend` - screenshot, PDF, screencast
    - :class:`DOMBackend` - DOM query, mutation, locators, snapshot
    - :class:`InputBackend` - click, type, fill, iframe, shadow DOM
    - :class:`NetworkBackend` - cookies, headers, HAR, interception
    - :class:`EmulationBackend` - device, viewport, geolocation, sensors
    - :class:`PerformanceBackend` - metrics, traces, coverage
    - :class:`DebugBackend` - breakpoints, stepping, pause/resume
    - :class:`CSSBackend` - styles, stylesheets, overlay highlights
    - :class:`StorageBackend` - DOM storage, Cache Storage, IndexedDB
    - :class:`EventsBackend` - event subscription, console, logs
    - :class:`AccessibilityBackend` - a11y tree, axe audit
    - :class:`DialogBackend` - dialogs, security, downloads
    - :class:`ServiceWorkerBackend` - SW list, unregister, update
    - :class:`AnimationBackend` - animation list, pause, play, seek
    - :class:`ExperimentalBackend` - WebAuthn, WebAudio, Media, Cast, BT, extensions

    Implementations include CDPBackend (via cdpwave) and BiDiBackend (via bidiwave).
    """
