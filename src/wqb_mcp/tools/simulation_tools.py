"""Simulation MCP tools."""

import asyncio
from typing import List, Optional, Sequence

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
    max_trade: str = "OFF"
):
    """
    Create multiple regular alpha simulations on BRAIN platform in a single request.

    This tool creates a multisimulation with multiple regular alpha expressions,
    waits for all simulations to complete, and returns detailed results for each alpha.

    NOTE: Multisimulations can take 8+ minutes to complete. This tool will wait
    for the entire process and return comprehensive results.
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

    Returns:
        Dictionary containing multisimulation results and individual alpha details
    """
    if len(alpha_expressions) < 2:
        raise ValueError("At least 2 alpha expressions are required")
    if len(alpha_expressions) > 8:
        raise ValueError("Maximum 8 alpha expressions allowed per request")

    multisimulation_data = []
    for alpha_expr in alpha_expressions:
        simulation_item = {
            'type': 'REGULAR',
            'settings': {
                'instrumentType': instrument_type,
                'region': region,
                'universe': universe,
                'delay': delay,
                'decay': decay,
                'neutralization': neutralization,
                'truncation': truncation,
                'pasteurization': pasteurization,
                'unitHandling': unit_handling,
                'nanHandling': nan_handling,
                'language': language,
                'visualization': visualization,
                'testPeriod': test_period,
                'maxTrade': max_trade
            },
            'regular': alpha_expr
        }
        multisimulation_data.append(simulation_item)

    response = brain_client.session.post(f"{brain_client.base_url}/simulations", json=multisimulation_data)

    if response.status_code != 201:
        raise RuntimeError(f"Failed to create multisimulation. Status: {response.status_code}")

    location = response.headers.get('Location', '')
    if not location:
        raise RuntimeError("No location header in multisimulation response")

    return str(await _wait_for_multisimulation_completion(location, len(alpha_expressions))
    )


async def _wait_for_multisimulation_completion(location: str, expected_children: int):
    """Wait for multisimulation to complete and return results"""
    print(f"Waiting for multisimulation to complete... (this may take several minutes)")
    print(f"Expected {expected_children} alpha simulations")
    print()
    children = []
    max_wait_attempts = 200
    wait_attempt = 0

    while wait_attempt < max_wait_attempts and len(children) == 0:
        wait_attempt += 1

        try:
            multisim_response = brain_client.session.get(location)
            if multisim_response.status_code == 200:
                multisim_data = multisim_response.json()
                children = multisim_data.get('children', [])

                if children:
                    break
                else:
                    retry_after = multisim_response.headers.get("Retry-After", 5)
                    wait_time = float(retry_after)
                    await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(5)
        except Exception:
            await asyncio.sleep(5)

    if not children:
        raise RuntimeError(f"Children did not appear within {max_wait_attempts} attempts (multisimulation may still be processing)")

    alpha_results = []
    for i, child_id in enumerate(children):
        try:
            child_url = child_id if child_id.startswith('http') else f"{brain_client.base_url}/simulations/{child_id}"

            finished = False
            max_alpha_attempts = 100
            alpha_attempt = 0

            while not finished and alpha_attempt < max_alpha_attempts:
                alpha_attempt += 1

                try:
                    alpha_progress = brain_client.session.get(child_url)
                    if alpha_progress.status_code == 200:
                        alpha_data = alpha_progress.json()
                        retry_after = alpha_progress.headers.get("Retry-After", 0)

                        if retry_after == 0:
                            finished = True
                            break
                        else:
                            wait_time = float(retry_after)
                            await asyncio.sleep(wait_time)
                    else:
                        await asyncio.sleep(5)
                except Exception:
                    await asyncio.sleep(5)

            if finished:
                alpha_id = alpha_data.get("alpha")
                if alpha_id:
                    alpha_details = brain_client.session.get(f"{brain_client.base_url}/alphas/{alpha_id}")
                    if alpha_details.status_code == 200:
                        alpha_detail_data = alpha_details.json()
                        alpha_results.append({
                            'alpha_id': alpha_id,
                            'location': child_url,
                            'details': alpha_detail_data
                        })
                    else:
                        alpha_results.append({
                            'alpha_id': alpha_id,
                            'location': child_url,
                            'error': f'Failed to get alpha details: {alpha_details.status_code}'
                        })
                else:
                    alpha_results.append({
                        'location': child_url,
                        'error': 'No alpha ID found in completed simulation'
                    })
            else:
                alpha_results.append({
                    'location': child_url,
                    'error': f'Alpha simulation did not complete within {max_alpha_attempts} attempts'
                })

        except Exception as e:
            alpha_results.append({
                'location': f"child_{i+1}",
                'error': str(e)
            })

    print(f"Multisimulation completed! Retrieved {len(alpha_results)} alpha results")
    return {
        'success': True,
        'message': f'Successfully created {expected_children} regular alpha simulations',
        'total_requested': expected_children,
        'total_created': len(alpha_results),
        'multisimulation_id': location.split('/')[-1],
        'multisimulation_location': location,
        'alpha_results': alpha_results
    }


@mcp.tool()
async def lookINTO_SimError_message(locations: Sequence[str]):
    """
    Fetch and parse error/status from multiple simulation locations (URLs).
    Args:
        locations: List of simulation result URLs (e.g., /simulations/{id})
    Returns:
        List of dicts with location, error message, and raw response
    """
    results = []
    for loc in locations:
        try:
            resp = brain_client.session.get(loc)
            if resp.status_code != 200:
                results.append({
                    "location": loc,
                    "error": f"HTTP {resp.status_code}",
                    "raw": resp.text
                })
                continue
            data = resp.json() if resp.text else {}
            error_msg = data.get("error") or data.get("message")
            if not data.get("alpha"):
                error_msg = error_msg or "Simulation did not get through, if you are running a multisimulation, check the other children location in your request"
            results.append({
                "location": loc,
                "error": error_msg,
                "raw": data
            })
        except Exception as e:
            results.append({
                "location": loc,
                "error": str(e),
                "raw": None
            })
    return str({"results": results})
