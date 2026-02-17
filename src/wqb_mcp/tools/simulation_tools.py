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
    decay: float = 4.0,
    neutralization: str = "SUBINDUSTRY",
    truncation: float = 0.08,
    test_period: str = "P1Y0M",
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
    Create and start a single simulation on BRAIN platform.
    Use wait_for_simulation to poll until completion.
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
    """Poll a simulation until completion or error. Returns alpha details on success."""
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
    decay: float = 4.0,
    neutralization: str = "SUBINDUSTRY",
    truncation: float = 0.08,
    test_period: str = "P1Y0M",
    unit_handling: str = "VERIFY",
    nan_handling: str = "OFF",
    language: str = "FASTEXPR",
    visualization: bool = True,
    pasteurization: str = "ON",
    max_trade: str = "OFF",
    settings: Optional[List[Dict[str, Any]]] = None,
):
    """
    Batch-submit regular alpha simulations. Modes:
    - N expressions × 1 shared setting (settings=None)
    - N expressions × N settings (zipped 1:1)
    - 1 expression × M settings (broadcast)

    Use wait_for_multi_simulation to poll results.
    Use get_platform_setting_options to discover valid options.
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
    if settings is None:
        overrides = [{} for _ in alpha_expressions]
    else:
        overrides = settings
    # Broadcast: 1 expression × M settings → repeat expression M times
    if len(alpha_expressions) == 1 and len(overrides) > 1:
        alpha_expressions = alpha_expressions * len(overrides)
    if len(overrides) != len(alpha_expressions):
        raise ValueError("settings must have the same length as alpha_expressions (or use 1 expression with M settings)")
    allowed_setting_keys = set(SimulationSettings.model_fields.keys())
    allowed_input_keys = allowed_setting_keys | set(settings_key_map.keys())

    simulation_items: List[SimulationData] = []
    for idx, (expr, override) in enumerate(zip(alpha_expressions, overrides), start=1):
        if not isinstance(override, dict):
            raise ValueError(f"settings[{idx}] must be an object")
        unknown_keys = sorted(k for k in override.keys() if k not in allowed_input_keys)
        if unknown_keys:
            raise ValueError(
                f"settings[{idx}] has unsupported keys: {', '.join(unknown_keys)}"
            )
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
