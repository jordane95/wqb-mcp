"""Alpha management mixin for BrainApiClient."""
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator
from ..utils import parse_json_or_error


class AlphaRegion(str, Enum):
    USA = "USA"
    GLB = "GLB"
    EUR = "EUR"
    ASI = "ASI"
    CHN = "CHN"
    AMR = "AMR"
    IND = "IND"


class AlphaUniverse(str, Enum):
    TOP3000 = "TOP3000"
    TOP1000 = "TOP1000"
    TOP500 = "TOP500"
    TOP200 = "TOP200"
    ILLIQUID_MINVOL1M = "ILLIQUID_MINVOL1M"
    TOPSP500 = "TOPSP500"
    MINVOL1M = "MINVOL1M"
    TOPDIV3000 = "TOPDIV3000"
    TOP2500 = "TOP2500"
    TOP1200 = "TOP1200"
    TOP800 = "TOP800"
    TOP400 = "TOP400"
    TOPCS1600 = "TOPCS1600"
    TOP2000U = "TOP2000U"
    TOP600 = "TOP600"


REGION_UNIVERSE_MAP: Dict[AlphaRegion, set[AlphaUniverse]] = {
    AlphaRegion.USA: {
        AlphaUniverse.TOP3000,
        AlphaUniverse.TOP1000,
        AlphaUniverse.TOP500,
        AlphaUniverse.TOP200,
        AlphaUniverse.ILLIQUID_MINVOL1M,
        AlphaUniverse.TOPSP500,
    },
    AlphaRegion.GLB: {
        AlphaUniverse.TOP3000,
        AlphaUniverse.MINVOL1M,
        AlphaUniverse.TOPDIV3000,
    },
    AlphaRegion.EUR: {
        AlphaUniverse.TOP2500,
        AlphaUniverse.TOP1200,
        AlphaUniverse.TOP800,
        AlphaUniverse.TOP400,
        AlphaUniverse.ILLIQUID_MINVOL1M,
        AlphaUniverse.TOPCS1600,
    },
    AlphaRegion.ASI: {
        AlphaUniverse.MINVOL1M,
        AlphaUniverse.ILLIQUID_MINVOL1M,
    },
    AlphaRegion.CHN: {
        AlphaUniverse.TOP2000U,
    },
    AlphaRegion.AMR: {
        AlphaUniverse.TOP600,
    },
    AlphaRegion.IND: {
        AlphaUniverse.TOP500,
    },
}


class AlphaSettings(BaseModel):
    instrumentType: str
    region: AlphaRegion
    universe: AlphaUniverse
    delay: int
    decay: float
    neutralization: str
    truncation: float
    pasteurization: str
    unitHandling: str
    nanHandling: str
    maxTrade: str
    maxPosition: str
    language: str
    visualization: bool
    startDate: str
    endDate: str

    @model_validator(mode="after")
    def validate_region_universe(self) -> "AlphaSettings":
        if self.region is None or self.universe is None:
            return self

        allowed = REGION_UNIVERSE_MAP.get(self.region)
        if allowed is None or self.universe in allowed:
            return self

        allowed_values = ", ".join(sorted(u.value for u in allowed))
        raise ValueError(
            f"Invalid universe '{self.universe.value}' for region '{self.region.value}'. "
            f"Allowed universes: {allowed_values}"
        )


class AlphaRegular(BaseModel):
    code: str
    description: Optional[str] = None
    operatorCount: int


class AlphaRegularPatch(BaseModel):
    description: Optional[str] = None


class AlphaPropertiesPatch(BaseModel):
    model_config = {"extra": "forbid"}

    name: Optional[str] = None
    color: Optional[str] = None
    tags: Optional[List[str]] = None
    selectionDesc: Optional[str] = None
    comboDesc: Optional[str] = None
    regular: Optional[AlphaRegularPatch] = None


class AlphaIdName(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class AlphaNamedMultiplier(BaseModel):
    name: Optional[str] = None
    multiplier: Optional[float] = None


class AlphaThemeMultiplier(AlphaIdName):
    multiplier: Optional[float] = None


class AlphaCheckBase(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    result: str


class AlphaCheckLimitValue(AlphaCheckBase):
    limit: float
    value: float


class AlphaCheckLimitValueRatio(AlphaCheckLimitValue):
    ratio: float


class AlphaCheckCompetitions(AlphaCheckBase):
    competitions: List[AlphaIdName]


class AlphaCheckPyramids(AlphaCheckBase):
    effective: int
    multiplier: float
    pyramids: List[AlphaNamedMultiplier]


class AlphaCheckThemes(AlphaCheckBase):
    themes: List[AlphaThemeMultiplier]


AlphaCheck = Union[
    AlphaCheckLimitValueRatio,
    AlphaCheckLimitValue,
    AlphaCheckCompetitions,
    AlphaCheckPyramids,
    AlphaCheckThemes,
    AlphaCheckBase,
]


class AlphaPerformanceBlock(BaseModel):
    pnl: float
    bookSize: float
    longCount: int
    shortCount: int
    turnover: float
    returns: float
    drawdown: float
    margin: float
    sharpe: float
    fitness: float
    startDate: Optional[str] = None

    def __str__(self) -> str:
        return (
            f"pnl={self.pnl:.4f} bookSize={self.bookSize:.4f} "
            f"longCount={self.longCount} shortCount={self.shortCount} "
            f"turnover={self.turnover:.4f} returns={self.returns:.4f} "
            f"drawdown={self.drawdown:.4f} margin={self.margin:.4f} "
            f"sharpe={self.sharpe:.4f} fitness={self.fitness:.4f}"
        )


class AlphaIsMetrics(AlphaPerformanceBlock):
    glbAmer: Optional[AlphaPerformanceBlock] = None
    glbApac: Optional[AlphaPerformanceBlock] = None
    glbEmea: Optional[AlphaPerformanceBlock] = None
    investabilityConstrained: AlphaPerformanceBlock
    riskNeutralized: Optional[AlphaPerformanceBlock] = None
    checks: List[AlphaCheck] = Field(default_factory=list)


class AlphaPyramidThemes(BaseModel):
    effective: Optional[int] = None
    pyramids: Optional[List[AlphaNamedMultiplier]] = None


class AlphaTrainTestMetrics(BaseModel):
    pnl: Optional[float] = None
    bookSize: Optional[float] = None
    longCount: Optional[int] = None
    shortCount: Optional[int] = None
    turnover: Optional[float] = None
    returns: Optional[float] = None
    drawdown: Optional[float] = None
    margin: Optional[float] = None
    sharpe: Optional[float] = None
    fitness: Optional[float] = None
    startDate: Optional[str] = None
    glbAmer: Optional[AlphaPerformanceBlock] = None
    glbApac: Optional[AlphaPerformanceBlock] = None
    glbEmea: Optional[AlphaPerformanceBlock] = None
    investabilityConstrained: Optional[AlphaPerformanceBlock] = None
    riskNeutralized: Optional[AlphaPerformanceBlock] = None


class AlphaOsMetrics(BaseModel):
    startDate: Optional[str] = None
    turnover: Optional[float] = None
    returns: Optional[float] = None
    drawdown: Optional[float] = None
    margin: Optional[float] = None
    fitness: Optional[float] = None
    preCloseSharpe: Optional[float] = None
    sharpe: Optional[float] = None
    sharpe60: Optional[float] = None
    sharpe125: Optional[float] = None
    sharpe250: Optional[float] = None
    sharpe500: Optional[float] = None
    osISSharpeRatio: Optional[float] = None
    preCloseSharpeRatio: Optional[float] = None
    checks: List[AlphaCheck] = Field(default_factory=list)

    def __str__(self) -> str:
        parts: List[str] = []
        if self.turnover is not None:
            parts.append(f"turnover={self.turnover:.4f}")
        if self.returns is not None:
            parts.append(f"returns={self.returns:.4f}")
        if self.drawdown is not None:
            parts.append(f"drawdown={self.drawdown:.4f}")
        if self.margin is not None:
            parts.append(f"margin={self.margin:.4f}")
        if self.fitness is not None:
            parts.append(f"fitness={self.fitness:.4f}")
        if self.sharpe is not None:
            parts.append(f"sharpe={self.sharpe:.4f}")
        if self.sharpe60 is not None:
            parts.append(f"sharpe60={self.sharpe60:.4f}")
        if self.sharpe125 is not None:
            parts.append(f"sharpe125={self.sharpe125:.4f}")
        if self.sharpe250 is not None:
            parts.append(f"sharpe250={self.sharpe250:.4f}")
        if self.sharpe500 is not None:
            parts.append(f"sharpe500={self.sharpe500:.4f}")
        if self.preCloseSharpe is not None:
            parts.append(f"preCloseSharpe={self.preCloseSharpe:.4f}")
        if self.osISSharpeRatio is not None:
            parts.append(f"osISSharpeRatio={self.osISSharpeRatio:.4f}")
        if self.preCloseSharpeRatio is not None:
            parts.append(f"preCloseSharpeRatio={self.preCloseSharpeRatio:.4f}")
        if self.startDate is not None:
            parts.append(f"startDate={self.startDate}")
        if self.checks:
            parts.append(f"checks={len(self.checks)}")
        return " ".join(parts) if parts else "(no os metrics)"


class AlphaDetailsResponse(BaseModel):
    model_config = {"populate_by_name": True}

    id: str
    type: str
    author: str
    settings: AlphaSettings
    regular: AlphaRegular
    dateCreated: str
    dateSubmitted: Optional[str] = None
    dateModified: str
    name: Optional[str] = None
    favorite: bool
    hidden: bool
    color: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    classifications: List[AlphaIdName] = Field(default_factory=list)
    grade: Optional[str] = None
    stage: str
    status: str
    is_: AlphaIsMetrics = Field(alias="is")
    os: Optional[AlphaOsMetrics] = None
    train: Optional[AlphaTrainTestMetrics] = None
    test: Optional[AlphaTrainTestMetrics] = None
    prod: Optional[AlphaTrainTestMetrics] = None
    competitions: Optional[List[AlphaIdName]] = None
    themes: Optional[List[AlphaThemeMultiplier]] = None
    pyramids: Optional[List[AlphaNamedMultiplier]] = None
    pyramidThemes: Optional[AlphaPyramidThemes] = None
    team: Optional[Dict[str, Any]] = None
    osmosisPoints: Optional[float] = None

    def is_atom(self) -> bool:
        """Detect atom-like alphas from classifications/tags."""
        for c in self.classifications or []:
            cid = (c.id or c.name or "")
            if isinstance(cid, str) and "SINGLE_DATA_SET" in cid:
                return True

        for t in self.tags or []:
            if isinstance(t, str) and t.strip().lower() == "atom":
                return True

        for c in self.classifications or []:
            cid = (c.id or c.name or "")
            if isinstance(cid, str) and "ATOM" in cid.upper():
                return True
        return False

    def pyramid_names(self) -> List[str]:
        """Extract pyramid names from either pyramids or pyramidThemes."""
        names: List[str] = []
        for p in self.pyramids or []:
            if p.name:
                names.append(p.name)
        if names:
            return names
        if self.pyramidThemes and self.pyramidThemes.pyramids:
            for p in self.pyramidThemes.pyramids:
                if p.name:
                    names.append(p.name)
        return names

    def __str__(self) -> str:
        region = self.settings.region.value if self.settings and self.settings.region else "-"
        lines = [
            f"alpha id: {self.id}",
            f"type: {self.type or 'UNKNOWN'}",
            f"region: {region}",
            f"stage: {self.stage or '-'}",
            f"status: {self.status or '-'}",
        ]
        if self.is_ is not None:
            lines.append(f"IS: {self.is_}")
        if self.os is not None:
            lines.append(f"OS: {self.os}")
        return "\n".join(lines)


class AlphaMixin:
    """Handles alpha details, submit, and property updates."""

    async def get_alpha_details(self, alpha_id: str) -> AlphaDetailsResponse:
        """Get detailed information about an alpha."""
        await self.ensure_authenticated()
        response = self.session.get(f"{self.base_url}/alphas/{alpha_id}")
        response.raise_for_status()
        return AlphaDetailsResponse.model_validate(parse_json_or_error(response, f"/alphas/{alpha_id}"))

    async def submit_alpha(self, alpha_id: str) -> Dict[str, Any]:
        """Submit an alpha for production."""
        await self.ensure_authenticated()
        response = self.session.post(f"{self.base_url}/alphas/{alpha_id}/submit")
        response.raise_for_status()
        return {
            "submitted": True,
            "alpha_id": alpha_id,
            "status_code": response.status_code,
        }

    async def set_alpha_properties(
        self,
        alpha_id: str,
        name: Optional[str] = None,
        color: Optional[str] = None,
        tags: Optional[List[str]] = None,
        selection_desc: Optional[str] = None,
        combo_desc: Optional[str] = None,
        regular_desc: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update alpha properties (name, color, tags, descriptions)."""
        await self.ensure_authenticated()

        payload = AlphaPropertiesPatch(
            name=name,
            color=color,
            tags=tags,
            selectionDesc=selection_desc,
            comboDesc=combo_desc,
            regular=AlphaRegularPatch(description=regular_desc) if regular_desc is not None else None,
        )
        data = payload.model_dump(exclude_none=True)

        response = self.session.patch(f"{self.base_url}/alphas/{alpha_id}", json=data)
        response.raise_for_status()
        return parse_json_or_error(response, f"/alphas/{alpha_id}")

    async def performance_comparison(
        self, alpha_id: str, team_id: Optional[str] = None, competition: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get performance comparison data for an alpha."""
        await self.ensure_authenticated()
        params = {"teamId": team_id, "competition": competition}
        params = {k: v for k, v in params.items() if v is not None}

        response = self.session.get(f"{self.base_url}/alphas/{alpha_id}/performance-comparison", params=params)
        if response.status_code == 404:
            data = parse_json_or_error(response, f"/alphas/{alpha_id}/performance-comparison")
            return {"available": False, "detail": data.get("detail", "Not found.")}
        response.raise_for_status()
        return parse_json_or_error(response, f"/alphas/{alpha_id}/performance-comparison")
