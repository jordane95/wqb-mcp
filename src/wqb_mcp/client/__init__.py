"""BrainApiClient composed from domain mixins."""

import sys

import requests

from .auth import AuthMixin
from .simulation import SimulationMixin
from .alpha import AlphaMixin
from .alpha_recordsets import AlphaRecordsetsMixin
from .correlation import CorrelationMixin
from .data import DataMixin
from .diversity import DiversityMixin
from .community import CommunityMixin
from .user import UserMixin
from .operators import OperatorsMixin
from .platform_config import PlatformConfigMixin


class BrainApiClient(
    AuthMixin,
    SimulationMixin,
    AlphaRecordsetsMixin,
    AlphaMixin,
    CorrelationMixin,
    DataMixin,
    DiversityMixin,
    CommunityMixin,
    UserMixin,
    OperatorsMixin,
    PlatformConfigMixin,
):
    """WorldQuant BRAIN API client with comprehensive functionality."""

    def __init__(self):
        self.base_url = "https://api.worldquantbrain.com"
        self.session = requests.Session()
        self.auth_credentials = None
        self.is_authenticating = False

        # Configure session
        self.session.timeout = 30
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def log(self, message: str, level: str = "INFO"):
        """Log messages to stderr to avoid MCP protocol interference."""
        try:
            print(f"[{level}] {message}", file=sys.stderr)
        except UnicodeEncodeError:
            try:
                safe_message = message.encode('ascii', 'ignore').decode('ascii')
                print(f"[{level}] {safe_message}", file=sys.stderr)
            except Exception:
                print(f"[{level}] Log message", file=sys.stderr)
        except Exception:
            print(f"[{level}] Log message", file=sys.stderr)


brain_client = BrainApiClient()
