"""Device emulation and permissions mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from wavexis.config import SensorParams


class EmulationBackend(ABC):
    """Device emulation, viewport, geolocation, sensors, and permissions."""

    @abstractmethod
    async def emulate_device(self, device: str) -> None:
        """Emulate a device by preset name (e.g. 'iphone-15')."""

    @abstractmethod
    async def set_viewport(self, width: int, height: int, device_scale_factor: float = 1.0) -> None:
        """Set a custom viewport with given dimensions and scale factor."""

    @abstractmethod
    async def set_geolocation(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        """Override the geolocation position."""

    @abstractmethod
    async def set_timezone(self, timezone: str) -> None:
        """Override the system timezone (IANA timezone ID)."""

    @abstractmethod
    async def set_dark_mode(self, enabled: bool) -> None:
        """Enable or disable dark mode emulation."""

    @abstractmethod
    async def set_locale(self, locale: str) -> None:
        """Override the browser locale (e.g. 'en-US', 'fr-FR')."""

    @abstractmethod
    async def set_cpu_throttle(self, rate: float) -> None:
        """Throttle CPU performance by a rate multiplier (e.g. 4 = 4x slower)."""

    @abstractmethod
    async def set_touch_emulation(self, enabled: bool) -> None:
        """Enable or disable touch emulation."""

    @abstractmethod
    async def set_sensors(self, sensors: SensorParams) -> None:
        """Override sensor values (geolocation, device orientation, etc.)."""

    @abstractmethod
    async def grant_permission(self, permission: str) -> None:
        """Grant a browser permission (e.g. 'geolocation', 'notifications')."""

    @abstractmethod
    async def reset_permissions(self) -> None:
        """Reset all granted permissions."""

    @abstractmethod
    async def set_device_metrics_override(
        self,
        width: int,
        height: int,
        device_scale_factor: float = 1.0,
        mobile: bool = False,
    ) -> None:
        """Override device metrics (width, height, scale, mobile)."""

    @abstractmethod
    async def clear_device_metrics_override(self) -> None:
        """Clear device metrics override."""

    @abstractmethod
    async def set_emulated_media(self, media: str) -> None:
        """Set the emulated media type (e.g. 'screen', 'print', 'braille')."""

    @abstractmethod
    async def clear_emulated_media(self) -> None:
        """Clear emulated media override."""

    @abstractmethod
    async def set_emulated_vision_deficiency(self, deficiency: str) -> None:
        """Set emulated vision deficiency (e.g. 'none', 'achromatopsia', 'blurredVision')."""

    @abstractmethod
    async def clear_emulated_vision_deficiency(self) -> None:
        """Clear emulated vision deficiency override."""

    @abstractmethod
    async def set_idle_override(
        self, is_user_active: bool = True, is_screen_active: bool = True
    ) -> None:
        """Override the idle state to prevent screen sleep/lock."""

    @abstractmethod
    async def clear_idle_override(self) -> None:
        """Clear the idle state override."""

    @abstractmethod
    async def set_script_execution_disabled(self, disabled: bool = True) -> None:
        """Disable or enable JavaScript script execution."""

    @abstractmethod
    async def set_visible_size(self, width: int, height: int) -> None:
        """Set the visible size of the page (for screenshot clipping)."""

    @abstractmethod
    async def add_screen(self, screen: dict[str, Any]) -> None:
        """Add a virtual screen with the given configuration."""

    @abstractmethod
    async def can_emulate(self) -> bool:
        """Check whether the browser supports emulation."""

    @abstractmethod
    async def clear_auto_dark_mode_override(self) -> None:
        """Clear the auto dark mode override."""

    @abstractmethod
    async def clear_default_background_color_override(self) -> None:
        """Clear the default background color override."""

    @abstractmethod
    async def clear_device_posture_override(self) -> None:
        """Clear the device posture override."""

    @abstractmethod
    async def clear_display_features_override(self) -> None:
        """Clear the display features override."""

    @abstractmethod
    async def clear_geolocation_override(self) -> None:
        """Clear the geolocation override."""

    @abstractmethod
    async def clear_timezone_override(self) -> None:
        """Clear the timezone override."""

    @abstractmethod
    async def get_overridden_sensor_information(self, sensor_type: str) -> dict[str, Any]:
        """Get information about overridden sensors of the given type."""

    @abstractmethod
    async def get_screen_infos(self) -> dict[str, Any]:
        """Get information about all virtual screens."""

    @abstractmethod
    async def remove_screen(self, screen_id: str) -> None:
        """Remove a virtual screen by ID."""

    @abstractmethod
    async def reset_page_scale_factor(self) -> None:
        """Reset the page scale factor to its default."""

    @abstractmethod
    async def set_auto_dark_mode_override(self, enabled: bool) -> None:
        """Enable or disable auto dark mode override."""

    @abstractmethod
    async def set_automation_override(self, enabled: bool) -> None:
        """Enable or disable automation override."""

    @abstractmethod
    async def set_cpu_throttling_rate(self, rate: float) -> None:
        """Set CPU throttling rate as a multiplier (e.g. 4 = 4x slower)."""

    @abstractmethod
    async def set_data_saver_override(self, enabled: bool) -> None:
        """Enable or disable data saver override."""

    @abstractmethod
    async def set_default_background_color_override(self, color: dict[str, Any]) -> None:
        """Override the default background color with the given RGBA color."""

    @abstractmethod
    async def set_device_posture_override(self, posture: str) -> None:
        """Override the device posture (e.g. 'continuous', 'folded')."""

    @abstractmethod
    async def set_disabled_image_types(self, image_types: list[str]) -> None:
        """Disable the given image types from loading."""

    @abstractmethod
    async def set_display_features_override(self, features: list[dict[str, Any]]) -> None:
        """Override display features with the given list."""

    @abstractmethod
    async def set_document_cookie_disabled(self, disabled: bool) -> None:
        """Disable or enable document cookies."""

    @abstractmethod
    async def set_emit_touch_events_for_mouse(
        self, enabled: bool, configuration: dict[str, Any] | None = None
    ) -> None:
        """Enable or disable touch event emulation for mouse input."""

    @abstractmethod
    async def set_emulated_media_feature(self, features: list[dict[str, str]]) -> None:
        """Set emulated media features (e.g. prefers-color-scheme, prefers-reduced-motion)."""

    @abstractmethod
    async def set_emulated_os_text_scale(self, scale: float) -> None:
        """Override the OS text scale factor."""

    @abstractmethod
    async def set_focus_emulation_enabled(self, enabled: bool) -> None:
        """Enable or disable focus emulation."""

    @abstractmethod
    async def set_geolocation_override(
        self, latitude: float, longitude: float, accuracy: float = 100.0
    ) -> None:
        """Override the geolocation position with latitude, longitude, and accuracy."""

    @abstractmethod
    async def set_hardware_concurrency_override(self, concurrency: int) -> None:
        """Override the hardware concurrency (navigator.hardwareConcurrency)."""

    @abstractmethod
    async def set_locale_override(self, locale: str) -> None:
        """Override the browser locale (e.g. 'en-US', 'fr-FR')."""

    @abstractmethod
    async def set_navigator_overrides(self, navigator: dict[str, Any]) -> None:
        """Override navigator properties with the given values."""

    @abstractmethod
    async def set_page_scale_factor(self, factor: float) -> None:
        """Set the page scale factor (zoom level)."""

    @abstractmethod
    async def set_pressure_source_override_enabled(self, source: str, enabled: bool) -> None:
        """Enable or disable pressure source override for the given source type."""

    @abstractmethod
    async def set_pressure_state_override(self, source: str, state: str, value: float) -> None:
        """Override the pressure state for the given source."""

    @abstractmethod
    async def set_primary_screen(self, screen_id: str) -> None:
        """Set the primary screen by ID."""

    @abstractmethod
    async def set_safe_area_insets_override(self, insets: dict[str, Any]) -> None:
        """Override the safe area insets."""

    @abstractmethod
    async def set_scrollbars_hidden(self, hidden: bool) -> None:
        """Hide or show scrollbars."""

    @abstractmethod
    async def set_sensor_override_enabled(self, type: str, enabled: bool) -> None:
        """Enable or disable sensor override for the given sensor type."""

    @abstractmethod
    async def set_sensor_override_readings(self, type: str, readings: list[dict[str, Any]]) -> None:
        """Override sensor readings for the given sensor type."""

    @abstractmethod
    async def set_small_viewport_height_difference_override(self, difference: float) -> None:
        """Override the small viewport height difference."""

    @abstractmethod
    async def set_timezone_override(self, timezone_id: str) -> None:
        """Override the timezone with the given IANA timezone ID."""

    @abstractmethod
    async def set_touch_emulation_enabled(self, enabled: bool, max_touch_points: int = 5) -> None:
        """Enable or disable touch emulation with optional max touch points."""

    @abstractmethod
    async def set_user_agent_override(
        self,
        user_agent: str,
        accept_language: str = "",
        platform: str = "",
        user_agent_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Override the user agent string and related metadata."""

    @abstractmethod
    async def set_virtual_time_policy(self, policy: str, budget: int = 0) -> None:
        """Set the virtual time policy (e.g. 'advance', 'pause', 'pauseIfNetworkFetchesPending')."""

    @abstractmethod
    async def update_screen(self, screen_id: str, screen: dict[str, Any]) -> None:
        """Update a virtual screen by ID with the given configuration."""
