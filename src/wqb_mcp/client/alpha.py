"""Alpha management mixin for BrainApiClient."""
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from asyncio import sleep as async_sleep

from pydantic import BaseModel, Field, TypeAdapter, model_validator
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


# -- Alpha check models (discriminated by field presence) --
# The API returns checks with varying shapes; Pydantic tries each variant
# in Union order and picks the first match.  More-specific models must
# come before less-specific ones.

class AlphaCheckBase(BaseModel):
    """Fallback for simple pass/fail checks (e.g. CONCENTRATED_WEIGHT, POWER_POOL_CORRELATION)."""
    model_config = {"extra": "forbid"}

    name: str
    result: str


class AlphaCheckLimitValue(AlphaCheckBase):
    """Checks with a numeric threshold and actual value (e.g. LOW_SHARPE, HIGH_TURNOVER, CONCENTRATED_WEIGHT)."""
    limit: float
    value: Optional[float] = None
    date: Optional[str] = None


class AlphaCheckLimitValueRatio(AlphaCheckLimitValue):
    """Limit/value checks that also carry a ratio (e.g. LOW_SUB_UNIVERSE_SHARPE)."""
    ratio: float


class AlphaCheckLadder(AlphaCheckLimitValue):
    """Time-windowed limit/value checks (e.g. IS_LADDER_SHARPE)."""
    year: int
    startDate: str
    endDate: str


class AlphaCheckCompetitions(AlphaCheckBase):
    """Lists competitions the alpha qualifies for."""
    competitions: List[AlphaIdName]


class AlphaCheckPyramids(AlphaCheckBase):
    """Pyramid category matching result (MATCHES_PYRAMID)."""
    effective: int
    multiplier: float
    pyramids: List[AlphaNamedMultiplier]


class AlphaCheckThemes(AlphaCheckBase):
    """Theme matching result (MATCHES_THEMES)."""
    themes: List[AlphaThemeMultiplier]
    multiplier: Optional[float] = None


class AlphaCheckMessage(AlphaCheckBase):
    """Checks that carry a descriptive message (e.g. UNITS validation warnings)."""
    message: str


AlphaCheck = Union[
    AlphaCheckLimitValueRatio,
    AlphaCheckLadder,
    AlphaCheckLimitValue,
    AlphaCheckCompetitions,
    AlphaCheckPyramids,
    AlphaCheckThemes,
    AlphaCheckMessage,
    AlphaCheckBase,
]

_AlphaCheckAdapter = TypeAdapter(AlphaCheck)


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
    fitness: Optional[float] = None
    startDate: Optional[str] = None

    def __str__(self) -> str:
        fitness_str = f"{self.fitness:.4f}" if self.fitness is not None else "None"
        return (
            f"sharpe={self.sharpe:.4f} fitness={fitness_str} "
            f"pnl={self.pnl:.4f} bookSize={self.bookSize:.4f} "
            f"longCount={self.longCount} shortCount={self.shortCount} "
            f"turnover={self.turnover:.4f} returns={self.returns:.4f} "
            f"drawdown={self.drawdown:.4f} margin={self.margin:.4f}"
        )


class AlphaIsMetrics(AlphaPerformanceBlock):
    glbAmer: Optional[AlphaPerformanceBlock] = None
    glbApac: Optional[AlphaPerformanceBlock] = None
    glbEmea: Optional[AlphaPerformanceBlock] = None
    investabilityConstrained: Optional[AlphaPerformanceBlock] = None
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
        # Expression
        if self.regular:
            lines.append(f"expression: {self.regular.code}")
        # Settings
        if self.settings:
            s = self.settings
            lines.append(
                f"settings: universe={s.universe.value} delay={s.delay} decay={s.decay} "
                f"neutralization={s.neutralization} truncation={s.truncation} "
                f"instrumentType={s.instrumentType} nanHandling={s.nanHandling} "
                f"pasteurization={s.pasteurization}"
            )
        if self.is_ is not None:
            lines.append(f"IS: {self.is_}")
        if self.os is not None:
            lines.append(f"OS: {self.os}")
        return "\n".join(lines)


class SubmitAlphaResponse(BaseModel):
    """Result of POST /alphas/{alpha_id}/submit.

    Full lifecycle:
    - 201: checks running → poll GET Location until resolved
    - 200 poll (no Retry-After): all checks passed → submitted
    - 403 poll or direct: checks resolved with FAILs
    - 403 direct: ALREADY_SUBMITTED
    - 404: alpha not found
    """

    alpha_id: str
    submitted: bool
    status_code: int
    location: Optional[str] = None
    polls: int = 0
    checks: List[AlphaCheck] = Field(default_factory=list)
    detail: Optional[str] = None

    def __str__(self) -> str:
        if self.submitted:
            return f"alpha {self.alpha_id}: submitted ({self.polls} polls)"
        parts = [f"alpha {self.alpha_id}: FAILED (HTTP {self.status_code})"]
        if self.detail:
            parts.append(f"  detail: {self.detail}")
        for c in self.checks:
            if c.result == "FAIL":
                parts.append(f"  - {c.name}: {c.result}")
        if self.polls:
            parts.append(f"  polls: {self.polls}")
        return "\n".join(parts)


class AlphaCheckResponse(BaseModel):
    """Result of GET /alphas/{alpha_id}/check.

    Polling lifecycle:
    - 200 with Retry-After → checks still running, keep polling
    - 200 without Retry-After → checks complete, body has is.checks[]
    - 403 → checks resolved with failures
    - 404 → alpha not found
    """

    alpha_id: str
    ready: bool
    status_code: int
    polls: int = 0
    checks: List[AlphaCheck] = Field(default_factory=list)
    pass_count: int = 0
    warn_count: int = 0
    fail_count: int = 0
    pending_count: int = 0
    failed_checks: List[str] = Field(default_factory=list)
    warning_checks: List[str] = Field(default_factory=list)
    detail: Optional[str] = None

    def __str__(self) -> str:
        status = "READY" if self.ready else "NOT READY"
        lines = [f"alpha {self.alpha_id} check: {status}"]
        lines.append(
            f"  {self.pass_count} PASS, {self.warn_count} WARNING, "
            f"{self.fail_count} FAIL, {self.pending_count} PENDING"
        )
        if self.detail:
            lines.append(f"  detail: {self.detail}")
        for f in self.failed_checks:
            lines.append(f"  [FAIL] {f}")
        for w in self.warning_checks:
            lines.append(f"  [WARNING] {w}")
        # Show pyramid/theme info from PASS checks
        for c in self.checks:
            if isinstance(c, AlphaCheckPyramids) and c.result == "PASS":
                pyrs = ", ".join(f"{p.name}(x{p.multiplier})" for p in c.pyramids)
                lines.append(f"  [PYRAMID] effective={c.effective} multiplier={c.multiplier} | {pyrs}")
            if isinstance(c, AlphaCheckThemes) and c.result == "PASS":
                themes = ", ".join(f"{t.name}(x{t.multiplier})" for t in c.themes)
                lines.append(f"  [THEMES] {themes}")
        return "\n".join(lines)


class AlphaMixin:
    """Handles alpha details, submit, check, and property updates."""

    async def get_alpha_details(self, alpha_id: str) -> AlphaDetailsResponse:
        """Get detailed information about an alpha."""
        await self.ensure_authenticated()
        response = self.session.get(f"{self.base_url}/alphas/{alpha_id}")
        response.raise_for_status()
        return AlphaDetailsResponse.model_validate(parse_json_or_error(response, f"/alphas/{alpha_id}"))

    async def check_alpha(self, alpha_id: str, max_polls: int = 60) -> AlphaCheckResponse:
        """Call GET /alphas/{alpha_id}/check with polling.

        The platform runs server-side submission-readiness checks (Sharpe,
        turnover, correlation, pyramid, themes, etc.) and returns results
        via a Retry-After polling pattern.

        Args:
            alpha_id: The ID of the alpha to check.
            max_polls: Maximum polling attempts (default 60).
        """
        await self.ensure_authenticated()
        url = f"{self.base_url}/alphas/{alpha_id}/check"

        for poll_index in range(max_polls):
            response = self.session.get(url)

            if response.status_code == 404:
                return AlphaCheckResponse(
                    alpha_id=alpha_id, ready=False, status_code=404,
                    detail="Alpha not found.",
                )

            if response.status_code == 403:
                return self._parse_check_response(alpha_id, response, poll_index)

            response.raise_for_status()

            retry_after = response.headers.get("Retry-After")
            done = retry_after in (None, "0", "0.0")

            if done:
                return self._parse_check_response(alpha_id, response, poll_index)

            self.log(
                f"Alpha {alpha_id} check running (poll {poll_index + 1}/{max_polls}), "
                f"retry-after={retry_after}s",
                "INFO",
            )
            await async_sleep(float(retry_after or 1))

        return AlphaCheckResponse(
            alpha_id=alpha_id, ready=False, status_code=200, polls=max_polls,
            detail=f"Checks still running after {max_polls} polls.",
        )

    def _parse_check_response(
        self, alpha_id: str, response, polls: int,
    ) -> AlphaCheckResponse:
        """Parse body of GET /alphas/{alpha_id}/check."""
        body = parse_json_or_error(response, f"/alphas/{alpha_id}/check")
        checks_raw = (body.get("is") or {}).get("checks") or []
        parsed = [_AlphaCheckAdapter.validate_python(c) for c in checks_raw]

        failed = [c for c in parsed if c.result == "FAIL"]
        warned = [c for c in parsed if c.result == "WARNING"]
        passed = [c for c in parsed if c.result == "PASS"]
        pending = [c for c in parsed if c.result == "PENDING"]

        return AlphaCheckResponse(
            alpha_id=alpha_id,
            ready=len(failed) == 0 and len(pending) == 0,
            status_code=response.status_code,
            polls=polls,
            checks=parsed,
            pass_count=len(passed),
            warn_count=len(warned),
            fail_count=len(failed),
            pending_count=len(pending),
            failed_checks=[self._fmt_check(c) for c in failed],
            warning_checks=[self._fmt_check(c) for c in warned],
        )

    @staticmethod
    def _fmt_check(c) -> str:
        detail = c.name
        if hasattr(c, "limit") and c.limit is not None:
            detail += f" (limit={c.limit}"
            if hasattr(c, "value") and c.value is not None:
                detail += f", value={c.value}"
            detail += ")"
        elif hasattr(c, "message") and c.message is not None:
            detail += f" ({c.message})"
        return detail

    async def submit_alpha(self, alpha_id: str, max_polls: int = 60) -> SubmitAlphaResponse:
        """Submit an alpha and poll until checks resolve."""
        await self.ensure_authenticated()
        response = self.session.post(f"{self.base_url}/alphas/{alpha_id}/submit")
        if response.status_code not in (201, 403, 404):
            response.raise_for_status()

        # 404 — not found
        if response.status_code == 404:
            body = parse_json_or_error(response, f"/alphas/{alpha_id}/submit")
            return SubmitAlphaResponse(
                alpha_id=alpha_id, submitted=False, status_code=404,
                detail=body.get("detail", "Not found."),
            )

        # 403 direct — checks already resolved (e.g. ALREADY_SUBMITTED, stale checks)
        if response.status_code == 403:
            return self._parse_submit_checks(alpha_id, response, polls=0)

        # 201 — checks running, poll Location
        if response.status_code == 201:
            location = response.headers.get("Location", "")
            # API returns http:// but server requires https://
            if location.startswith("http://"):
                location = "https://" + location[len("http://"):]
            if not location:
                return SubmitAlphaResponse(
                    alpha_id=alpha_id, submitted=True, status_code=201,
                )
            retry_after = response.headers.get("Retry-After", "1")
            for poll_index in range(1, max_polls + 1):
                await async_sleep(float(retry_after or 1))
                poll_resp = self.session.get(location)
                retry_after = poll_resp.headers.get("Retry-After")
                done = retry_after in (None, "0", "0.0")

                # 403 — checks resolved with failures
                if poll_resp.status_code == 403:
                    return self._parse_submit_checks(alpha_id, poll_resp, polls=poll_index)

                # 404 — submit endpoint gone, alpha moved to OS (success)
                if poll_resp.status_code == 404:
                    return SubmitAlphaResponse(
                        alpha_id=alpha_id, submitted=True, status_code=200,
                        polls=poll_index,
                    )

                # 200 with no Retry-After — all checks passed
                if poll_resp.status_code == 200 and done:
                    return SubmitAlphaResponse(
                        alpha_id=alpha_id, submitted=True, status_code=200,
                        location=location, polls=poll_index,
                    )

                # 200 with Retry-After — still running, continue
            # Exhausted polls
            return SubmitAlphaResponse(
                alpha_id=alpha_id, submitted=False, status_code=200,
                location=location, polls=max_polls,
                detail=f"Checks still running after {max_polls} polls.",
            )

    def _parse_submit_checks(
        self, alpha_id: str, response, polls: int
    ) -> SubmitAlphaResponse:
        """Parse a 403 submit response with is.checks[]."""
        body = parse_json_or_error(response, f"/alphas/{alpha_id}/submit")
        checks_raw = (body.get("is") or {}).get("checks") or []
        return SubmitAlphaResponse(
            alpha_id=alpha_id,
            submitted=False,
            status_code=403,
            polls=polls,
            checks=[_AlphaCheckAdapter.validate_python(c) for c in checks_raw],
        )

    async def set_alpha_properties(
        self,
        alpha_id: str,
        name: Optional[str] = None,
        color: Optional[str] = None,
        tags: Optional[List[str]] = None,
        selection_desc: Optional[str] = None,
        combo_desc: Optional[str] = None,
        regular_desc: Optional[str] = None,
    ) -> AlphaDetailsResponse:
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
        return AlphaDetailsResponse.model_validate(parse_json_or_error(response, f"/alphas/{alpha_id}"))

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
