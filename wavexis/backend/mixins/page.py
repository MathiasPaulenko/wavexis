"""Page lifecycle and inspection mixin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PageBackend(ABC):
    """Page-level lifecycle, inspection, and resource operations."""

    @abstractmethod
    async def page_get_frame_tree(self) -> dict[str, Any]:
        """Get the current page frame tree."""

    @abstractmethod
    async def page_get_layout_metrics(self) -> dict[str, Any]:
        """Get page layout metrics (viewport, content size, etc.)."""

    @abstractmethod
    async def page_get_navigation_history(self) -> dict[str, Any]:
        """Get the navigation history for the current page."""

    @abstractmethod
    async def page_navigate_to_history_entry(self, entry_id: int) -> None:
        """Navigate to a specific history entry by ID."""

    @abstractmethod
    async def page_bring_to_front(self) -> None:
        """Bring the current page to the foreground."""

    @abstractmethod
    async def page_wait_for_debugger(self) -> None:
        """Wait for the debugger to attach."""

    @abstractmethod
    async def page_get_resource_content(self, frame_id: str, url: str) -> dict[str, Any]:
        """Get the content of a page resource by frame ID and URL."""

    @abstractmethod
    async def page_set_download_behavior(self, behavior: str, download_path: str = "") -> None:
        """Set page download behavior (allow/deny and path)."""

    @abstractmethod
    async def page_capture_snapshot(self, format: str = "mhtml") -> str:
        """Capture a snapshot of the page as MHTML or text."""

    @abstractmethod
    async def page_print_to_pdf(
        self,
        landscape: bool = False,
        display_header_footer: bool = False,
        print_background: bool = False,
        scale: float = 1.0,
        paper_width: float = 8.5,
        paper_height: float = 11.0,
        margin_top: float = 0.4,
        margin_bottom: float = 0.4,
        margin_left: float = 0.4,
        margin_right: float = 0.4,
    ) -> str:
        """Print the page to PDF and return base64-encoded data."""

    @abstractmethod
    async def page_start_screencast(
        self, format: str = "jpeg", quality: int = 80, max_width: int = 0, max_height: int = 0
    ) -> None:
        """Start screencasting the page."""

    @abstractmethod
    async def page_stop_screencast(self) -> None:
        """Stop screencasting the page."""

    @abstractmethod
    async def page_set_bypass_csp(self, enabled: bool) -> None:
        """Enable or disable CSP bypass for the page."""

    @abstractmethod
    async def page_set_ad_blocking_enabled(self, enabled: bool) -> None:
        """Enable or disable ad blocking for the page."""

    @abstractmethod
    async def page_add_script_to_evaluate_on_new_document(
        self, source: str, world_name: str = ""
    ) -> str:
        """Add a script to evaluate on every new document. Returns script ID."""

    @abstractmethod
    async def page_remove_script_to_evaluate_on_new_document(self, script_id: str) -> None:
        """Remove a previously added script by ID."""

    @abstractmethod
    async def page_generate_test_report(self, message: str, group: str = "") -> None:
        """Generate a test report for the Reporting API."""

    @abstractmethod
    async def page_get_app_manifest(self) -> dict[str, Any]:
        """Get the web app manifest for the current page."""

    @abstractmethod
    async def page_get_resource_tree(self) -> dict[str, Any]:
        """Get the resource tree for the current page."""

    @abstractmethod
    async def page_add_compilation_cache(self, url: str, data: str) -> None:
        """Add data to the compilation cache for the given URL."""

    @abstractmethod
    async def page_add_script_to_evaluate_on_load(self, source: str) -> str:
        """Add a script to evaluate on page load. Returns script ID."""

    @abstractmethod
    async def page_capture_screenshot(
        self,
        format: str = "png",
        quality: int = 80,
        clip: dict[str, Any] | None = None,
        from_surface: bool = True,
        capture_beyond_viewport: bool = False,
    ) -> str:
        """Capture a screenshot of the page. Returns base64-encoded data."""

    @abstractmethod
    async def page_clear_compilation_cache(self) -> None:
        """Clear the compilation cache."""

    @abstractmethod
    async def page_clear_device_orientation_override(self) -> None:
        """Clear the device orientation override."""

    @abstractmethod
    async def page_clear_geolocation_override(self) -> None:
        """Clear the geolocation override."""

    @abstractmethod
    async def page_crash(self) -> None:
        """Crash the renderer."""

    @abstractmethod
    async def page_create_isolated_world(
        self, frame_id: str, world_name: str = "", grant_universal_access: bool = False
    ) -> str:
        """Create an isolated world for the given frame. Returns execution context ID."""

    @abstractmethod
    async def page_disable(self) -> None:
        """Disable the page domain."""

    @abstractmethod
    async def page_enable(self) -> None:
        """Enable the page domain."""

    @abstractmethod
    async def page_get_ad_script_ancestry(self, frame_id: str) -> dict[str, Any]:
        """Get the ad script ancestry for a frame."""

    @abstractmethod
    async def page_get_annotated_page_content(self) -> dict[str, Any]:
        """Get annotated page content."""

    @abstractmethod
    async def page_get_app_id(self) -> dict[str, Any]:
        """Get the app ID for the current page."""

    @abstractmethod
    async def page_get_installability_errors(self) -> dict[str, Any]:
        """Get installability errors for the current page."""

    @abstractmethod
    async def page_get_manifest_icons(self) -> dict[str, Any]:
        """Get manifest icons for the current page."""

    @abstractmethod
    async def page_get_origin_trials(self) -> dict[str, Any]:
        """Get origin trials for the current page."""

    @abstractmethod
    async def page_get_permissions_policy_state(self, frame_id: str) -> dict[str, Any]:
        """Get permissions policy state for a frame."""

    @abstractmethod
    async def page_handle_java_script_dialog(self, accept: bool, prompt_text: str = "") -> None:
        """Handle a JavaScript dialog (alias for handle_javascript_dialog)."""

    @abstractmethod
    async def page_handle_javascript_dialog(self, accept: bool, prompt_text: str = "") -> None:
        """Handle a JavaScript dialog."""

    @abstractmethod
    async def page_produce_compilation_cache(self, url: str) -> dict[str, Any]:
        """Produce compilation cache for the given URL."""

    @abstractmethod
    async def page_remove_script_to_evaluate_on_load(self, script_id: str) -> None:
        """Remove a script previously added to evaluate on load."""

    @abstractmethod
    async def page_reset_navigation_history(self) -> None:
        """Reset the navigation history."""

    @abstractmethod
    async def page_screencast_frame_ack(self, session_id: int) -> None:
        """Acknowledge a screencast frame."""

    @abstractmethod
    async def page_search_in_resource(
        self,
        frame_id: str,
        url: str,
        query: str,
        case_sensitive: bool = False,
        is_regex: bool = False,
    ) -> dict[str, Any]:
        """Search for a string in a resource."""

    @abstractmethod
    async def page_set_device_orientation_override(
        self, alpha: float, beta: float, gamma: float
    ) -> None:
        """Override the device orientation."""

    @abstractmethod
    async def page_set_document_content(self, frame_id: str, html: str) -> None:
        """Set the document content for a frame."""

    @abstractmethod
    async def page_set_font_families(self, font_families: dict[str, Any]) -> None:
        """Set font families for the page."""

    @abstractmethod
    async def page_set_font_sizes(self, font_sizes: dict[str, Any]) -> None:
        """Set font sizes for the page."""

    @abstractmethod
    async def page_set_geolocation_override(
        self, latitude: float = 0.0, longitude: float = 0.0, accuracy: float = 0.0
    ) -> None:
        """Override the geolocation."""

    @abstractmethod
    async def page_set_intercept_file_chooser_dialog(self, enabled: bool) -> None:
        """Intercept file chooser dialogs."""

    @abstractmethod
    async def page_set_lifecycle_events_enabled(self, enabled: bool) -> None:
        """Enable or disable lifecycle events."""

    @abstractmethod
    async def page_set_prerendering_allowed(self, is_allowed: bool) -> None:
        """Set whether prerendering is allowed."""

    @abstractmethod
    async def page_set_rph_registration_mode(self, mode: str) -> None:
        """Set the RPH registration mode."""

    @abstractmethod
    async def page_set_spc_transaction_mode(self, mode: str) -> None:
        """Set the SPC transaction mode."""

    @abstractmethod
    async def page_set_touch_emulation_enabled(
        self, enabled: bool, configuration: str = ""
    ) -> None:
        """Enable or disable touch emulation."""

    @abstractmethod
    async def page_set_web_lifecycle_state(self, state: str) -> None:
        """Set the web lifecycle state."""

    @abstractmethod
    async def page_stop(self) -> None:
        """Stop all page loading."""
