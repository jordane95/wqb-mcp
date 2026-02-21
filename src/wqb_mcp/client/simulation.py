"""Simulation mixin for BrainApiClient."""

import json
import logging
from asyncio import sleep as async_sleep
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, RootModel

from ..utils import parse_json_or_error

logger = logging.getLogger("wqb_mcp.client")


class SimulationSettings(BaseModel):
    model_config = {"extra": "forbid"}

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


class SimulationSettingCombination(BaseModel):
    instrumentType: str
    region: str
    delay: int
    universe: List[str] = Field(default_factory=list)
    neutralization: List[str] = Field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"{self.instrumentType}/{self.region}/D{self.delay}\n"
            f"  universes: {', '.join(self.universe)}\n"
            f"  neutralization: {', '.join(self.neutralization)}"
        )


class SimulationSettingOptionsResponse(BaseModel):
    instrument_options: List[SimulationSettingCombination] = Field(default_factory=list)
    total_combinations: int
    instrument_types: List[str] = Field(default_factory=list)
    regions_by_type: Dict[str, List[str]] = Field(default_factory=dict)

    def __str__(self) -> str:
        lines = [
            f"Platform Setting Options ({self.total_combinations} combinations)",
            f"Instrument Types: {', '.join(self.instrument_types) or '-'}",
        ]
        for inst_type, regions in self.regions_by_type.items():
            lines.append(f"  {inst_type}: regions={', '.join(regions)}")

        lines.append("")
        for i, combo in enumerate(self.instrument_options, 1):
            lines.append(
                f"  {i}. {combo.instrumentType}/{combo.region}/D{combo.delay}  "
                f"universes=[{', '.join(combo.universe)}]  "
                f"neutralization=[{', '.join(combo.neutralization)}]"
            )
        return "\n".join(lines)


class SimulationErrorLocation(BaseModel):
    model_config = {"extra": "forbid"}

    line: Optional[int] = None
    start: Optional[int] = None
    end: Optional[int] = None
    property: Optional[str] = None
    type: Optional[str] = None


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


class MultiSimulationParentSnapshot(BaseModel):
    model_config = {"extra": "forbid"}

    progress: Optional[float] = None
    children: List[str] = []
    type: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class MultiSimulationChildSnapshot(BaseModel):
    model_config = {"extra": "forbid"}

    id: Optional[str] = None
    parent: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    location: Optional[SimulationErrorLocation] = None
    alpha: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    regular: Optional[str] = None


class MultiSimulationChildResult(BaseModel):
    child_id: str
    status: str
    alpha_id: Optional[str] = None
    message: Optional[str] = None
    location: Optional[SimulationErrorLocation] = None


class MultiSimulationCreateResponse(BaseModel):
    model_config = {"extra": "forbid"}

    multi_id: str
    location: str
    retry_after: Optional[str] = None
    parent_status: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    child_results: List[MultiSimulationChildResult] = Field(default_factory=list)
    polls: int = 0

    def __str__(self) -> str:
        base = (
            f"multi simulation id: {self.multi_id} | "
            f"status={self.parent_status or 'RUNNING'} | "
            f"children={len(self.children)} | polls={self.polls}"
        )
        if not self.child_results:
            return base
        lines = [base]
        for idx, child in enumerate(self.child_results, start=1):
            msg = f" | message={child.message}" if child.message else ""
            lines.append(
                f"- child {idx} simulation_id={child.child_id} | status={child.status}{msg}"
            )
        return "\n".join(lines)


class MultiSimulationWaitResponse(BaseModel):
    model_config = {"extra": "forbid"}

    multi_id: str
    location: str
    requested: int
    children_total: int
    children_completed: int
    results: List[MultiSimulationChildResult]

    def __str__(self) -> str:
        status_counts: Dict[str, int] = {}
        for item in self.results:
            status_counts[item.status] = status_counts.get(item.status, 0) + 1
        summary = ", ".join(f"{k}:{v}" for k, v in sorted(status_counts.items())) or "-"
        preview = "\n".join(
            f"{i + 1}. {r.child_id} | {r.status} | alpha={r.alpha_id or '-'}"
            for i, r in enumerate(self.results[:5])
        )
        return (
            f"multi-simulation: {self.multi_id} | requested={self.requested} | "
            f"children={self.children_total} | complete={self.children_completed} | status={summary}"
            + (f"\n{preview}" if preview else "")
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
        """Submit a simulation and do a short poll (min 2, max 3) to catch early errors."""
        await self.ensure_authenticated()
        payload = self._build_simulation_payload(simulation_data)
        response = self.session.post(f"{self.base_url}/simulations", json=payload)
        self._raise_http_error_with_payload(response, "/simulations")

        location = response.headers.get("Location", "")
        if not location:
            raise RuntimeError("Simulation submission succeeded but no Location header was returned")

        simulation_id = location.rstrip("/").split("/")[-1]
        logger.info("Simulation submitted: %s", simulation_id)

        snapshot = SimulationSnapshot()
        retry_after: Optional[str] = None
        done = False
        min_polls = 2
        max_polls = 3
        for poll_index in range(1, max_polls + 1):
            simulation_progress = self.session.get(location)
            self._raise_http_error_with_payload(simulation_progress, "/simulations/{id}")
            snapshot_raw = parse_json_or_error(simulation_progress, "/simulations/{id}")
            snapshot = SimulationSnapshot.model_validate(snapshot_raw)
            self._raise_simulation_error_if_any(snapshot)

            retry_after = simulation_progress.headers.get("Retry-After")
            done = retry_after in (None, "0", "0.0")
            if poll_index >= min_polls and done:
                break
            if poll_index < min_polls:
                await async_sleep(float(retry_after or 1))

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
            try:
                snapshot = SimulationSnapshot.model_validate(snapshot_raw)
            except Exception as e:
                if isinstance(snapshot_raw, dict) and "children" in snapshot_raw:
                    raise ValueError(
                        "Provided id/location is a multi-simulation parent. "
                        "Use wait_for_multi_simulation for multi simulations."
                    ) from e
                raise
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

    async def create_multi_simulation(
        self,
        simulations: List[SimulationData],
    ) -> MultiSimulationCreateResponse:
        """Submit a multi-simulation and do a short parent poll (min 2, max 3 polls)."""
        if len(simulations) < 2:
            raise ValueError("At least 2 alpha expressions are required")
        if len(simulations) > 8:
            raise ValueError("Maximum 8 alpha expressions allowed per request")

        await self.ensure_authenticated()

        fixed_fields = ("instrumentType", "region", "delay", "language")
        first = simulations[0].settings
        for idx, sim in enumerate(simulations[1:], start=2):
            mismatched = [
                field
                for field in fixed_fields
                if getattr(sim.settings, field) != getattr(first, field)
            ]
            if mismatched:
                raise ValueError(
                    "One multi-simulation batch must keep "
                    "instrumentType, region, delay, language identical. "
                    f"Mismatch at simulations[{idx}].settings: {', '.join(mismatched)}."
                )

        payload: List[Dict[str, Any]] = []
        for sim_data in simulations:
            if sim_data.type != "REGULAR":
                raise ValueError("Only REGULAR simulations are supported in multi-simulation")
            payload.append(self._build_simulation_payload(sim_data))

        response = self.session.post(f"{self.base_url}/simulations", json=payload)
        self._raise_http_error_with_payload(response, "/simulations")

        location = response.headers.get("Location", "")
        if not location:
            raise RuntimeError("Multi-simulation submission succeeded but no Location header was returned")

        parent_status: Optional[str] = None
        children: List[str] = []
        child_results: List[MultiSimulationChildResult] = []
        polls = 0
        min_polls = 2
        max_polls = 3
        for poll_index in range(1, max_polls + 1):
            polls = poll_index
            parent_resp = self.session.get(location)
            self._raise_http_error_with_payload(parent_resp, "/simulations/{id}")
            parent_raw = parse_json_or_error(parent_resp, "/simulations/{id}")
            parent_snapshot = MultiSimulationParentSnapshot.model_validate(parent_raw)
            parent_status = parent_snapshot.status
            children = [str(x) for x in (parent_snapshot.children or [])]

            if poll_index >= min_polls and (children or parent_status == "ERROR"):
                break

            retry_after = parent_resp.headers.get("Retry-After")
            done = retry_after in (None, "0", "0.0")
            if poll_index >= min_polls and done:
                break
            await async_sleep(float(retry_after or 1))

        if children:
            for child_id in children:
                child_url = child_id if child_id.startswith("http") else f"{self.base_url}/simulations/{child_id}"
                child_resp = self.session.get(child_url)
                self._raise_http_error_with_payload(child_resp, "/simulations/{id}")
                child_raw = parse_json_or_error(child_resp, "/simulations/{id}")
                child_snapshot = MultiSimulationChildSnapshot.model_validate(child_raw)
                child_results.append(
                    MultiSimulationChildResult(
                        child_id=child_snapshot.id or child_id,
                        status=child_snapshot.status or "UNKNOWN",
                        alpha_id=child_snapshot.alpha,
                        message=child_snapshot.message,
                        location=child_snapshot.location,
                    )
                )

        return MultiSimulationCreateResponse(
            multi_id=location.rstrip("/").split("/")[-1],
            location=location,
            retry_after=response.headers.get("Retry-After"),
            parent_status=parent_status,
            children=children,
            child_results=child_results,
            polls=polls,
        )

    async def wait_for_multi_simulation(
        self,
        location_or_id: str,
        max_parent_polls: int = 200,
        max_child_polls: int = 200,
    ) -> MultiSimulationWaitResponse:
        """Poll a multi-simulation parent and then each child simulation until terminal state."""
        await self.ensure_authenticated()
        location = (
            location_or_id
            if location_or_id.startswith("http://") or location_or_id.startswith("https://")
            else f"{self.base_url}/simulations/{location_or_id}"
        )
        multi_id = location.rstrip("/").split("/")[-1]

        parent_snapshot = MultiSimulationParentSnapshot()
        for _ in range(max_parent_polls):
            response = self.session.get(location)
            self._raise_http_error_with_payload(response, "/simulations/{id}")
            parent_raw = parse_json_or_error(response, "/simulations/{id}")
            try:
                parent_snapshot = MultiSimulationParentSnapshot.model_validate(parent_raw)
            except Exception as e:
                if isinstance(parent_raw, dict) and "id" in parent_raw and "children" not in parent_raw:
                    raise ValueError(
                        "Provided id/location is not a multi-simulation parent. "
                        "Use wait_for_simulation for single simulations."
                    ) from e
                raise

            if parent_snapshot.children:
                break

            retry_after = response.headers.get("Retry-After")
            done = retry_after in (None, "0", "0.0")
            if done:
                break
            await async_sleep(float(retry_after or 1))

        child_ids = [str(x) for x in (parent_snapshot.children or [])]
        if not child_ids:
            # Submit-time setting validation errors return HTTP 400 on create_multi_simulation,
            # so this wait path is reached only after a parent location/id already exists.
            parent_status = (parent_snapshot.status or "").upper()
            running_statuses = {"RUNNING", "PENDING", "PROCESSING", "QUEUED", "WAITING"}
            if parent_snapshot.progress is not None or parent_status in running_statuses:
                raise RuntimeError(
                    "Multi-simulation parent is still running and children are not available yet. "
                    "Increase max_parent_polls or retry later."
                )
            raise ValueError(
                "Provided id/location is not a multi-simulation parent (no children found). "
                "Use wait_for_simulation for single simulations."
            )
        results: List[MultiSimulationChildResult] = []
        for child_id in child_ids:
            child_url = child_id if child_id.startswith("http") else f"{self.base_url}/simulations/{child_id}"
            child_snapshot = MultiSimulationChildSnapshot(id=child_id, status="UNKNOWN")

            for _ in range(max_child_polls):
                response = self.session.get(child_url)
                self._raise_http_error_with_payload(response, "/simulations/{id}")
                child_raw = parse_json_or_error(response, "/simulations/{id}")
                child_snapshot = MultiSimulationChildSnapshot.model_validate(child_raw)

                retry_after = response.headers.get("Retry-After")
                done = retry_after in (None, "0", "0.0")
                if done:
                    break
                await async_sleep(float(retry_after or 1))

            status = child_snapshot.status or ("COMPLETE" if child_snapshot.alpha else "UNKNOWN")
            results.append(
                MultiSimulationChildResult(
                    child_id=child_snapshot.id or child_id,
                    status=status,
                    alpha_id=child_snapshot.alpha,
                    message=child_snapshot.message,
                    location=child_snapshot.location,
                )
            )

        children_completed = sum(1 for item in results if item.status == "COMPLETE")
        return MultiSimulationWaitResponse(
            multi_id=multi_id,
            location=location,
            requested=len(child_ids),
            children_total=len(child_ids),
            children_completed=children_completed,
            results=results,
        )

    # --- Platform setting options ---

    @staticmethod
    def _choice_values(items: List[Dict[str, Any]]) -> List[Any]:
        return [item["value"] for item in items if isinstance(item, dict) and "value" in item]

    async def get_platform_setting_options(self, force_refresh: bool = False) -> "SimulationSettingOptionsResponse":
        """Get available instrument types, regions, delays, universes, and neutralization options."""
        cache_key = "platform_settings"

        if not force_refresh:
            cached = self._static_cache.read_dict(cache_key)
            if cached is not None:
                return SimulationSettingOptionsResponse.model_validate(cached)

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
                        SimulationSettingCombination(
                            instrumentType=instrument,
                            region=region,
                            delay=delay,
                            universe=universes,
                            neutralization=neutralizations,
                        )
                    )

        result = SimulationSettingOptionsResponse(
            instrument_options=combinations,
            total_combinations=len(combinations),
            instrument_types=instrument_types,
            regions_by_type=regions_by_type,
        )

        self._static_cache.write_dict(
            cache_key,
            result.model_dump(mode="json"),
            ttl_days=30,
            file_subpath="platform_settings/platform_settings.json",
        )
        return result
