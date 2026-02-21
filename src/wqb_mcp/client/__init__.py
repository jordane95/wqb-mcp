"""BrainApiClient composed from domain mixins."""

import logging
import sys

import requests

from .auth import AuthMixin
from .simulation import SimulationMixin
from .alpha import AlphaMixin
from .alpha_recordsets import AlphaRecordsetsMixin
from .correlation import CorrelationMixin
from .local_correlation import LocalCorrelationMixin
from .data import DataMixin
from .community import CommunityMixin
from .user import UserMixin
from .operators import OperatorsMixin
from .static_cache import StaticCache

# ---------------------------------------------------------------------------
# Configure the package-level logger once.  A single StreamHandler on stderr
# ensures all child loggers (wqb_mcp.client, wqb_mcp.client.static_cache, …)
# propagate here.  stdout is reserved for MCP JSON-RPC traffic.
# ---------------------------------------------------------------------------
_root_logger = logging.getLogger("wqb_mcp")
if not _root_logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    _root_logger.addHandler(_handler)
    _root_logger.setLevel(logging.DEBUG)  # allow children to decide their own level

# Level-name mapping used by the backward-compat property setter
_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "SUCCESS": logging.INFO,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


class BrainApiClient(
    AuthMixin,
    SimulationMixin,
    AlphaRecordsetsMixin,
    AlphaMixin,
    CorrelationMixin,
    LocalCorrelationMixin,
    DataMixin,
    CommunityMixin,
    UserMixin,
    OperatorsMixin,
):
    """WorldQuant BRAIN API client with comprehensive functionality."""

    def __init__(self):
        self.base_url = "https://api.worldquantbrain.com"
        self.session = requests.Session()
        self.auth_credentials = None
        self.is_authenticating = False
        self._static_cache = StaticCache()
        self.logger = logging.getLogger("wqb_mcp.client")
        self.logger.setLevel(logging.INFO)

        # Configure session
        self.session.timeout = 30
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    # Backward-compat property so warmup.py's
    #   brain_client.log_level = "WARN" / "INFO"
    # keeps working.
    @property
    def log_level(self) -> str:
        return logging.getLevelName(self.logger.level)

    @log_level.setter
    def log_level(self, value: str) -> None:
        self.logger.setLevel(_LEVEL_MAP.get(value.upper(), logging.INFO))


brain_client = BrainApiClient()
