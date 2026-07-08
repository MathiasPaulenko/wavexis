"""wavexis CLI — thin orchestrator that imports domain modules."""

from wavexis.cli import (
    _advanced,  # noqa: F401
    _capture,  # noqa: F401
    _config,  # noqa: F401
    _debug,  # noqa: F401
    _emulation,  # noqa: F401
    _experimental,  # noqa: F401
    _iframe,  # noqa: F401
    _input,  # noqa: F401
    _navigation,  # noqa: F401
    _network,  # noqa: F401
    _network_inspect,  # noqa: F401
    _nl,  # noqa: F401
    _perf,  # noqa: F401
    _serve,  # noqa: F401
    _session,  # noqa: F401
    _shadow,  # noqa: F401
    _workflow,  # noqa: F401
)
from wavexis.cli._capture import _check_assertion  # noqa: F401
from wavexis.cli._shared import (  # noqa: F401
    EXIT_BACKEND_ERROR,
    EXIT_BROWSER_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_SUCCESS,
    CLIContext,
    _browser_options,
    _ctx,
    _load_global_config,
    app,
)

__all__ = ["app"]
