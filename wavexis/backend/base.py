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
    ConsoleBackend,
    CrashReportContextBackend,
    CSSBackend,
    DebugBackend,
    DeviceAccessBackend,
    DeviceOrientationBackend,
    DialogBackend,
    DigitalCredentialsBackend,
    DOMBackend,
    DOMDebuggerBackend,
    DOMSnapshotBackend,
    DOMStorageBackend,
    EmulationBackend,
    EventBreakpointsBackend,
    EventsBackend,
    ExperimentalBackend,
    ExtensionsBackend,
    FedCmBackend,
    FetchBackend,
    FileSystemBackend,
    HeadlessExperimentalBackend,
    HeapProfilerBackend,
    IndexedDBBackend,
    InputBackend,
    InputDomainBackend,
    InspectorBackend,
    IOBackend,
    LayerTreeBackend,
    LogBackend,
    MediaBackend,
    MemoryBackend,
    NavigationBackend,
    NetworkBackend,
    NetworkDomainBackend,
    OverlayBackend,
    PageBackend,
    PerformanceBackend,
    PerformanceTimelineBackend,
    PreloadBackend,
    ProfilerBackend,
    PwaBackend,
    RuntimeBackend,
    SchemaBackend,
    ScreenshotBackend,
    SecurityBackend,
    SensorBackend,
    ServiceWorkerBackend,
    SmartCardEmulationBackend,
    StorageBackend,
    SystemInfoBackend,
    TargetBackend,
)


class AbstractBackend(
    NavigationBackend,
    PageBackend,
    PreloadBackend,
    ProfilerBackend,
    PwaBackend,
    SchemaBackend,
    SecurityBackend,
    SensorBackend,
    ScreenshotBackend,
    DOMBackend,
    DOMDebuggerBackend,
    InputBackend,
    NetworkBackend,
    OverlayBackend,
    EmulationBackend,
    PerformanceBackend,
    PerformanceTimelineBackend,
    RuntimeBackend,
    DebugBackend,
    CSSBackend,
    ConsoleBackend,
    CrashReportContextBackend,
    StorageBackend,
    SystemInfoBackend,
    TargetBackend,
    EventsBackend,
    AccessibilityBackend,
    DialogBackend,
    ServiceWorkerBackend,
    SmartCardEmulationBackend,
    AnimationBackend,
    ExperimentalBackend,
    DeviceAccessBackend,
    DeviceOrientationBackend,
    DigitalCredentialsBackend,
    DOMSnapshotBackend,
    DOMStorageBackend,
    EventBreakpointsBackend,
    ExtensionsBackend,
    FedCmBackend,
    FetchBackend,
    FileSystemBackend,
    HeadlessExperimentalBackend,
    HeapProfilerBackend,
    IndexedDBBackend,
    InputDomainBackend,
    InspectorBackend,
    IOBackend,
    LayerTreeBackend,
    LogBackend,
    MediaBackend,
    MemoryBackend,
    NetworkDomainBackend,
):
    """Unified abstract interface for browser automation backends.

        Composed from domain-specific mixins:

        - :class:`NavigationBackend` - launch, navigate, tabs, contexts, eval, raw
        - :class:`PageBackend` - page lifecycle, frame tree, layout metrics, resources
        - :class:`ScreenshotBackend` - screenshot, PDF, screencast
        - :class:`DOMBackend` - DOM query, mutation, locators, snapshot
        - :class:`InputBackend` - click, type, fill, iframe, shadow DOM
        - :class:`NetworkBackend` - cookies, headers, HAR, interception
        - :class:`EmulationBackend` - device, viewport, geolocation, sensors
        - :class:`PerformanceBackend` - metrics, traces, coverage
        - :class:`DebugBackend` - breakpoints, stepping, pause/resume
    - :class:`DOMDebuggerBackend` - DOM breakpoints, event listener breakpoints, XHR breakpoints
        - :class:`CSSBackend` - styles, stylesheets, overlay highlights
        - :class:`StorageBackend` - DOM storage, Cache Storage, IndexedDB
        - :class:`EventsBackend` - event subscription, console, logs
        - :class:`AccessibilityBackend` - a11y tree, axe audit
        - :class:`DialogBackend` - dialogs, security, downloads
        - :class:`ServiceWorkerBackend` - SW list, unregister, update
        - :class:`SmartCardEmulationBackend` - smart card reader emulation
        - :class:`AnimationBackend` - animation list, pause, play, seek
        - :class:`ExperimentalBackend` - WebAuthn, WebAudio, Media, Cast, BT, extensions
        - :class:`SystemInfoBackend` - system info, process info, feature state

        Implementations include CDPBackend (via cdpwave) and BiDiBackend (via bidiwave).
    """
