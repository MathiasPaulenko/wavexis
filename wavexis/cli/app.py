"""wavexis CLI — thin orchestrator that imports domain modules."""

from wavexis.cli._advanced import *  # noqa: F401, F403
from wavexis.cli._capture import *  # noqa: F401, F403
from wavexis.cli._config import *  # noqa: F401, F403
from wavexis.cli._debug import *  # noqa: F401, F403
from wavexis.cli._emulation import *  # noqa: F401, F403
from wavexis.cli._experimental import *  # noqa: F401, F403
from wavexis.cli._iframe import *  # noqa: F401, F403
from wavexis.cli._input import *  # noqa: F401, F403
from wavexis.cli._navigation import *  # noqa: F401, F403
from wavexis.cli._network import *  # noqa: F401, F403
from wavexis.cli._perf import *  # noqa: F401, F403
from wavexis.cli._serve import *  # noqa: F401, F403
from wavexis.cli._session import *  # noqa: F401, F403
from wavexis.cli._shared import *  # noqa: F401, F403
from wavexis.cli._shared import app  # noqa: F401
from wavexis.cli._workflow import *  # noqa: F401, F403

__all__ = ["app"]
