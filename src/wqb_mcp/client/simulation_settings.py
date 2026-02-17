"""Simulation settings mixin for BrainApiClient."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from ..utils import parse_json_or_error


class SimulationSettingCombination(BaseModel):
    instrument_type: str = Field(alias="InstrumentType")
    region: str = Field(alias="Region")
    delay: int = Field(alias="Delay")
    universe: List[str] = Field(default_factory=list, alias="Universe")
    neutralization: List[str] = Field(default_factory=list, alias="Neutralization")

    def __str__(self) -> str:
        return (
            f"{self.instrument_type}/{self.region}/D{self.delay}\n"
            f"  universes: {', '.join(self.universe)}\n"
            f"  neutralization: {', '.join(self.neutralization)}"
        )


class SimulationSettingOptionsResponse(BaseModel):
    instrument_options: List[SimulationSettingCombination] = Field(default_factory=list)
    total_combinations: int
    instrument_types: List[str] = Field(default_factory=list)
    regions_by_type: Dict[str, List[str]] = Field(default_factory=dict)

    def __str__(self) -> str:
        preview = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(self.instrument_options))
        if not preview:
            preview = "(empty)"
        return (
            f"simulation setting options: combinations={self.total_combinations} | "
            f"instrument_types={','.join(self.instrument_types) if self.instrument_types else '-'}\n"
            f"{preview}"
        )


class SimulationSettingsMixin:
    """Handles get_platform_setting_options."""

    @staticmethod
    def _choice_values(items: List[Dict[str, Any]]) -> List[Any]:
        return [item["value"] for item in items if isinstance(item, dict) and "value" in item]

    async def get_platform_setting_options(self) -> SimulationSettingOptionsResponse:
        """Get available instrument types, regions, delays, universes, and neutralization options."""
        await self.ensure_authenticated()

        response = self.session.options(f"{self.base_url}/simulations")
        response.raise_for_status()

        settings_data = parse_json_or_error(response, "/simulations")
        children = settings_data["actions"]["POST"]["settings"]["children"]

        instrument_choice = children["instrumentType"]["choices"]
        region_choice = children["region"]["choices"]["instrumentType"]
        universe_choice = children["universe"]["choices"]["instrumentType"]
        delay_choice = children["delay"]["choices"]["instrumentType"]
        neutralization_choice = children["neutralization"]["choices"]["instrumentType"]

        instrument_types = self._choice_values(instrument_choice)
        combinations: List[SimulationSettingCombination] = []
        regions_by_type: Dict[str, List[str]] = {}

        for instrument in instrument_types:
            regions = self._choice_values(region_choice[instrument])
            regions_by_type[instrument] = regions

            for region in regions:
                delays = self._choice_values(delay_choice[instrument]["region"][region])
                universes = self._choice_values(universe_choice[instrument]["region"][region])
                neutralizations = self._choice_values(neutralization_choice[instrument]["region"][region])

                for delay in delays:
                    combinations.append(
                        SimulationSettingCombination.model_validate(
                            {
                                "InstrumentType": instrument,
                                "Region": region,
                                "Delay": delay,
                                "Universe": universes,
                                "Neutralization": neutralizations,
                            }
                        )
                    )

        return SimulationSettingOptionsResponse(
            instrument_options=combinations,
            total_combinations=len(combinations),
            instrument_types=instrument_types,
            regions_by_type=regions_by_type,
        )
