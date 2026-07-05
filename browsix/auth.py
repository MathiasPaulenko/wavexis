"""Auth context for loading cookies, headers, and basic auth from JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AuthContext:
    """Authentication context loaded from a JSON file.

    Attributes:
        cookies: List of cookie dicts with name, value, domain, path.
        headers: Extra HTTP headers to set.
        username: HTTP basic auth username.
        password: HTTP basic auth password.
    """

    cookies: list[dict[str, str]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    username: str | None = None
    password: str | None = None


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
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return AuthContext(
        cookies=data.get("cookies", []),
        headers=data.get("headers", {}),
        username=data.get("username"),
        password=data.get("password"),
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
    data: list[dict[str, str]] = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("cookies", [])


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
    data: dict[str, str] = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if "headers" in data and isinstance(data["headers"], dict):
            return data["headers"]
        return data
    return {}
