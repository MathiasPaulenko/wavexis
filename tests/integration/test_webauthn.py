"""Integration tests for WebAuthn actions against a real Chrome browser."""

import pytest

from browsix.actions.webauthn import WebAuthnAction, WebAuthnParams
from browsix.backend.cdp import CDPBackend
from browsix.config import BrowserOptions, WaitStrategy

pytestmark = [pytest.mark.integration, pytest.mark.chrome]


@pytest.fixture
def backend() -> CDPBackend:
    return CDPBackend()


@pytest.fixture
def browser_opts() -> BrowserOptions:
    return BrowserOptions(headless=True)


async def test_webauthn_add_virtual_authenticator(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    params = WebAuthnParams(
        url="https://example.com",
        action="add-virtual-authenticator",
        protocol="ctap2",
        transport="usb",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await WebAuthnAction(params).execute(backend)
    assert isinstance(result, str)
    assert len(result) > 0


async def test_webauthn_add_and_get_credentials(
    backend: CDPBackend, browser_opts: BrowserOptions
) -> None:
    params_add = WebAuthnParams(
        url="https://example.com",
        action="add-virtual-authenticator",
        protocol="ctap2",
        transport="usb",
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    auth_id = await WebAuthnAction(params_add).execute(backend)
    assert isinstance(auth_id, str)

    params_get = WebAuthnParams(
        url="https://example.com",
        action="get-credentials",
        authenticator_id=auth_id,
        wait=WaitStrategy(strategy="load"),
        browser=browser_opts,
    )
    result = await WebAuthnAction(params_get).execute(backend)
    assert isinstance(result, list)
