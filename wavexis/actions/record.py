"""Record action: capture browser interactions and generate wavexis.yaml."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

import yaml

from wavexis.backend.base import AbstractBackend
from wavexis.config import BrowserOptions, WaitStrategy
from wavexis.exceptions import WavexisError

_RECORD_SCRIPT = """
(function() {
    const events = [];
    const recordEvent = (type, data) => {
        events.push({ type, ...data, timestamp: Date.now() });
        window.__wavexis_record_events = events;
    };

    document.addEventListener('click', (e) => {
        const el = e.target;
        const selector = el.id ? '#' + el.id :
            el.className && typeof el.className === 'string' ?
                '.' + el.className.split(' ')[0] :
                el.tagName.toLowerCase();
        recordEvent('click', { selector, x: e.clientX, y: e.clientY });
    }, true);

    document.addEventListener('change', (e) => {
        const el = e.target;
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') {
            const selector = el.id ? '#' + el.id :
                el.name ? `[name="${el.name}"]` :
                el.tagName.toLowerCase();
            recordEvent('input', { selector, value: el.value, tag: el.tagName.toLowerCase() });
        }
    }, true);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === 'Tab' || e.key === 'Escape') {
            const el = e.target;
            const selector = el.id ? '#' + el.id :
                el.tagName.toLowerCase();
            recordEvent('keypress', { selector, key: e.key });
        }
    }, true);

    window.addEventListener('beforeunload', () => {
        recordEvent('navigate', { url: window.location.href });
    }, true);

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

    for event in events:
        etype = event.get("type")

        if etype == "click":
            actions.append({"click": {"selector": event["selector"]}})

        elif etype == "input":
            tag = event.get("tag", "input")
            if tag == "select":
                actions.append({
                    "select": {
                        "selector": event["selector"],
                        "value": event["value"],
                    }
                })
            else:
                actions.append({
                    "type": {
                        "selector": event["selector"],
                        "text": event["value"],
                    }
                })

        elif etype == "keypress":
            key = event.get("key", "")
            if key == "Enter":
                actions.append({"click": {"selector": event["selector"]}})
            else:
                actions.append({"keypress": {"key": key}})

        elif etype == "navigate":
            actions.append({"navigate": {"url": event["url"]}})

    config = {"actions": actions}
    return yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)


async def record_session(
    backend: AbstractBackend,
    url: str,
    duration: int = 60,
) -> str:
    """Record browser interactions and return a wavexis YAML config.

    Launches a non-headless browser, injects event listeners, and
    collects interactions until the duration expires or the page is closed.

    Args:
        backend: A browser backend instance.
        url: URL to navigate to for recording.
        duration: Maximum recording duration in seconds.

    Returns:
        YAML string representing the recorded actions.
    """
    await backend.launch(BrowserOptions(headless=False))
    await backend.navigate(url, WaitStrategy(strategy="load"))

    await backend.eval(_RECORD_SCRIPT, await_promise=False)

    events: list[dict[str, Any]] = []
    interrupted = False
    with contextlib.suppress(KeyboardInterrupt):
        await asyncio.sleep(duration)
    else:
        interrupted = True

    if not interrupted:
        try:
            raw = await backend.eval(
                "JSON.stringify(window.__wavexis_record_events || [])",
                await_promise=True,
            )
            if isinstance(raw, str):
                events = json.loads(raw)
            elif isinstance(raw, list):
                events = raw
        except (json.JSONDecodeError, TypeError, WavexisError):
            pass

    with contextlib.suppress(WavexisError):
        await backend.close()

    return events_to_yaml(events, url)
