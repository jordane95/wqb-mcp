"""Data mixin for BrainApiClient."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

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

    async def get_datasets(self, instrument_type: str = "EQUITY", region: str = "USA",
                          delay: int = 1, universe: str = "TOP3000", theme: str = "false", search: Optional[str] = None) -> DataDatasetsResponse:
        """Get available datasets."""
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
        return DataDatasetsResponse.model_validate(parse_json_or_error(response, "/data-sets"))

    async def get_datafields(self, instrument_type: str = "EQUITY", region: str = "USA",
                            delay: int = 1, universe: str = "TOP3000", theme: str = "false",
                            dataset_id: Optional[str] = None, data_type: str = "ALL",
                            search: Optional[str] = None) -> DataFieldsResponse:
        """Get available data fields, automatically paginating to fetch all results."""
        await self.ensure_authenticated()

        page_size = 50
        all_results: List[DataFieldItem] = []
        offset = 0
        total_count: Optional[int] = None

        while True:
            query = DataFieldsQuery(
                instrument_type=instrument_type,
                region=region,
                delay=delay,
                universe=universe,
                theme=theme,
                dataset_id=dataset_id,
                data_type=data_type,
                search=search,
                limit=page_size,
                offset=offset,
            )

            response = self.session.get(f"{self.base_url}/data-fields", params=query.to_params())
            response.raise_for_status()
            page = DataFieldsResponse.model_validate(parse_json_or_error(response, "/data-fields"))

            if total_count is None:
                total_count = page.count

            all_results.extend(page.results)

            if len(all_results) >= total_count or len(page.results) < page_size:
                break

            offset += page_size

        assert len(all_results) == total_count, (
            f"Pagination mismatch: fetched {len(all_results)} but API reported {total_count}"
        )
        return DataFieldsResponse(count=total_count or 0, results=all_results)
