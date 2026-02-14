"""Pydantic models for the WorldQuant BRAIN MCP Server."""

from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr


class AuthCredentials(BaseModel):
    email: EmailStr
    password: str


class SimulationSettings(BaseModel):
    instrumentType: str = "EQUITY"
    region: str = "USA"
    universe: str = "TOP3000"
    delay: int = 1
    decay: float = 0.0
    neutralization: str = "NONE"
    truncation: float = 0.0
    pasteurization: str = "ON"
    unitHandling: str = "VERIFY"
    nanHandling: str = "OFF"
    language: str = "FASTEXPR"
    visualization: bool = True
    testPeriod: str = "P0Y0M"
    selectionHandling: str = "POSITIVE"
    selectionLimit: int = 1000
    maxTrade: str = "OFF"
    componentActivation: str = "IS"


class CorrelatedAlpha(BaseModel):
    """Represents a single correlated alpha."""
    alpha_id: str
    correlation: float


class CorrelationCheckResult(BaseModel):
    """Result for a single correlation type check."""
    max_correlation: float
    passes_check: bool
    count: Optional[int] = None
    top_correlations: Optional[List[CorrelatedAlpha]] = None


class CorrelationCheckResponse(BaseModel):
    """Complete correlation check response."""
    alpha_id: str
    threshold: float
    correlation_type: str
    checks: Dict[str, CorrelationCheckResult]
    all_passed: bool


class SimulationData(BaseModel):
    type: str = "REGULAR"  # "REGULAR" or "SUPER"
    settings: SimulationSettings
    regular: Optional[str] = None
    combo: Optional[str] = None
    selection: Optional[str] = None
