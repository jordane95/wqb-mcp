"""Data mixin for BrainApiClient."""

import time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from ..utils import dataframe_markdown_preview, parse_json_or_error


class DataCategoryRef(BaseModel):
    id: str
    name: str


class DataResearchPaper(BaseModel):
    type: str
    title: str
    url: str


class DataDatasetItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[DataCategoryRef] = None
    subcategory: Optional[DataCategoryRef] = None
    region: Optional[str] = None
    delay: Optional[int] = None
    universe: Optional[str] = None
    dateCoverage: Optional[float] = None
    coverage: Optional[float] = None
    valueScore: Optional[float] = None
    userCount: Optional[int] = None
    alphaCount: Optional[int] = None
    fieldCount: Optional[int] = None
    pyramidMultiplier: Optional[float] = None
    themes: List[str] = Field(default_factory=list)
    researchPapers: List[DataResearchPaper] = Field(default_factory=list)

    @field_validator("description", mode="before")
    @classmethod
    def _coerce_description(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)


class DataDatasetsResponse(BaseModel):
    count: int
    results: List[DataDatasetItem] = Field(default_factory=list)

    def __str__(self) -> str:
        return dataframe_markdown_preview(
            rows=[item.model_dump(mode="json", exclude_none=True) for item in self.results],
            preferred_cols=["id", "name", "description"],
            max_rows=5,
        )


class DataFieldType(str, Enum):
    MATRIX = "MATRIX"
    VECTOR = "VECTOR"
    GROUP = "GROUP"
    SYMBOL = "SYMBOL"
    UNIVERSE = "UNIVERSE"


class DataIdNameRef(BaseModel):
    id: str
    name: str


class DataFieldItem(BaseModel):
    id: str
    description: Optional[str] = None
    dataset: Optional[DataIdNameRef] = None
    category: Optional[DataIdNameRef] = None
    subcategory: Optional[DataIdNameRef] = None
    region: Optional[str] = None
    delay: Optional[int] = None
    universe: Optional[str] = None
    type: Optional[DataFieldType] = None
    dateCoverage: Optional[float] = None
    coverage: Optional[float] = None
    userCount: Optional[int] = None
    alphaCount: Optional[int] = None
    pyramidMultiplier: Optional[float] = None
    themes: List[str] = Field(default_factory=list)

    @field_validator("description", mode="before")
    @classmethod
    def _coerce_description(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)


class DataFieldsResponse(BaseModel):
    count: int
    results: List[DataFieldItem] = Field(default_factory=list)

    def __str__(self) -> str:
        return dataframe_markdown_preview(
            rows=[item.model_dump(mode="json", exclude_none=True) for item in self.results],
            preferred_cols=["id", "type", "description"],
            max_rows=5,
        )


class DataSetsQuery(BaseModel):
    model_config = {"extra": "forbid"}

    instrument_type: str = "EQUITY"
    region: str = "USA"
    delay: Literal[0, 1] = 1
    universe: str = "TOP3000"
    theme: Literal["false"] = "false"
    search: Optional[str] = None

    def to_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "instrumentType": self.instrument_type,
            "region": self.region,
            "delay": self.delay,
            "universe": self.universe,
            "theme": self.theme,
        }
        if self.search:
            params["search"] = self.search
        return params


class DataFieldsQuery(BaseModel):
    model_config = {"extra": "forbid"}

    instrument_type: str = "EQUITY"
    region: str = "USA"
    delay: Literal[0, 1] = 1
    universe: str = "TOP3000"
    theme: Literal["false"] = "false"
    dataset_id: Optional[str] = None
    data_type: Union[DataFieldType, Literal["ALL"]] = "ALL"
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0

    def to_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "instrumentType": self.instrument_type,
            "region": self.region,
            "delay": self.delay,
            "universe": self.universe,
            "limit": str(self.limit),
            "offset": str(self.offset),
        }
        if self.data_type != "ALL":
            params["type"] = self.data_type.value if isinstance(self.data_type, Enum) else self.data_type
        if self.dataset_id:
            params["dataset.id"] = self.dataset_id
        if self.search:
            params["search"] = self.search
        return params


class DataMixin:
    """Handles datasets and datafields."""

    @staticmethod
    def _data_cache_key_prefix(instrument_type: str, region: str, universe: str, delay: int) -> str:
        return f"data:{instrument_type}:{region}:{universe}:D{delay}"

    @staticmethod
    def _data_file_prefix(instrument_type: str, region: str, universe: str, delay: int) -> str:
        return f"data/{instrument_type}/{region}/{universe}/D{delay}"

    async def get_datasets(self, instrument_type: str = "EQUITY", region: str = "USA",
                          delay: int = 1, universe: str = "TOP3000", theme: str = "false",
                          search: Optional[str] = None, force_refresh: bool = False) -> DataDatasetsResponse:
        """Get available datasets."""
        cache_key = f"{self._data_cache_key_prefix(instrument_type, region, universe, delay)}:datasets"
        file_subpath = f"{self._data_file_prefix(instrument_type, region, universe, delay)}/datasets.csv"

        if not search and not force_refresh:
            rows = self._static_cache.read_table(cache_key)
            if rows is not None:
                return DataDatasetsResponse(count=len(rows), results=[DataDatasetItem.model_validate(r) for r in rows])

        await self.ensure_authenticated()

        query = DataSetsQuery(
            instrument_type=instrument_type,
            region=region,
            delay=delay,
            universe=universe,
            theme=theme,
            search=search,
        )

        response = self.session.get(f"{self.base_url}/data-sets", params=query.to_params())
        response.raise_for_status()
        result = DataDatasetsResponse.model_validate(parse_json_or_error(response, "/data-sets"))

        if result.count != len(result.results):
            raise RuntimeError(
                f"Datasets count mismatch: count={result.count}, got {len(result.results)}"
            )

        if not search:
            self._static_cache.write_table(
                cache_key,
                [item.model_dump(mode="json") for item in result.results],
                ttl_days=7,
                file_subpath=file_subpath,
            )
        return result

    async def get_datafields(self, instrument_type: str = "EQUITY", region: str = "USA",
                            delay: int = 1, universe: str = "TOP3000", theme: str = "false",
                            dataset_id: Optional[str] = None, data_type: str = "ALL",
                            search: Optional[str] = None, force_refresh: bool = False) -> DataFieldsResponse:
        """Get available data fields, automatically paginating to fetch all results."""
        prefix = self._data_cache_key_prefix(instrument_type, region, universe, delay)
        file_prefix = self._data_file_prefix(instrument_type, region, universe, delay)

        if dataset_id:
            safe_id = dataset_id.replace(" ", "_")
            cache_key = f"{prefix}:datafields:{safe_id}"
            file_subpath = f"{file_prefix}/dataset/{safe_id}/datafields.csv"
        else:
            cache_key = f"{prefix}:datafields"
            file_subpath = f"{file_prefix}/datafields.csv"

        if not search and not force_refresh:
            rows = self._static_cache.read_table(cache_key)
            if rows is not None:
                return DataFieldsResponse(count=len(rows), results=[DataFieldItem.model_validate(r) for r in rows])

        await self.ensure_authenticated()

        page_size = 50
        all_results: List[DataFieldItem] = []
        total_count: Optional[int] = None
        max_try = 5
        max_429_retries = 10

        # First request to get total count
        query = DataFieldsQuery(
            instrument_type=instrument_type, region=region, delay=delay,
            universe=universe, theme=theme, dataset_id=dataset_id,
            data_type=data_type, search=search, limit=page_size, offset=0,
        )
        for _ in range(max_429_retries):
            response = self.session.get(f"{self.base_url}/data-fields", params=query.to_params())
            if response.status_code != 429:
                break
            time.sleep(3)
        response.raise_for_status()
        first_page = parse_json_or_error(response, "/data-fields")
        total_count = first_page.get("count", 0)

        if total_count == 0:
            return DataFieldsResponse(count=0, results=[])

        for offset in range(0, total_count, page_size):
            query = DataFieldsQuery(
                instrument_type=instrument_type, region=region, delay=delay,
                universe=universe, theme=theme, dataset_id=dataset_id,
                data_type=data_type, search=search, limit=page_size, offset=offset,
            )
            for _ in range(max_try):
                for _ in range(max_429_retries):
                    response = self.session.get(f"{self.base_url}/data-fields", params=query.to_params())
                    if response.status_code != 429:
                        break
                    time.sleep(3)
                data = response.json()
                if "results" in data:
                    break
                time.sleep(5)
            else:
                response.raise_for_status()

            page = DataFieldsResponse.model_validate(data)
            all_results.extend(page.results)

        if len(all_results) != total_count:
            raise RuntimeError(
                f"Datafields pagination incomplete: expected {total_count}, got {len(all_results)}"
            )

        result = DataFieldsResponse(count=total_count, results=all_results)

        if not search:
            self._static_cache.write_table(
                cache_key,
                [item.model_dump(mode="json") for item in result.results],
                ttl_days=7,
                file_subpath=file_subpath,
            )
        return result
