"""Unit tests for v2.10.0 features: backend degradation, CWV scoring, rate limiting."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Backend degradation tests ──────────────────────────────────


class TestBackendDegradation:
    """Tests for BackendManager.select_with_fallback."""

    @pytest.mark.asyncio
    async def test_fallback_when_preferred_fails(self) -> None:
        """Should fall back to second backend when preferred constructor fails."""
        from wavexis.backend.manager import BackendManager

        manager = BackendManager()

        def _fail_init() -> None:
            raise ImportError("cdpwave not installed")

        fail_cls = MagicMock(side_effect=ImportError("cdpwave not installed"))
        good_backend = MagicMock()
        good_cls = MagicMock(return_value=good_backend)

        manager._registry = {"cdp": fail_cls, "bidi": good_cls}

        result = await manager.select_with_fallback("cdp")
        assert result is good_backend

    @pytest.mark.asyncio
    async def test_fallback_tries_all_backends(self) -> None:
        """Should try all available backends until one succeeds."""
        from wavexis.backend.manager import BackendManager

        manager = BackendManager()

        fail1 = MagicMock(side_effect=ImportError("no cdp"))
        fail2 = MagicMock(side_effect=ImportError("no bidi"))
        good = MagicMock(return_value=MagicMock())

        manager._registry = {"cdp": fail1, "bidi": fail2, "custom": good}

        result = await manager.select_with_fallback(None)
        assert result is not None
        good.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_raises_when_all_fail(self) -> None:
        """Should raise BackendNotAvailableError when all backends fail."""
        from wavexis.backend.manager import BackendManager
        from wavexis.exceptions import BackendNotAvailableError

        manager = BackendManager()

        fail = MagicMock(side_effect=ImportError("no backend"))
        manager._registry = {"cdp": fail}

        with pytest.raises(BackendNotAvailableError):
            await manager.select_with_fallback("cdp")

    @pytest.mark.asyncio
    async def test_fallback_no_backends_available(self) -> None:
        """Should raise BackendNotAvailableError when no backends registered."""
        from wavexis.backend.manager import BackendManager
        from wavexis.exceptions import BackendNotAvailableError

        manager = BackendManager()
        manager._registry = {}

        with pytest.raises(BackendNotAvailableError):
            await manager.select_with_fallback(None)

    @pytest.mark.asyncio
    async def test_fallback_preferred_succeeds(self) -> None:
        """Should return preferred backend when it succeeds."""
        from wavexis.backend.manager import BackendManager

        manager = BackendManager()

        preferred = MagicMock()
        preferred_cls = MagicMock(return_value=preferred)
        other_cls = MagicMock()

        manager._registry = {"cdp": preferred_cls, "bidi": other_cls}

        result = await manager.select_with_fallback("cdp")
        assert result is preferred
        other_cls.assert_not_called()


# ── Core Web Vitals tests ──────────────────────────────────────


class TestCoreWebVitals:
    """Tests for CoreWebVitalsAction scoring and ratings."""

    def test_rating_good(self) -> None:
        """_rating should return 'good' for values at or below good threshold."""
        from wavexis.actions.core_web_vitals import _rating

        assert _rating(2000, 2500, 4000) == "good"
        assert _rating(2500, 2500, 4000) == "good"

    def test_rating_needs_improvement(self) -> None:
        """_rating should return 'needs-improvement' for values between thresholds."""
        from wavexis.actions.core_web_vitals import _rating

        assert _rating(3000, 2500, 4000) == "needs-improvement"
        assert _rating(0.15, 0.1, 0.25) == "needs-improvement"

    def test_rating_poor(self) -> None:
        """_rating should return 'poor' for values above poor threshold."""
        from wavexis.actions.core_web_vitals import _rating

        assert _rating(5000, 2500, 4000) == "poor"
        assert _rating(0.3, 0.1, 0.25) == "poor"

    def test_compute_score_perfect(self) -> None:
        """Score should be 100 when all metrics are good."""
        from wavexis.actions.core_web_vitals import CoreWebVitalsAction, CoreWebVitalsParams

        action = CoreWebVitalsAction(CoreWebVitalsParams())
        metrics = {
            "lcp_ms": 1000, "cls": 0.05, "inp_ms": 100,
            "fcp_ms": 500, "ttfb_ms": 200, "tbt_ms": 50, "load_ms": 1000,
        }
        score = action._compute_score(metrics, dom_size=500)
        assert score == 100

    def test_compute_score_poor(self) -> None:
        """Score should be low when all metrics are poor."""
        from wavexis.actions.core_web_vitals import CoreWebVitalsAction, CoreWebVitalsParams

        action = CoreWebVitalsAction(CoreWebVitalsParams())
        metrics = {
            "lcp_ms": 5000, "cls": 0.3, "inp_ms": 600,
            "fcp_ms": 3500, "ttfb_ms": 2000, "tbt_ms": 700, "load_ms": 6000,
        }
        score = action._compute_score(metrics, dom_size=3500)
        assert score <= 10

    def test_check_budgets_pass(self) -> None:
        """Budgets should pass when all metrics are within thresholds."""
        from wavexis.actions.core_web_vitals import CoreWebVitalsAction, CoreWebVitalsParams

        action = CoreWebVitalsAction(CoreWebVitalsParams())
        metrics = {"lcp_ms": 2000, "cls": 0.05, "inp_ms": 150}
        budgets = {"lcp_ms": 2500, "cls": 0.1, "inp_ms": 200}
        result = action._check_budgets(metrics, budgets)
        assert result["all_pass"] is True
        assert result["lcp_ms"]["pass"] is True

    def test_check_budgets_fail(self) -> None:
        """Budgets should fail when any metric exceeds threshold."""
        from wavexis.actions.core_web_vitals import CoreWebVitalsAction, CoreWebVitalsParams

        action = CoreWebVitalsAction(CoreWebVitalsParams())
        metrics = {"lcp_ms": 3000, "cls": 0.05, "inp_ms": 150}
        budgets = {"lcp_ms": 2500, "cls": 0.1, "inp_ms": 200}
        result = action._check_budgets(metrics, budgets)
        assert result["all_pass"] is False
        assert result["lcp_ms"]["pass"] is False
        assert result["cls"]["pass"] is True


# ── Rate limiting tests ────────────────────────────────────────


class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_within_capacity(self) -> None:
        """Should allow requests up to capacity."""
        from wavexis.serve import TokenBucket

        bucket = TokenBucket(capacity=5, refill_period=60.0)
        for _ in range(5):
            assert await bucket.acquire() is True

    @pytest.mark.asyncio
    async def test_acquire_exceeds_capacity(self) -> None:
        """Should deny requests exceeding capacity."""
        from wavexis.serve import TokenBucket

        bucket = TokenBucket(capacity=2, refill_period=60.0)
        assert await bucket.acquire() is True
        assert await bucket.acquire() is True
        assert await bucket.acquire() is False

    @pytest.mark.asyncio
    async def test_refill_over_time(self) -> None:
        """Should refill tokens over time."""
        from wavexis.serve import TokenBucket

        bucket = TokenBucket(capacity=1, refill_period=0.1)
        assert await bucket.acquire() is True
        assert await bucket.acquire() is False
        await asyncio.sleep(0.15)
        assert await bucket.acquire() is True

    @pytest.mark.asyncio
    async def test_retry_after_when_empty(self) -> None:
        """retry_after should return positive value when empty."""
        from wavexis.serve import TokenBucket

        bucket = TokenBucket(capacity=1, refill_period=60.0)
        await bucket.acquire()
        retry = await bucket.retry_after()
        assert retry > 0

    @pytest.mark.asyncio
    async def test_retry_after_when_has_tokens(self) -> None:
        """retry_after should return 0 when tokens available."""
        from wavexis.serve import TokenBucket

        bucket = TokenBucket(capacity=5, refill_period=60.0)
        assert await bucket.retry_after() == 0.0


class TestRateLimitMiddleware:
    """Tests for rate limit middleware integration."""

    @pytest.mark.asyncio
    async def test_middleware_allows_when_within_limit(self) -> None:
        """Middleware should call handler when within rate limit."""
        from wavexis.serve import TokenBucket, _rate_limit_middleware

        bucket = TokenBucket(capacity=10, refill_period=60.0)
        middleware = _rate_limit_middleware(bucket)

        request = MagicMock()
        handler = AsyncMock(return_value=MagicMock())

        with patch("wavexis.serve._import_aiohttp"):
            await middleware(request, handler)

        handler.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_blocks_when_exceeded(self) -> None:
        """Middleware should return 429 when rate limit exceeded."""
        from wavexis.serve import TokenBucket, _rate_limit_middleware

        bucket = TokenBucket(capacity=1, refill_period=60.0)
        await bucket.acquire()

        middleware = _rate_limit_middleware(bucket)

        request = MagicMock()
        handler = AsyncMock()

        mock_web = MagicMock()
        mock_response = MagicMock()
        mock_web.Response.return_value = mock_response

        with patch("wavexis.serve._import_aiohttp", return_value=mock_web):
            await middleware(request, handler)

        handler.assert_not_called()
        mock_web.Response.assert_called_once()
        assert mock_web.Response.call_args[1]["status"] == 429
