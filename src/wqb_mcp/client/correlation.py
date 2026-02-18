"""Correlation mixin for BrainApiClient."""

import asyncio
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field
from ..utils import parse_json_or_error


class CorrelationType(str, Enum):
    PROD = "prod"
    SELF = "self"
    POWER_POOL = "power-pool"


class CorrelatedAlpha(BaseModel):
    """Represents a single correlated alpha."""
    alpha_id: str
    correlation: float


class SchemaProperty(BaseModel):
    name: str
    title: str
    type: str


class CorrelationSchema(BaseModel):
    name: str
    title: str
    properties: List[SchemaProperty] = []


class CorrelationData(BaseModel):
    """Correlation API response (shared by prod/self/powerpool)."""
    model_config = {"populate_by_name": True}

    schema_: Optional[CorrelationSchema] = Field(None, alias="schema")
    max: Optional[float] = None
    min: Optional[float] = None
    records: List[List[Union[float, str, int, None]]] = []


class CorrelationCheckResult(BaseModel):
    """Result for a single correlation type check."""
    max_correlation: Optional[float] = None
    passes_check: bool
    count: Optional[int] = None
    top_correlations: Optional[List[CorrelatedAlpha]] = None

    def __str__(self) -> str:
        status = "PASS" if self.passes_check else "FAIL"
        if self.max_correlation is None:
            parts = [f"no data, {status}"]
        else:
            parts = [f"max={self.max_correlation}, {status}"]
        if self.count is not None:
            parts.append(f"{self.count} correlated")
        if self.top_correlations:
            top = ", ".join(f"{a.alpha_id}({a.correlation})" for a in self.top_correlations)
            parts.append(f"top: {top}")
        return " | ".join(parts)


class CorrelationCheckResponse(BaseModel):
    """Complete correlation check response."""
    alpha_id: str
    threshold: float
    check_types: List[CorrelationType]
    checks: Dict[CorrelationType, CorrelationCheckResult]
    all_passed: bool

    def __str__(self) -> str:
        status = "PASS" if self.all_passed else "FAIL"
        lines = [f"Correlation check for {self.alpha_id} (threshold={self.threshold}): {status}"]
        for ct, result in self.checks.items():
            lines.append(f"- {ct.value}: {result}")
        return "\n".join(lines)

class SubmissionCheckResponse(BaseModel):
    """Comprehensive pre-submission check result."""
    alpha_id: str
    alpha_type: str
    region: str
    stage: str
    status: str
    correlation_checks: CorrelationCheckResponse
    is_checks_pass: int = 0
    is_checks_warn: int = 0
    is_checks_fail: int = 0
    is_checks_pending: int = 0
    failed_checks: List[str] = Field(default_factory=list)
    warning_checks: List[str] = Field(default_factory=list)
    all_passed: bool

    def __str__(self) -> str:
        status = "PASS" if self.all_passed else "FAIL"
        lines = [
            f"submission check for {self.alpha_id}: {status}",
            f"alpha: {self.alpha_type} | region={self.region} | stage={self.stage} | status={self.status}",
            f"IS checks: {self.is_checks_pass} PASS, {self.is_checks_warn} WARNING, "
            f"{self.is_checks_fail} FAIL, {self.is_checks_pending} PENDING",
        ]
        for f in self.failed_checks:
            lines.append(f"  [FAIL] {f}")
        for w in self.warning_checks:
            lines.append(f"  [WARNING] {w}")
        lines.append(str(self.correlation_checks))
        return "\n".join(lines)


class CorrelationMixin:
    """Handles production/self/powerpool correlation, check_correlation, submission_check."""

    async def _fetch_correlation(self, alpha_id: str, corr_type: CorrelationType) -> CorrelationData:
        """Fetch correlation data from a given endpoint with retry logic."""
        await self.ensure_authenticated()

        max_retries = 5
        retry_delay = 20
        last_error = None

        for attempt in range(max_retries):
            try:
                self.log(f"Fetching {corr_type.value} correlation for alpha {alpha_id} (attempt {attempt + 1}/{max_retries})", "INFO")

                response = self.session.get(f"{self.base_url}/alphas/{alpha_id}/correlations/{corr_type.value}")
                response.raise_for_status()

                data = parse_json_or_error(response, f"/alphas/{alpha_id}/correlations/{corr_type.value}")
                if not data:
                    last_error = ValueError(f"Empty {corr_type.value} correlation response for {alpha_id}")
                    self.log(str(last_error), "WARNING")
                    await asyncio.sleep(retry_delay)
                    continue

                self.log(f"Successfully retrieved {corr_type.value} correlation for alpha {alpha_id}", "SUCCESS")
                return CorrelationData(**data)

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    self.log(f"Failed to get {corr_type.value} correlation for {alpha_id} (attempt {attempt + 1}): {e}, retrying in {retry_delay}s...", "WARNING")
                    await asyncio.sleep(retry_delay)
                else:
                    self.log(f"Failed to get {corr_type.value} correlation for {alpha_id} after {max_retries} attempts: {e}", "ERROR")

        raise last_error

    async def check_correlation(self, alpha_id: str, check_types: List[CorrelationType] = None, threshold: float = 0.7) -> CorrelationCheckResponse:
        """Check alpha correlation against production alphas, self alphas, or both."""
        await self.ensure_authenticated()

        if check_types is None:
            check_types = [CorrelationType.PROD, CorrelationType.SELF]

        checks_dict = {}
        all_passed = True

        for check_type in check_types:
            corr_data = await self._fetch_correlation(alpha_id, check_type)

            if corr_data.max is None:
                # No correlated alphas (e.g. alpha not yet submitted) — auto-pass
                checks_dict[check_type] = CorrelationCheckResult(
                    passes_check=True,
                )
                continue

            max_correlation = corr_data.max
            passes_check = max_correlation < threshold

            count = None
            top_correlations = None

            # Only extract count and top correlated alphas from self/powerpool (not prod histogram)
            is_self_type = corr_data.schema_ and corr_data.schema_.name == "selfCorrelation"
            if is_self_type and corr_data.records:
                count = len(corr_data.records)
                top_corr_list = []
                for record in corr_data.records[:3]:
                    if len(record) >= 6:
                        top_corr_list.append(CorrelatedAlpha(
                            alpha_id=record[0],
                            correlation=record[5]
                        ))
                if top_corr_list:
                    top_correlations = top_corr_list

            checks_dict[check_type] = CorrelationCheckResult(
                max_correlation=max_correlation,
                passes_check=passes_check,
                count=count,
                top_correlations=top_correlations
            )

            if not passes_check:
                all_passed = False

        return CorrelationCheckResponse(
            alpha_id=alpha_id,
            threshold=threshold,
            check_types=check_types,
            checks=checks_dict,
            all_passed=all_passed
        )

    async def get_submission_check(self, alpha_id: str, is_power_pool: bool = False) -> SubmissionCheckResponse:
        """Comprehensive pre-submission check.

        Args:
            alpha_id: The ID of the alpha to check.
            is_power_pool: If True, applies Power Pool correlation rules (threshold=0.5, 10% Sharpe rule).
        """
        await self.ensure_authenticated()

        # Apply different correlation rules based on alpha type
        if is_power_pool:
            # Power Pool: check power-pool correlation with threshold=0.5
            correlation_checks = await self.check_correlation(
                alpha_id,
                check_types=[CorrelationType.POWER_POOL],
                threshold=0.5
            )

            # Apply 10% Sharpe rule if PP correlation > 0.5
            pp_check = correlation_checks.checks.get(CorrelationType.POWER_POOL)
            if pp_check and pp_check.max_correlation is not None and pp_check.max_correlation > 0.5:
                # Get current alpha's Sharpe
                alpha = await self.get_alpha_details(alpha_id)
                current_sharpe = alpha.is_.sharpe if alpha.is_ else None

                # Get the most correlated PP alpha's Sharpe
                if pp_check.top_correlations and current_sharpe is not None:
                    most_correlated_id = pp_check.top_correlations[0].alpha_id
                    correlated_alpha = await self.get_alpha_details(most_correlated_id)
                    correlated_sharpe = correlated_alpha.is_.sharpe if correlated_alpha.is_ else None

                    if correlated_sharpe is not None:
                        # Check if current alpha's Sharpe is 10% higher
                        if current_sharpe >= 1.1 * correlated_sharpe:
                            # Override the check to pass
                            pp_check.passes_check = True
                            correlation_checks.all_passed = True
                            self.log(
                                f"Power Pool correlation > 0.5 but Sharpe is 10% higher "
                                f"({current_sharpe:.4f} >= 1.1 × {correlated_sharpe:.4f}), check passes",
                                "INFO"
                            )
        else:
            # Regular alpha: check prod + self correlation with threshold=0.7
            correlation_checks = await self.check_correlation(alpha_id)

        alpha = await self.get_alpha_details(alpha_id)

        def _format_check(c) -> str:
            detail = c.name
            if hasattr(c, "limit") and hasattr(c, "value"):
                detail += f" (limit={c.limit}, value={c.value})"
            elif hasattr(c, "message"):
                detail += f" ({c.message})"
            return detail

        checks = alpha.is_.checks if alpha.is_ else []
        failed = [c for c in checks if c.result == "FAIL"]
        warned = [c for c in checks if c.result == "WARNING"]
        passed = [c for c in checks if c.result == "PASS"]
        pending = [c for c in checks if c.result == "PENDING"]

        region = alpha.settings.region.value if alpha.settings and alpha.settings.region else "-"

        return SubmissionCheckResponse(
            alpha_id=alpha_id,
            alpha_type=alpha.type,
            region=region,
            stage=alpha.stage,
            status=alpha.status,
            correlation_checks=correlation_checks,
            is_checks_pass=len(passed),
            is_checks_warn=len(warned),
            is_checks_fail=len(failed),
            is_checks_pending=len(pending),
            failed_checks=[_format_check(c) for c in failed],
            warning_checks=[_format_check(c) for c in warned],
            all_passed=correlation_checks.all_passed and len(failed) == 0 and len(pending) == 0,
        )
