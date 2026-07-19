"""Protocol mixins for AbstractBackend.

Each mixin defines the abstract interface for a specific domain
(navigation, DOM, network, etc.). ``AbstractBackend`` composes them
all into a single unified interface.
"""

from wavexis.backend.mixins.accessibility import AccessibilityBackend
from wavexis.backend.mixins.animation import AnimationBackend
from wavexis.backend.mixins.console import ConsoleBackend
from wavexis.backend.mixins.crash_report_context import CrashReportContextBackend
from wavexis.backend.mixins.css import CSSBackend
from wavexis.backend.mixins.debug import DebugBackend
from wavexis.backend.mixins.device_access import DeviceAccessBackend
from wavexis.backend.mixins.device_orientation import DeviceOrientationBackend
from wavexis.backend.mixins.dialog import DialogBackend
from wavexis.backend.mixins.digital_credentials import DigitalCredentialsBackend
from wavexis.backend.mixins.dom import DOMBackend
from wavexis.backend.mixins.dom_debugger import DOMDebuggerBackend
from wavexis.backend.mixins.dom_snapshot import DOMSnapshotBackend
from wavexis.backend.mixins.dom_storage import DOMStorageBackend
from wavexis.backend.mixins.emulation import EmulationBackend
from wavexis.backend.mixins.event_breakpoints import EventBreakpointsBackend
from wavexis.backend.mixins.events import EventsBackend
from wavexis.backend.mixins.experimental import ExperimentalBackend
from wavexis.backend.mixins.extensions import ExtensionsBackend
from wavexis.backend.mixins.fed_cm import FedCmBackend
from wavexis.backend.mixins.fetch import FetchBackend
from wavexis.backend.mixins.file_system import FileSystemBackend
from wavexis.backend.mixins.headless_experimental import HeadlessExperimentalBackend
from wavexis.backend.mixins.heap_profiler import HeapProfilerBackend
from wavexis.backend.mixins.indexed_db import IndexedDBBackend
from wavexis.backend.mixins.input import InputBackend
from wavexis.backend.mixins.input_domain import InputDomainBackend
from wavexis.backend.mixins.inspector import InspectorBackend
from wavexis.backend.mixins.io import IOBackend
from wavexis.backend.mixins.layer_tree import LayerTreeBackend
from wavexis.backend.mixins.log import LogBackend
from wavexis.backend.mixins.media import MediaBackend
from wavexis.backend.mixins.memory import MemoryBackend
from wavexis.backend.mixins.navigation import NavigationBackend
from wavexis.backend.mixins.network import NetworkBackend
from wavexis.backend.mixins.network_domain import NetworkDomainBackend
from wavexis.backend.mixins.overlay import OverlayBackend
from wavexis.backend.mixins.page import PageBackend
from wavexis.backend.mixins.performance import PerformanceBackend
from wavexis.backend.mixins.performance_timeline import PerformanceTimelineBackend
from wavexis.backend.mixins.preload import PreloadBackend
from wavexis.backend.mixins.profiler import ProfilerBackend
from wavexis.backend.mixins.pwa import PwaBackend
from wavexis.backend.mixins.runtime import RuntimeBackend
from wavexis.backend.mixins.schema import SchemaBackend
from wavexis.backend.mixins.screenshot import ScreenshotBackend
from wavexis.backend.mixins.security import SecurityBackend
from wavexis.backend.mixins.sensor import SensorBackend
from wavexis.backend.mixins.service_worker import ServiceWorkerBackend
from wavexis.backend.mixins.smart_card_emulation import SmartCardEmulationBackend
from wavexis.backend.mixins.storage import StorageBackend
from wavexis.backend.mixins.system_info import SystemInfoBackend
from wavexis.backend.mixins.target import TargetBackend

__all__ = [
    "AccessibilityBackend",
    "AnimationBackend",
    "CSSBackend",
    "ConsoleBackend",
    "CrashReportContextBackend",
    "DebugBackend",
    "DeviceAccessBackend",
    "DeviceOrientationBackend",
    "DigitalCredentialsBackend",
    "DialogBackend",
    "DOMBackend",
    "DOMDebuggerBackend",
    "DOMSnapshotBackend",
    "DOMStorageBackend",
    "EmulationBackend",
    "EventsBackend",
    "EventBreakpointsBackend",
    "ExperimentalBackend",
    "ExtensionsBackend",
    "FedCmBackend",
    "FetchBackend",
    "FileSystemBackend",
    "HeadlessExperimentalBackend",
    "HeapProfilerBackend",
    "IndexedDBBackend",
    "InputDomainBackend",
    "InspectorBackend",
    "IOBackend",
    "InputBackend",
    "LayerTreeBackend",
    "LogBackend",
    "MediaBackend",
    "MemoryBackend",
    "NetworkDomainBackend",
    "NavigationBackend",
    "NetworkBackend",
    "OverlayBackend",
    "PageBackend",
    "PreloadBackend",
    "ProfilerBackend",
    "PwaBackend",
    "PerformanceBackend",
    "PerformanceTimelineBackend",
    "RuntimeBackend",
    "SchemaBackend",
    "SecurityBackend",
    "SensorBackend",
    "ScreenshotBackend",
    "ServiceWorkerBackend",
    "SmartCardEmulationBackend",
    "StorageBackend",
    "SystemInfoBackend",
    "TargetBackend",
]
