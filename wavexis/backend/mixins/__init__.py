"""Protocol mixins for AbstractBackend.

Each mixin defines the abstract interface for a specific domain
(navigation, DOM, network, etc.). ``AbstractBackend`` composes them
all into a single unified interface.
"""

from wavexis.backend.mixins.accessibility import AccessibilityBackend
from wavexis.backend.mixins.animation import AnimationBackend
from wavexis.backend.mixins.css import CSSBackend
from wavexis.backend.mixins.debug import DebugBackend
from wavexis.backend.mixins.dialog import DialogBackend
from wavexis.backend.mixins.dom import DOMBackend
from wavexis.backend.mixins.emulation import EmulationBackend
from wavexis.backend.mixins.events import EventsBackend
from wavexis.backend.mixins.experimental import ExperimentalBackend
from wavexis.backend.mixins.input import InputBackend
from wavexis.backend.mixins.navigation import NavigationBackend
from wavexis.backend.mixins.network import NetworkBackend
from wavexis.backend.mixins.performance import PerformanceBackend
from wavexis.backend.mixins.screenshot import ScreenshotBackend
from wavexis.backend.mixins.service_worker import ServiceWorkerBackend
from wavexis.backend.mixins.storage import StorageBackend

__all__ = [
    "AccessibilityBackend",
    "AnimationBackend",
    "CSSBackend",
    "DebugBackend",
    "DialogBackend",
    "DOMBackend",
    "EmulationBackend",
    "EventsBackend",
    "ExperimentalBackend",
    "InputBackend",
    "NavigationBackend",
    "NetworkBackend",
    "PerformanceBackend",
    "ScreenshotBackend",
    "ServiceWorkerBackend",
    "StorageBackend",
]
