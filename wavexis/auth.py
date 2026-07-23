"""Auth context for loading cookies, headers, and basic auth from JSON.

.. deprecated::
    Storing passwords in plain-text JSON is insecure. Consider using
    environment variables or an encrypted secrets manager instead.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from wavexis.exceptions import WavexisError
from wavexis.output import validate_path

if TYPE_CHECKING:
    from wavexis.backend.base import AbstractBackend
    from wavexis.config import WaitStrategy

logger = logging.getLogger(__name__)

__all__ = [
    "AuthContext",
    "apply_auth_context",
    "load_auth",
    "load_auth_context",
    "load_headers",
]

# Auth files should be small JSON payloads; reject anything larger as a DoS guard.
_MAX_AUTH_FILE_SIZE = 1_000_000


def _check_file_size(path: Path) -> None:
    if path.exists() and path.stat().st_size > _MAX_AUTH_FILE_SIZE:
        raise ValueError(f"Auth file exceeds maximum size of {_MAX_AUTH_FILE_SIZE} bytes: {path}")


def _validate_cookie(cookie: Any) -> dict[str, str]:
    if not isinstance(cookie, dict):
        raise ValueError("Each cookie must be a JSON object")
    if "name" not in cookie or "value" not in cookie:
        raise ValueError("Each cookie must have 'name' and 'value' keys")
    return {str(k): str(v) for k, v in cookie.items()}


@dataclass
class AuthContext:
    """Authentication context loaded from a JSON file.

    Attributes:
        cookies: List of cookie dicts with name, value, domain, path.
        headers: Extra HTTP headers to set.
        username: HTTP basic auth username.
        password: HTTP basic auth password.
        target_origin: Expected origin (scheme://host) for the target URL.
            If provided, the URL passed to ``apply_auth_context`` must match
            this origin or one of the cookie domains.
    """

    cookies: list[dict[str, str]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    username: str | None = None
    password: str | None = None
    target_origin: str | None = None


def load_auth_context(path: str) -> AuthContext:
    """Load an AuthContext from a JSON file.

    Args:
        path: Path to the JSON auth context file.

    Returns:
        An AuthContext instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    valid_path = validate_path(path)
    _check_file_size(valid_path)
    raw_data = json.loads(valid_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        got = type(raw_data).__name__
        raise ValueError(f"Auth context file must contain a JSON object, got {got}")
    data = raw_data
    cookies = data.get("cookies", [])
    if not isinstance(cookies, list):
        raise ValueError("'cookies' must be a list of cookie objects")
    validated_cookies = [_validate_cookie(c) for c in cookies]
    headers = data.get("headers", {})
    if not isinstance(headers, dict):
        raise ValueError("'headers' must be a JSON object")
    password = data.get("password")
    if password and not os.environ.get("WAVEXIS_AUTH_NO_WARN"):
        logger.warning(
            "Auth context '%s' contains a plain-text password. "
            "Consider using environment variables or an encrypted secrets manager. "
            "Set WAVEXIS_AUTH_NO_WARN=1 to suppress this warning.",
            path,
        )
    return AuthContext(
        cookies=validated_cookies,
        headers={str(k): str(v) for k, v in headers.items()},
        username=data.get("username"),
        password=password,
        target_origin=data.get("target_origin"),
    )


def load_auth(path: str | Path) -> list[dict[str, str]]:
    """Load cookies from a JSON file.

    Args:
        path: Path to the JSON file containing a list of cookie dicts.

    Returns:
        List of cookie dicts.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    valid_path = validate_path(path)
    _check_file_size(valid_path)
    data: list[dict[str, str]] | dict[str, Any] = json.loads(valid_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [_validate_cookie(c) for c in data]
    if isinstance(data, dict):
        cookies = data.get("cookies", [])
        if not isinstance(cookies, list):
            raise ValueError("'cookies' must be a list of cookie objects")
        return [_validate_cookie(c) for c in cookies]
    got = type(data).__name__
    raise ValueError(f"Auth cookie file must contain a JSON list or object, got {got}")


def load_headers(path: str | Path) -> dict[str, str]:
    """Load HTTP headers from a JSON file.

    Args:
        path: Path to the JSON file containing a headers dict.

    Returns:
        Dict of header name to value.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    valid_path = validate_path(path)
    _check_file_size(valid_path)
    data: Any = json.loads(valid_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if "headers" in data and isinstance(data["headers"], dict):
            return {str(k): str(v) for k, v in data["headers"].items()}
        return {str(k): str(v) for k, v in data.items()}
    raise ValueError(f"Headers file must contain a JSON object, got {type(data).__name__}")


def _origin(url: str) -> str:
    """Return the scheme://host origin of a URL, lower-cased."""
    parsed = urlparse(url)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _host_matches_cookie_domain(host: str, domain: str) -> bool:
    """Check whether ``host`` matches a cookie ``domain`` attribute."""
    host = host.lower()
    domain = domain.lower().lstrip(".")
    if host == domain:
        return True
    return host.endswith("." + domain)


def _validate_auth_origin(url: str, ctx: AuthContext) -> None:
    """Ensure the navigation URL matches an allowed auth origin.

    When ``target_origin`` is set it is the only allowed origin. Otherwise the
    URL must match the origin of one of the cookie domains. This prevents a
    guessed/forced context file from sending credentials to an
    attacker-controlled URL.
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https"):
        raise WavexisError(
            f"Auth context cannot be applied to {parsed_url.scheme!r} URLs"
        )
    url_origin = _origin(url)
    if ctx.target_origin:
        if url_origin != ctx.target_origin.lower():
            raise WavexisError(
                f"URL {url!r} does not match required target_origin "
                f"{ctx.target_origin!r}."
            )
        return

    url_host = parsed_url.hostname or ""
    allowed: set[str] = set()
    for cookie in ctx.cookies:
        domain = cookie.get("domain")
        if not domain or not domain.strip():
            continue
        if "://" in domain or "/" in domain:
            raise WavexisError(
                f"Cookie domain must be a plain host, got {domain!r}"
            )
        allowed.add(domain.lower().lstrip("."))
    if not allowed:
        raise WavexisError(
            "Auth context must specify a target_origin or cookie domain "
            "to prevent credential exfiltration."
        )
    for origin_or_domain in allowed:
        if "://" in origin_or_domain:
            if url_origin == origin_or_domain:
                return
        elif _host_matches_cookie_domain(url_host, origin_or_domain):
            return
    raise WavexisError(
        f"URL {url!r} does not match any allowed auth origin."
    )


async def apply_auth_context(
    backend: AbstractBackend,
    ctx: AuthContext,
    url: str,
    wait: WaitStrategy | None = None,
) -> None:
    """Apply auth context to a backend and navigate to a URL.

    Sets headers, basic auth, navigates, sets cookies, and re-navigates.

    Args:
        backend: The browser backend to apply auth to.
        ctx: The auth context with cookies, headers, and credentials.
        url: The URL to navigate to.
        wait: Wait strategy for navigation. Defaults to "load".
    """
    from wavexis.config import CookieParams, WaitStrategy

    if wait is None:
        wait = WaitStrategy(strategy="load")

    if url:
        _validate_auth_origin(url, ctx)

    if ctx.headers:
        await backend.set_headers(ctx.headers)
    if ctx.username and ctx.password:
        cred = base64.b64encode(f"{ctx.username}:{ctx.password}".encode()).decode()
        await backend.set_headers({"Authorization": f"Basic {cred}"})
    if url:
        await backend.navigate(url, wait)
    cookies_set = False
    for cookie in ctx.cookies:
        cookies_set = True
        cp = CookieParams(
            name=cookie.get("name", ""),
            value=cookie.get("value", ""),
            domain=cookie.get("domain", ""),
            path=cookie.get("path", "/"),
        )
        await backend.set_cookie(cp)
    if cookies_set and url:
        await backend.navigate(url, wait)
