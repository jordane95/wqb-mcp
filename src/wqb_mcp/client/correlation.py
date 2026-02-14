"""Correlation mixin for BrainApiClient."""

import asyncio
from typing import Any, Dict

from ..models import CorrelatedAlpha, CorrelationCheckResponse, CorrelationCheckResult


class CorrelationMixin:
    """Handles production/self/powerpool correlation, check_correlation, submission_check."""

    async def get_production_correlation(self, alpha_id: str) -> Dict[str, Any]:
        """Get production correlation data for an alpha with retry logic."""
        await self.ensure_authenticated()

        max_retries = 5
        retry_delay = 20  # seconds

        for attempt in range(max_retries):
            try:
                self.log(f"Attempting to get production correlation for alpha {alpha_id} (attempt {attempt + 1}/{max_retries})", "INFO")

                response = self.session.get(f"{self.base_url}/alphas/{alpha_id}/correlations/prod")
                response.raise_for_status()

                text = (response.text or "").strip()
                if not text:
                    if attempt < max_retries - 1:
                        self.log(f"Empty production correlation response for {alpha_id}, retrying in {retry_delay} seconds...", "WARNING")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        self.log(f"Empty production correlation response after {max_retries} attempts for {alpha_id}", "WARNING")
                        return {}

                try:
                    correlation_data = response.json()
                    if correlation_data:
                        self.log(f"Successfully retrieved production correlation for alpha {alpha_id}", "SUCCESS")
                        return correlation_data
                    else:
                        if attempt < max_retries - 1:
                            self.log(f"Empty production correlation JSON for {alpha_id}, retrying in {retry_delay} seconds...", "WARNING")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            self.log(f"Empty production correlation JSON after {max_retries} attempts for {alpha_id}", "WARNING")
                            return {}

                except Exception as parse_err:
                    if attempt < max_retries - 1:
                        self.log(f"Production correlation JSON parse failed for {alpha_id} (attempt {attempt + 1}), retrying in {retry_delay} seconds...", "WARNING")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        self.log(f"Production correlation JSON parse failed for {alpha_id} after {max_retries} attempts: {parse_err}", "WARNING")
                        return {}

            except Exception as e:
                if attempt < max_retries - 1:
                    self.log(f"Failed to get production correlation for {alpha_id} (attempt {attempt + 1}), retrying in {retry_delay} seconds: {str(e)}", "WARNING")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    self.log(f"Failed to get production correlation for {alpha_id} after {max_retries} attempts: {str(e)}", "ERROR")
                    raise

        return {}

    async def get_self_correlation(self, alpha_id: str) -> Dict[str, Any]:
        """Get self-correlation data for an alpha with retry logic."""
        await self.ensure_authenticated()

        max_retries = 5
        retry_delay = 20  # seconds

        for attempt in range(max_retries):
            try:
                self.log(f"Attempting to get self correlation for alpha {alpha_id} (attempt {attempt + 1}/{max_retries})", "INFO")

                response = self.session.get(f"{self.base_url}/alphas/{alpha_id}/correlations/self")
                response.raise_for_status()

                text = (response.text or "").strip()
                if not text:
                    if attempt < max_retries - 1:
                        self.log(f"Empty self correlation response for {alpha_id}, retrying in {retry_delay} seconds...", "WARNING")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        self.log(f"Empty self correlation response after {max_retries} attempts for {alpha_id}", "WARNING")
                        return {}

                try:
                    correlation_data = response.json()
                    if correlation_data:
                        self.log(f"Successfully retrieved self correlation for alpha {alpha_id}", "SUCCESS")
                        return correlation_data
                    else:
                        if attempt < max_retries - 1:
                            self.log(f"Empty self correlation JSON for {alpha_id}, retrying in {retry_delay} seconds...", "WARNING")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            self.log(f"Empty self correlation JSON after {max_retries} attempts for {alpha_id}", "WARNING")
                            return {}

                except Exception as parse_err:
                    if attempt < max_retries - 1:
                        self.log(f"Self correlation JSON parse failed for {alpha_id} (attempt {attempt + 1}), retrying in {retry_delay} seconds...", "WARNING")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        self.log(f"Self correlation JSON parse failed for {alpha_id} after {max_retries} attempts: {parse_err}", "WARNING")
                        return {}

            except Exception as e:
                if attempt < max_retries - 1:
                    self.log(f"Failed to get self correlation for {alpha_id} (attempt {attempt + 1}), retrying in {retry_delay} seconds: {str(e)}", "WARNING")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    self.log(f"Failed to get self correlation for {alpha_id} after {max_retries} attempts: {str(e)}", "ERROR")
                    raise

        return {}

    async def get_power_pool_correlation(self, alpha_id: str) -> Dict[str, Any]:
        """Get Power Pool correlation data for an alpha with retry logic."""
        await self.ensure_authenticated()

        max_retries = 5
        retry_delay = 20  # seconds

        for attempt in range(max_retries):
            try:
                self.log(f"Attempting to get Power Pool correlation for alpha {alpha_id} (attempt {attempt + 1}/{max_retries})", "INFO")

                response = self.session.get(f"{self.base_url}/alphas/{alpha_id}/correlations/power-pool")
                response.raise_for_status()

                text = (response.text or "").strip()
                if not text:
                    if attempt < max_retries - 1:
                        self.log(f"Empty Power Pool correlation response for {alpha_id}, retrying in {retry_delay} seconds...", "WARNING")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        self.log(f"Empty Power Pool correlation response after {max_retries} attempts for {alpha_id}", "WARNING")
                        return {}

                try:
                    correlation_data = response.json()
                    if correlation_data:
                        self.log(f"Successfully retrieved Power Pool correlation for alpha {alpha_id}", "SUCCESS")
                        return correlation_data
                    else:
                        if attempt < max_retries - 1:
                            self.log(f"Empty Power Pool correlation JSON for {alpha_id}, retrying in {retry_delay} seconds...", "WARNING")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            self.log(f"Empty Power Pool correlation JSON after {max_retries} attempts for {alpha_id}", "WARNING")
                            return {}

                except Exception as parse_err:
                    if attempt < max_retries - 1:
                        self.log(f"Power Pool correlation JSON parse failed for {alpha_id} (attempt {attempt + 1}), retrying in {retry_delay} seconds...", "WARNING")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        self.log(f"Power Pool correlation JSON parse failed for {alpha_id} after {max_retries} attempts: {parse_err}", "WARNING")
                        return {}

            except Exception as e:
                if attempt < max_retries - 1:
                    self.log(f"Failed to get Power Pool correlation for {alpha_id} (attempt {attempt + 1}), retrying in {retry_delay} seconds: {str(e)}", "WARNING")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    self.log(f"Failed to get Power Pool correlation for {alpha_id} after {max_retries} attempts: {str(e)}", "ERROR")
                    raise

        return {}

    async def check_correlation(self, alpha_id: str, correlation_type: str = "both", threshold: float = 0.7) -> Dict[str, Any]:
        """Check alpha correlation against production alphas, self alphas, or both."""
        await self.ensure_authenticated()

        try:
            checks_dict = {}

            # Determine which correlations to check
            check_types = []
            if correlation_type == "both":
                check_types = ["production", "self"]
            elif correlation_type == "all":
                check_types = ["production", "self", "powerpool"]
            else:
                check_types = [correlation_type]

            all_passed = True

            for check_type in check_types:
                if check_type == "production":
                    correlation_data = await self.get_production_correlation(alpha_id)
                elif check_type == "self":
                    correlation_data = await self.get_self_correlation(alpha_id)
                elif check_type == "powerpool":
                    correlation_data = await self.get_power_pool_correlation(alpha_id)
                else:
                    continue

                # Analyze correlation data (robust to schema/records format)
                if isinstance(correlation_data, dict):
                    schema = correlation_data.get('schema') or {}
                    if isinstance(schema, dict) and schema.get('max') is not None:
                        max_correlation = float(schema['max'])
                    elif correlation_data.get('max') is not None:
                        max_correlation = float(correlation_data['max'])
                    else:
                        records = correlation_data.get('records') or []
                        if isinstance(records, list) and records:
                            candidate_max = None
                            for row in records:
                                if isinstance(row, (list, tuple)):
                                    for v in row:
                                        try:
                                            vf = float(v)
                                            if -1.0 <= vf <= 1.0:
                                                candidate_max = vf if candidate_max is None else max(candidate_max, vf)
                                        except Exception:
                                            continue
                                elif isinstance(row, dict):
                                    for key in ('correlation', 'prodCorrelation', 'selfCorrelation', 'max'):
                                        try:
                                            vf = float(row.get(key))
                                            if -1.0 <= vf <= 1.0:
                                                candidate_max = vf if candidate_max is None else max(candidate_max, vf)
                                        except Exception:
                                            continue
                            if candidate_max is None:
                                raise ValueError("Unable to derive max correlation from records")
                            max_correlation = float(candidate_max)
                        else:
                            raise KeyError("Correlation response missing 'schema.max' or top-level 'max' and no 'records' to derive from")
                else:
                    raise TypeError("Correlation data is not a dictionary")

                passes_check = max_correlation < threshold

                count = None
                top_correlations = None

                records = correlation_data.get('records', [])
                if records:
                    count = len(records)
                    top_corr_list = []
                    for record in records[:3]:
                        if isinstance(record, (list, tuple)) and len(record) >= 6:
                            top_corr_list.append(CorrelatedAlpha(
                                alpha_id=record[0],
                                correlation=record[5]
                            ))
                    if top_corr_list:
                        top_correlations = top_corr_list

                check_result = CorrelationCheckResult(
                    max_correlation=max_correlation,
                    passes_check=passes_check,
                    count=count,
                    top_correlations=top_correlations
                )

                checks_dict[check_type] = check_result

                if not passes_check:
                    all_passed = False

            response = CorrelationCheckResponse(
                alpha_id=alpha_id,
                threshold=threshold,
                correlation_type=correlation_type,
                checks=checks_dict,
                all_passed=all_passed
            )
            return response.model_dump()

        except Exception as e:
            self.log(f"Failed to check correlation: {str(e)}", "ERROR")
            raise

    async def get_submission_check(self, alpha_id: str) -> Dict[str, Any]:
        """Comprehensive pre-submission check."""
        await self.ensure_authenticated()

        try:
            correlation_checks = await self.check_correlation(alpha_id, correlation_type="both")
            alpha_details = await self.get_alpha_details(alpha_id)

            checks = {
                'correlation_checks': correlation_checks,
                'alpha_details': alpha_details,
                'all_passed': correlation_checks['all_passed']
            }

            return checks
        except Exception as e:
            self.log(f"Failed to get submission check: {str(e)}", "ERROR")
            raise
