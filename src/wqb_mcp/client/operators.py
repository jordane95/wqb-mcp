"""Operators mixin for BrainApiClient."""

from typing import List, Optional

from pydantic import BaseModel, Field

from ..utils import dataframe_markdown_preview, parse_json_or_error


class OperatorItem(BaseModel):
    name: str
    category: str
    scope: List[str] = Field(default_factory=list)
    definition: str
    description: str
    documentation: Optional[str] = None
    level: Optional[str] = None


class OperatorsResponse(BaseModel):
    operators: List[OperatorItem] = Field(default_factory=list)
    count: int

    def __str__(self) -> str:
        rows = [op.model_dump(mode="json", exclude_none=True) for op in self.operators]
        table = dataframe_markdown_preview(
            rows=rows,
            preferred_cols=["name", "definition", "description"],
            max_rows=10,
        )
        return (
            "Operators summary\n"
            f"- count: `{self.count}`\n"
            f"- preview_rows: `{min(len(rows), 10)}`\n"
            f"- preview:\n{table}"
        )


class OperatorsMixin:
    """Handles operator metadata retrieval."""

    async def get_operators(self) -> OperatorsResponse:
        """Get available operators for alpha creation."""
        await self.ensure_authenticated()
        response = self.session.get(f"{self.base_url}/operators")
        response.raise_for_status()
        operators_data = parse_json_or_error(response, "/operators")
        if isinstance(operators_data, list):
            operators_data = {"operators": operators_data, "count": len(operators_data)}
        return OperatorsResponse.model_validate(operators_data)
