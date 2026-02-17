"""Alpha recordsets mixin for BrainApiClient."""

import csv
import time
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field

from ..utils import parse_json_or_error


class RecordSetName(str, Enum):
    PNL = "pnl"
    SHARPE = "sharpe"
    TURNOVER = "turnover"
    DAILY_PNL = "daily-pnl"
    YEARLY_STATS = "yearly-stats"


class RecordSetSchemaProperty(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    title: str
    type: str


class RecordSetSchema(BaseModel):
    model_config = {"extra": "forbid"}

    name: RecordSetName
    title: str
    properties: List[RecordSetSchemaProperty] = Field(default_factory=list)


class AlphaRecordSetResponse(BaseModel):
    model_config = {"populate_by_name": True}

    schema_: RecordSetSchema = Field(alias="schema")
    records: List[List[Union[str, int, float, None]]] = Field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"{self.schema_.name}: {len(self.records)} rows | "
            f"{len(self.schema_.properties)} cols"
        )

    def rows_as_dicts(self) -> List[dict[str, Any]]:
        """Convert raw row arrays to dicts using schema property names."""
        keys = [prop.name for prop in self.schema_.properties]
        if not keys:
            return []

        result: List[dict[str, Any]] = []
        for row in self.records:
            result.append({key: (row[idx] if idx < len(row) else None) for idx, key in enumerate(keys)})
        return result

    def save_csv(self, path: Union[str, Path]) -> Path:
        """Save raw recordset rows to CSV using schema property names as headers."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        headers = [prop.name for prop in self.schema_.properties]
        with target.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if headers:
                writer.writerow(headers)
            writer.writerows(self.records)
        return target


class AlphaRecordsetsMixin:
    """Handles generic alpha recordsets APIs."""

    async def get_record_set_data(
        self, alpha_id: str, record_set_name: Union[RecordSetName, str]
    ) -> AlphaRecordSetResponse:
        """Get data from a specific record set."""
        await self.ensure_authenticated()

        if isinstance(record_set_name, RecordSetName):
            record_set = record_set_name
        else:
            try:
                record_set = RecordSetName(record_set_name)
            except ValueError as e:
                allowed = ", ".join(item.value for item in RecordSetName)
                raise ValueError(
                    f"Invalid record_set_name '{record_set_name}'. Allowed values: {allowed}"
                ) from e

        endpoint = f"/alphas/{alpha_id}/recordsets/{record_set.value}"
        max_retries = 30
        for _ in range(max_retries):
            response = self.session.get(f"{self.base_url}{endpoint}")
            response.raise_for_status()
            retry_after = float(response.headers.get("Retry-After", 0))
            if retry_after > 0:
                time.sleep(retry_after)
                continue
            if not response.text.strip():
                time.sleep(2)
                continue
            break
        return AlphaRecordSetResponse.model_validate(parse_json_or_error(response, endpoint))
