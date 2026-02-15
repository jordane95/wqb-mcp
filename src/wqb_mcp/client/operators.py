"""Operators mixin for BrainApiClient."""

from typing import Any, Dict
from .common import parse_json_or_error


class OperatorsMixin:
    """Handles get_operators and run_selection."""

    async def get_operators(self) -> Dict[str, Any]:
        """Get available operators for alpha creation."""
        await self.ensure_authenticated()
        try:
            response = self.session.get(f"{self.base_url}/operators")
            response.raise_for_status()
            operators_data = parse_json_or_error(response, "/operators")

            if isinstance(operators_data, list):
                return {"operators": operators_data, "count": len(operators_data)}
            else:
                return operators_data
        except Exception as e:
            self.log(f"Failed to get operators: {str(e)}", "ERROR")
            raise

    async def run_selection(
        self,
        selection: str,
        instrument_type: str = "EQUITY",
        region: str = "USA",
        delay: int = 1,
        selection_limit: int = 1000,
        selection_handling: str = "POSITIVE"
    ) -> Dict[str, Any]:
        """Run a selection query to filter instruments."""
        await self.ensure_authenticated()
        try:
            selection_data = {
                "selection": selection,
                "instrumentType": instrument_type,
                "region": region,
                "delay": delay,
                "selectionLimit": selection_limit,
                "selectionHandling": selection_handling
            }

            response = self.session.get(f"{self.base_url}/simulations/super-selection", params=selection_data)
            response.raise_for_status()
            return parse_json_or_error(response, "/simulations/super-selection")
        except Exception as e:
            self.log(f"Failed to run selection: {str(e)}", "ERROR")
            raise
