"""Simulation mixin for BrainApiClient."""

import json
from asyncio import sleep as async_sleep
from typing import Any, Dict, Optional

from pydantic import BaseModel, RootModel

from ..utils import parse_json_or_error


class SimulationSettings(BaseModel):
    instrumentType: str = "EQUITY"
    region: str = "USA"
    universe: str = "TOP3000"
    delay: int = 1
    decay: float = 0.0
    neutralization: str = "NONE"
    truncation: float = 0.0
    pasteurization: str = "ON"
    unitHandling: str = "VERIFY"
    nanHandling: str = "OFF"
    language: str = "FASTEXPR"
    visualization: bool = True
    testPeriod: str = "P0Y0M"
    selectionHandling: str = "POSITIVE"
    selectionLimit: int = 1000
    maxTrade: str = "OFF"
    componentActivation: str = "IS"


class SimulationData(BaseModel):
    type: str = "REGULAR"
    settings: SimulationSettings
    regular: Optional[str] = None
    combo: Optional[str] = None
    selection: Optional[str] = None


class SimulationErrorLocation(BaseModel):
    model_config = {"extra": "forbid"}

    line: Optional[int] = None
    start: Optional[int] = None
    end: Optional[int] = None
    property: Optional[str] = None


class SimulationSnapshot(BaseModel):
    model_config = {"extra": "forbid"}

    progress: Optional[float] = None
    id: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    location: Optional[SimulationErrorLocation] = None
    alpha: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    regular: Optional[str] = None

    def __str__(self) -> str:
        return self.model_dump_json(exclude_none=True)


class SimulationCreateResponse(BaseModel):
    model_config = {"extra": "forbid"}

    simulation_id: str
    location: str
    retry_after: Optional[str] = None
    done: bool
    snapshot: SimulationSnapshot

    def __str__(self) -> str:
        return f"simulation id: {self.simulation_id}"


class SimulationWaitResponse(BaseModel):
    model_config = {"extra": "forbid"}

    simulation_id: str
    location: str
    polls: int
    done: bool
    snapshot: SimulationSnapshot
    message: Optional[str] = None

    def __str__(self) -> str:
        if not self.done:
            return self.message or "Simulation not finished."
        return (
            f"alpha id: {self.snapshot.alpha}"
            if self.snapshot.alpha
            else "Simulation finished but alpha id is missing."
        )


class SuperSelectionQuery(BaseModel):
    model_config = {"extra": "forbid"}

    selection: str
    instrument_type: str = "EQUITY"
    region: str = "USA"
    delay: int = 1
    selection_limit: int = 1000
    selection_handling: str = "POSITIVE"

    def to_params(self) -> Dict[str, Any]:
        return {
            "selection": self.selection,
            "instrumentType": self.instrument_type,
            "region": self.region,
            "delay": self.delay,
            "selectionLimit": self.selection_limit,
            "selectionHandling": self.selection_handling,
        }


class SuperSelectionResponse(RootModel[Dict[str, Any]]):
    def __str__(self) -> str:
        return str(self.root)


class SimulationMixin:
    """Handles simulation creation."""

    @staticmethod
    def _build_simulation_payload(simulation_data: SimulationData) -> Dict[str, Any]:
        settings_dict = simulation_data.settings.model_dump()
        if simulation_data.type == "REGULAR":
            settings_dict.pop("selectionHandling", None)
            settings_dict.pop("selectionLimit", None)
            settings_dict.pop("componentActivation", None)
        settings_dict = {k: v for k, v in settings_dict.items() if v is not None}

        payload: Dict[str, Any] = {"type": simulation_data.type, "settings": settings_dict}
        if simulation_data.type == "REGULAR":
            if simulation_data.regular:
                payload["regular"] = simulation_data.regular
        elif simulation_data.type == "SUPER":
            if simulation_data.combo:
                payload["combo"] = simulation_data.combo
            if simulation_data.selection:
                payload["selection"] = simulation_data.selection
        return {k: v for k, v in payload.items() if v is not None}

    @staticmethod
    def _raise_http_error_with_payload(response: Any, endpoint: str) -> None:
        if response.status_code < 400:
            return
        try:
            payload = parse_json_or_error(response, endpoint)
            detail = json.dumps(payload, ensure_ascii=False)
        except Exception:
            detail = (response.text or "")[:500]
        raise RuntimeError(
            f"Request failed at {endpoint} | status={response.status_code} | detail={detail}"
        )

    @staticmethod
    def _raise_simulation_error_if_any(snapshot: SimulationSnapshot) -> None:
        if snapshot.status != "ERROR":
            return
        raise RuntimeError(f"Simulation error payload: {snapshot}")

    async def create_simulation(self, simulation_data: SimulationData) -> SimulationCreateResponse:
        """Submit a simulation and poll once for immediate status snapshot."""
        await self.ensure_authenticated()
        payload = self._build_simulation_payload(simulation_data)
        response = self.session.post(f"{self.base_url}/simulations", json=payload)
        self._raise_http_error_with_payload(response, "/simulations")

        location = response.headers.get("Location", "")
        if not location:
            raise RuntimeError("Simulation submission succeeded but no Location header was returned")

        simulation_id = location.rstrip("/").split("/")[-1]
        self.log(f"Simulation submitted: {simulation_id}", "SUCCESS")

        simulation_progress = self.session.get(location)
        self._raise_http_error_with_payload(simulation_progress, "/simulations/{id}")
        snapshot_raw = parse_json_or_error(simulation_progress, "/simulations/{id}")
        snapshot = SimulationSnapshot.model_validate(snapshot_raw)
        self._raise_simulation_error_if_any(snapshot)

        retry_after = simulation_progress.headers.get("Retry-After")
        done = retry_after in (None, "0", "0.0")
        return SimulationCreateResponse(
            simulation_id=simulation_id,
            location=location,
            retry_after=retry_after,
            done=done,
            snapshot=snapshot,
        )

    async def wait_for_simulation(self, location_or_id: str, max_polls: int = 200) -> SimulationWaitResponse:
        """Poll simulation status until completion or error."""
        await self.ensure_authenticated()
        location = (
            location_or_id
            if location_or_id.startswith("http://") or location_or_id.startswith("https://")
            else f"{self.base_url}/simulations/{location_or_id}"
        )
        simulation_id = location.rstrip("/").split("/")[-1]

        last_snapshot: Optional[SimulationSnapshot] = None
        for poll_index in range(1, max_polls + 1):
            response = self.session.get(location)
            self._raise_http_error_with_payload(response, "/simulations/{id}")
            snapshot_raw = parse_json_or_error(response, "/simulations/{id}")
            snapshot = SimulationSnapshot.model_validate(snapshot_raw)
            self._raise_simulation_error_if_any(snapshot)
            last_snapshot = snapshot

            retry_after = response.headers.get("Retry-After")
            done = retry_after in (None, "0", "0.0")
            if done:
                return SimulationWaitResponse(
                    simulation_id=simulation_id,
                    location=location,
                    polls=poll_index,
                    done=True,
                    snapshot=snapshot,
                )
            await async_sleep(float(retry_after or 1))

        return SimulationWaitResponse(
            simulation_id=simulation_id,
            location=location,
            polls=max_polls,
            done=False,
            snapshot=last_snapshot or SimulationSnapshot(),
            message=f"Reached max_polls={max_polls} before completion.",
        )

    async def run_selection(
        self,
        selection: str,
        instrument_type: str = "EQUITY",
        region: str = "USA",
        delay: int = 1,
        selection_limit: int = 1000,
        selection_handling: str = "POSITIVE",
    ) -> SuperSelectionResponse:
        """Run a selection query to filter instruments."""
        await self.ensure_authenticated()
        query = SuperSelectionQuery(
            selection=selection,
            instrument_type=instrument_type,
            region=region,
            delay=delay,
            selection_limit=selection_limit,
            selection_handling=selection_handling,
        )
        response = self.session.get(f"{self.base_url}/simulations/super-selection", params=query.to_params())
        response.raise_for_status()
        return SuperSelectionResponse.model_validate(
            parse_json_or_error(response, "/simulations/super-selection")
        )
