"""Record action: capture browser interactions and generate wavexis.yaml."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any

import yaml

from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy
from wavexis.exceptions import WavexisError

logger = logging.getLogger(__name__)

_RECORD_SCRIPT = r"""
(function() {
    if (window.__wavexis_recording) return;
    window.__wavexis_recording = true;
    const events = [];
    const recordEvent = (type, data) => {
        events.push({ type, ...data, timestamp: Date.now() });
        window.__wavexis_record_events = events;
    };

    // Build a robust CSS selector for the element, escaping any special
    // characters that would break querySelector or allow injection.
    const esc = (s) => CSS.escape(String(s));
    const classSelector = (el) => {
        const cls = el.className;
        if (cls && typeof cls === 'string') {
            const first = cls.trim().split(/\s+/)[0];
            if (first) return '.' + esc(first);
        }
        return '';
    };

    // Fallback: build an nth-child path from the element up to <body>.
    const nthChildPath = (el) => {
        const path = [];
        let node = el;
        while (node && node.nodeType === 1 && node !== document.body) {
            const parent = node.parentNode;
            if (!parent) break;
            const siblings = Array.prototype.filter.call(parent.children,
                function(c) { return c.tagName === node.tagName; });
            const idx = siblings.indexOf(node) + 1;
            path.unshift(node.tagName.toLowerCase() + ':nth-child(' + idx + ')');
            node = parent;
        }
        return path.length ? path.join(' > ') : el.tagName.toLowerCase();
    };

    const getSelector = (el) => {
        if (!el || el.nodeType !== 1) return null;
        if (el.id) return '#' + esc(el.id);
        if (el.getAttribute('data-testid'))
            return '[data-testid=' + esc(el.getAttribute('data-testid')) + ']';
        const cls = classSelector(el);
        if (cls) return el.tagName.toLowerCase() + cls;
        return nthChildPath(el);
    };

    document.addEventListener('click', (e) => {
        const el = e.target;
        recordEvent('click', {
            selector: getSelector(el),
            x: e.clientX, y: e.clientY,
            text: (el.innerText || '').substring(0, 100),
        });
    }, true);

    document.addEventListener('change', (e) => {
        const el = e.target;
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') {
            recordEvent('input', {
                selector: getSelector(el),
                value: el.value,
                tag: el.tagName.toLowerCase(),
            });
        }
    }, true);

    document.addEventListener('keydown', (e) => {
        if (e.key.length === 1 || ['Enter','Tab','Escape','Backspace','Delete'].includes(e.key)) {
            recordEvent('keypress', {
                selector: getSelector(e.target),
                key: e.key,
            });
        }
    }, true);

    // Scroll events (throttled to avoid flooding).
    let scrollTimer = null;
    window.addEventListener('scroll', () => {
        if (scrollTimer) return;
        scrollTimer = setTimeout(() => {
            recordEvent('scroll', { scrollX: window.scrollX, scrollY: window.scrollY });
            scrollTimer = null;
        }, 500);
    }, true);

    // Navigation: beforeunload for full page navigations.
    window.addEventListener('beforeunload', () => {
        recordEvent('navigate', { url: window.location.href });
    }, true);

    // SPA navigations: intercept History API.
    const origPush = history.pushState;
    const origReplace = history.replaceState;
    history.pushState = function() {
        recordEvent('navigate', { url: arguments[2] || window.location.href });
        return origPush.apply(this, arguments);
    };
    history.replaceState = function() {
        recordEvent('navigate', { url: arguments[2] || window.location.href });
        return origReplace.apply(this, arguments);
    };

    console.log('[wavexis] Recording started. Interact with the page.');
})();
"""


def events_to_yaml(events: list[dict[str, Any]], initial_url: str) -> str:
    """Convert recorded events to a wavexis YAML config.

    Args:
        events: List of recorded event dicts.
        initial_url: The initial URL that was navigated to.

    Returns:
        YAML string representing the recorded actions.
    """
    actions: list[dict[str, Any]] = [{"navigate": {"url": initial_url}}]
    last_url = initial_url

    for event in events:
        etype = event.get("type")

        if etype == "click":
            selector = event.get("selector", "")
            if selector:
                actions.append({"click": {"selector": selector}})

        elif etype == "input":
            tag = event.get("tag", "input")
            selector = event.get("selector", "")
            value = event.get("value", "")
            if tag == "select":
                actions.append(
                    {
                        "select": {
                            "selector": selector,
                            "value": value,
                        }
                    }
                )
            else:
                actions.append(
                    {
                        "type": {
                            "selector": selector,
                            "text": value,
                        }
                    }
                )

        elif etype == "keypress":
            key = event.get("key", "")
            selector = event.get("selector", "")
            if key == "Enter" and selector:
                actions.append({"click": {"selector": selector}})
            elif key and len(key) == 1:
                actions.append({"type": {"text": key}})
            else:
                actions.append({"keypress": {"key": key}})

        elif etype == "navigate":
            url = event.get("url", "")
            if url and url != last_url:
                actions.append({"navigate": {"url": url}})
                last_url = url

        elif etype == "scroll":
            # Scroll is not a standard multi-action type; skip.
            pass

    config = {"actions": actions}
    return str(yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True))


async def record_events(
    backend: AbstractBackend,
    url: str,
    duration: int = 60,
) -> list[dict[str, Any]]:
    """Navigate to *url*, inject recording script, and collect events.

    Unlike :func:`record_session`, this function does **not** launch the
    backend — it assumes the backend is already launched.  This makes it
    suitable for use from MCP servers or other orchestration layers that
    manage the backend lifecycle themselves.

    Args:
        backend: An already-launched browser backend instance.
        url: URL to navigate to for recording.
        duration: Maximum recording duration in seconds.

    Returns:
        List of recorded event dicts.  Use :func:`events_to_yaml` to
        convert them to a YAML workflow.
    """
    await backend.navigate(url, WaitStrategy(strategy="load"))
    await backend.eval(_RECORD_SCRIPT, await_promise=False)

    with contextlib.suppress(KeyboardInterrupt):
        await asyncio.sleep(duration)

    # Always attempt to collect recorded events, even when interrupted —
    # interrupting the recording is the primary way users stop it early,
    # and discarding events on Ctrl+C would lose the entire session.
    events: list[dict[str, Any]] = []
    try:
        raw = await backend.eval(
            "JSON.stringify(window.__wavexis_record_events || [])",
            await_promise=True,
        )
        if isinstance(raw, str):
            events = json.loads(raw)
        elif isinstance(raw, list):
            events = raw
    except (json.JSONDecodeError, TypeError, WavexisError) as exc:
        logger.warning("Failed to collect recorded events: %s", exc)

    return events


async def record_session(
    backend: AbstractBackend,
    url: str,
    duration: int = 60,
) -> str:
    """Record browser interactions and return a wavexis YAML config.

    Launches a non-headless browser, injects event listeners, and
    collects interactions until the duration expires or the page is closed.

    This is a convenience wrapper that launches the backend, calls
    :func:`record_events`, and converts the result to YAML.  For use cases
    where the backend lifecycle is managed externally (e.g. MCP servers),
    use :func:`record_events` + :func:`events_to_yaml` instead.

    Args:
        backend: A browser backend instance.
        url: URL to navigate to for recording.
        duration: Maximum recording duration in seconds.

    Returns:
        YAML string representing the recorded actions.
    """
    await backend.launch(BrowserOptions(headless=False))
    events = await record_events(backend, url, duration)
    return events_to_yaml(events, url)
