"""Simulation mixin for BrainApiClient."""

from time import sleep
from typing import Any, Dict

from ..models import SimulationData


class SimulationMixin:
    """Handles simulation creation."""

    async def create_simulation(self, simulation_data: SimulationData) -> Dict[str, Any]:
        """Create a new simulation on BRAIN platform."""
        await self.ensure_authenticated()

        try:
            self.log("Creating simulation...", "INFO")

            # Prepare settings based on simulation type
            settings_dict = simulation_data.settings.model_dump()

            # Remove fields based on simulation type
            if simulation_data.type == "REGULAR":
                # Remove SUPER-specific fields for REGULAR
                settings_dict.pop('selectionHandling', None)
                settings_dict.pop('selectionLimit', None)
                settings_dict.pop('componentActivation', None)

            # Filter out None values from settings
            settings_dict = {k: v for k, v in settings_dict.items() if v is not None}

            # Prepare simulation payload
            payload = {
                'type': simulation_data.type,
                'settings': settings_dict
            }

            # Add type-specific fields
            if simulation_data.type == "REGULAR":
                if simulation_data.regular:
                    payload['regular'] = simulation_data.regular
            elif simulation_data.type == "SUPER":
                if simulation_data.combo:
                    payload['combo'] = simulation_data.combo
                if simulation_data.selection:
                    payload['selection'] = simulation_data.selection

            # Filter out None values from entire payload
            payload = {k: v for k, v in payload.items() if v is not None}

            response = self.session.post(f"{self.base_url}/simulations", json=payload)
            response.raise_for_status()

            location = response.headers.get('Location', '')
            simulation_id = location.split('/')[-1] if location else None

            self.log(f"Simulation created with ID: {simulation_id}", "SUCCESS")

            while True:
                simulation_progress = self.session.get(location)
                if simulation_progress.headers.get("Retry-After", 0) == 0:
                    break
                print("Sleeping for " + simulation_progress.headers["Retry-After"] + " seconds")
                sleep(float(simulation_progress.headers["Retry-After"]))
            print("Alpha done simulating, getting alpha details")
            alpha_id = simulation_progress.json()["alpha"]
            alpha = self.session.get("https://api.worldquantbrain.com/alphas/" + alpha_id)
            result = alpha.json()
            result['note'] = "if you got a negative alpha sharpe, you can just add a minus sign in front of the last line of the Alpha to flip then think the next step."
            return result

        except Exception as e:
            self.log(f"Failed to create simulation: {str(e)}", "ERROR")
            raise
