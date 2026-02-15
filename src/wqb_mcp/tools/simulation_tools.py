"""Simulation MCP tools."""

from typing import Any, Dict, List, Optional

from . import mcp
from ..client import brain_client
from ..client.simulation import SimulationData, SimulationSettings


@mcp.tool()
async def create_simulation(
    type: str = "REGULAR",
    instrument_type: str = "EQUITY",
    region: str = "USA",
    universe: str = "TOP3000",
    delay: int = 1,
    decay: float = 0.0,
    neutralization: str = "NONE",
    truncation: float = 0.0,
    test_period: str = "P0Y0M",
    unit_handling: str = "VERIFY",
    nan_handling: str = "OFF",
    language: str = "FASTEXPR",
    visualization: bool = True,
    regular: Optional[str] = None,
    combo: Optional[str] = None,
    selection: Optional[str] = None,
    pasteurization: str = "ON",
    max_trade: str = "OFF",
    selection_handling: str = "POSITIVE",
    selection_limit: int = 1000,
    component_activation: str = "IS",
):
    """
    Create a new simulation on BRAIN platform.

    This tool creates and starts a simulation with your alpha code. Use this after you have your alpha formula ready.

    Args:
        type: Simulation type ("REGULAR" or "SUPER")
        instrument_type: Type of instruments (e.g., "EQUITY")
        region: Market region (e.g., "USA")
        universe: Universe of stocks (e.g., "TOP3000")
        delay: Data delay (0 or 1)
        decay: Decay value for the simulation
        neutralization: Neutralization method
        truncation: Truncation value
        test_period: Test period (e.g., "P0Y0M" for 1 year 6 months)
        unit_handling: Unit handling method
        nan_handling: NaN handling method
        language: Expression language (e.g., "FASTEXPR")
        visualization: Enable visualization
        regular: Regular simulation code (for REGULAR type)
        combo: Combo code (for SUPER type)
        selection: Selection code (for SUPER type)

    Returns:
        Simulation creation result with ID and location
    """
    settings = SimulationSettings(
        instrumentType=instrument_type,
        region=region,
        universe=universe,
        delay=delay,
        decay=decay,
        neutralization=neutralization,
        truncation=truncation,
        testPeriod=test_period,
        unitHandling=unit_handling,
        nanHandling=nan_handling,
        language=language,
        visualization=visualization,
        pasteurization=pasteurization,
        maxTrade=max_trade,
        selectionHandling=selection_handling,
        selectionLimit=selection_limit,
        componentActivation=component_activation,
    )

    sim_data = SimulationData(
        type=type,
        settings=settings,
        regular=regular,
        combo=combo,
        selection=selection
    )

    return str(await brain_client.create_simulation(sim_data))


@mcp.tool()
async def wait_for_simulation(location_or_id: str, max_polls: int = 200):
    """
    Poll a simulation until completion or error.

    Args:
        location_or_id: Simulation location URL or simulation id
        max_polls: Maximum number of polls before stopping

    Returns:
        Final simulation snapshot with completion metadata
    """
    result = await brain_client.wait_for_simulation(location_or_id, max_polls)
    if not result.done:
        return str(result)

    alpha_id = result.snapshot.alpha
    if not alpha_id:
        return str(result)

    details = await brain_client.get_alpha_details(alpha_id)
    return str(details)


@mcp.tool()
async def create_multi_simulation(
    alpha_expressions: List[str],
    instrument_type: str = "EQUITY",
    region: str = "USA",
    universe: str = "TOP3000",
    delay: int = 1,
    decay: float = 0.0,
    neutralization: str = "NONE",
    truncation: float = 0.0,
    test_period: str = "P0Y0M",
    unit_handling: str = "VERIFY",
    nan_handling: str = "OFF",
    language: str = "FASTEXPR",
    visualization: bool = True,
    pasteurization: str = "ON",
    max_trade: str = "OFF",
    settings: Optional[List[Dict[str, Any]]] = None,
):
    """
    Create multiple regular alpha simulations on BRAIN platform in a single request.

    This tool submits a multisimulation with multiple regular alpha expressions
    and returns the multisimulation id/location immediately.

    Use wait_for_multi_simulation to poll children until completion.
    Call get_platform_setting_options to get the valid options for the simulation.
    Args:
        alpha_expressions: List of alpha expressions (2-8 expressions required)
        instrument_type: Type of instruments (default: "EQUITY")
        region: Market region (default: "USA")
        universe: Universe of stocks (default: "TOP3000")
        delay: Data delay (default: 1)
        decay: Decay value (default: 0.0)
        neutralization: Neutralization method (default: "NONE")
        truncation: Truncation value (default: 0.0)
        test_period: Test period (default: "P0Y0M")
        unit_handling: Unit handling method (default: "VERIFY")
        nan_handling: NaN handling method (default: "OFF")
        language: Expression language (default: "FASTEXPR")
        visualization: Enable visualization (default: True)
        pasteurization: Pasteurization setting (default: "ON")
        max_trade: Max trade setting (default: "OFF")
        settings: Optional per-alpha settings overrides zipped with alpha_expressions.

    Returns:
        Multisimulation submission result with id and location
    """
    common_settings = SimulationSettings(
        instrumentType=instrument_type,
        region=region,
        universe=universe,
        delay=delay,
        decay=decay,
        neutralization=neutralization,
        truncation=truncation,
        testPeriod=test_period,
        unitHandling=unit_handling,
        nanHandling=nan_handling,
        language=language,
        visualization=visualization,
        pasteurization=pasteurization,
        maxTrade=max_trade,
    )
    settings_key_map = {
        "instrument_type": "instrumentType",
        "unit_handling": "unitHandling",
        "nan_handling": "nanHandling",
        "test_period": "testPeriod",
        "selection_handling": "selectionHandling",
        "selection_limit": "selectionLimit",
        "max_trade": "maxTrade",
        "component_activation": "componentActivation",
    }
    overrides = settings or [{} for _ in alpha_expressions]
    if len(overrides) != len(alpha_expressions):
        raise ValueError("settings must have the same length as alpha_expressions")

    simulation_items: List[SimulationData] = []
    for idx, (expr, override) in enumerate(zip(alpha_expressions, overrides), start=1):
        if not isinstance(override, dict):
            raise ValueError(f"settings[{idx}] must be an object")
        normalized = {settings_key_map.get(k, k): v for k, v in override.items()}
        merged = common_settings.model_dump()
        merged.update(normalized)
        per_item_settings = SimulationSettings.model_validate(merged)
        simulation_items.append(
            SimulationData(type="REGULAR", settings=per_item_settings, regular=expr)
        )

    return str(await brain_client.create_multi_simulation(simulations=simulation_items))


@mcp.tool()
async def wait_for_multi_simulation(
    location_or_id: str,
    max_parent_polls: int = 200,
    max_child_polls: int = 200,
):
    """Poll a multi-simulation parent and each child until terminal state."""
    result = await brain_client.wait_for_multi_simulation(
        location_or_id=location_or_id,
        max_parent_polls=max_parent_polls,
        max_child_polls=max_child_polls,
    )

    status_counts = {}
    for item in result.results:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
    summary = ", ".join(f"{k}:{v}" for k, v in sorted(status_counts.items())) or "-"
    lines = [
        f"multi-simulation: {result.multi_id} | requested={result.requested} | "
        f"children={result.children_total} | complete={result.children_completed} | status={summary}"
    ]
    for idx, child in enumerate(result.results, start=1):
        if child.status != "COMPLETE" or not child.alpha_id:
            if child.message:
                lines.append(
                    f"- child {idx} simulation_id={child.child_id} | status={child.status} | "
                    f"message={child.message}"
                )
            else:
                lines.append(f"- child {idx} simulation_id={child.child_id} | status={child.status}")
            continue

        details = await brain_client.get_alpha_details(child.alpha_id)
        lines.append(f"--- child {idx} simulation_id={child.child_id} complete ---")
        lines.append(str(details))

    return "\n".join(lines)
