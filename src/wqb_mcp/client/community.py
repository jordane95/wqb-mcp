"""Community mixin for BrainApiClient."""

from collections import Counter
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..utils import parse_json_or_error


class UserSelfLite(BaseModel):
    id: str


class EventItem(BaseModel):
    id: str
    title: str
    type: Optional[str] = None
    category: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None
    register: Optional[str] = None
    venue: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class EventsResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[EventItem] = Field(default_factory=list)

    def __str__(self) -> str:
        if not self.results:
            return f"events: count={self.count}"
        lines = [f"events: count={self.count}"]
        for i, event in enumerate(self.results[:3], start=1):
            lines.append(
                f"{i}. {event.id} | {event.title} | start={event.start or '-'} | "
                f"type={event.type or '-'} | tz={event.timezone or '-'}"
            )
        return "\n".join(lines)


class LeaderboardEntry(BaseModel):
    user: str
    weightFactor: Optional[float] = None
    valueFactor: Optional[float] = None
    dailyOsmosisRank: Optional[float] = None
    dataFieldsUsed: Optional[int] = None
    submissionsCount: Optional[int] = None
    meanProdCorrelation: Optional[float] = None
    meanSelfCorrelation: Optional[float] = None
    superAlphaSubmissionsCount: Optional[int] = None
    superAlphaMeanProdCorrelation: Optional[float] = None
    superAlphaMeanSelfCorrelation: Optional[float] = None
    university: Optional[str] = None
    country: Optional[str] = None


class LeaderboardResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[LeaderboardEntry] = Field(default_factory=list)

    def __str__(self) -> str:
        if not self.results:
            return f"leaderboard: count={self.count}"
        me = self.results[0]
        return (
            f"leaderboard: count={self.count}\n"
            f"user={me.user} | valueFactor={me.valueFactor} | submissions={me.submissionsCount} | "
            f"meanProdCorr={me.meanProdCorrelation} | country={me.country or '-'}"
        )


class CompetitionItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    universities: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    excludedCountries: Optional[List[str]] = None
    status: Optional[str] = None
    teamBased: Optional[bool] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    signUpStartDate: Optional[str] = None
    signUpEndDate: Optional[str] = None
    signUpDate: Optional[str] = None
    team: Optional[Dict[str, Any]] = None
    scoring: Optional[str] = None
    leaderboard: Optional[Dict[str, Any]] = None
    prizeBoard: Optional[bool] = None
    universityBoard: Optional[bool] = None
    submissions: Optional[bool] = None
    faq: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None


class UserCompetitionsResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[CompetitionItem] = Field(default_factory=list)

    def __str__(self) -> str:
        if not self.results:
            return f"user competitions: count={self.count}"
        lines = [f"user competitions: count={self.count}"]
        for i, comp in enumerate(self.results[:3], start=1):
            lines.append(
                f"{i}. {comp.id} | {comp.name} | status={comp.status or '-'} | "
                f"start={comp.startDate or '-'} | end={comp.endDate or '-'} | "
                f"scoring={comp.scoring or '-'}"
            )
        return "\n".join(lines)


class CompetitionDetailsResponse(CompetitionItem):
    def __str__(self) -> str:
        return (
            f"competition: {self.id}\n"
            f"name: {self.name}\n"
            f"status: {self.status or '-'}\n"
            f"scoring: {self.scoring or '-'}\n"
            f"period: {self.startDate or '-'} -> {self.endDate or '-'}\n"
            f"submissions: {self.submissions}"
        )


class AgreementContentItem(BaseModel):
    type: str
    value: str
    id: Optional[str] = None


class CompetitionAgreementResponse(BaseModel):
    id: str
    title: str
    lastModified: Optional[str] = None
    content: List[AgreementContentItem] = Field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"competition agreement: {self.id}\n"
            f"title: {self.title}\n"
            f"lastModified: {self.lastModified or '-'}\n"
            f"content_items: {len(self.content)}"
        )


class TutorialsPageRef(BaseModel):
    title: str
    id: str
    lastModified: Optional[str] = None


class TutorialItem(BaseModel):
    id: str
    category: Optional[str] = None
    pages: List[TutorialsPageRef] = Field(default_factory=list)
    title: Optional[str] = None
    sequence: Optional[int] = None
    lastModified: Optional[str] = None


class TutorialsResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[TutorialItem] = Field(default_factory=list)

    def __str__(self) -> str:
        lines = [f"tutorials: count={self.count} showing={len(self.results)}"]
        for i, item in enumerate(self.results[:3], start=1):
            lines.append(
                f"{i}. {item.id} | {item.title or '-'} | category={item.category or '-'} | pages={len(item.pages)}"
            )
        return "\n".join(lines)


class TutorialHeadingValue(BaseModel):
    level: Optional[str] = None
    content: Optional[str] = None


class TutorialImageValue(BaseModel):
    title: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fileSize: Optional[int] = None
    url: Optional[str] = None


class TutorialContentItem(BaseModel):
    type: str
    value: Union[str, TutorialHeadingValue, TutorialImageValue, Dict[str, Any]]
    id: Optional[str] = None


class TutorialPageResponse(BaseModel):
    id: str
    title: Optional[str] = None
    lastModified: Optional[str] = None
    content: List[TutorialContentItem] = Field(default_factory=list)
    sequence: Optional[int] = None
    category: Optional[str] = None

    def __str__(self) -> str:
        by_type = Counter(item.type for item in self.content)
        top_types = ", ".join(f"{k}:{v}" for k, v in by_type.most_common(3))
        first_preview = "-"
        if self.content:
            first = self.content[0]
            if isinstance(first.value, str):
                value_preview = first.value.strip().replace("\n", " ")
            else:
                value_preview = str(first.value)
            if len(value_preview) > 180:
                value_preview = value_preview[:180] + "..."
            first_preview = f"{first.type}: {value_preview}"
        return (
            f"tutorial-page: {self.id} | title={self.title or '-'} | "
            f"category={self.category or '-'} | content_items={len(self.content)} | "
            f"types={top_types or '-'} | first={first_preview}"
        )


class CommunityMixin:
    """Handles events, leaderboard, competitions, agreements."""

    async def _resolve_user_id(self, user_id: Optional[str]) -> str:
        if user_id:
            return user_id
        response = self.session.get(f"{self.base_url}/users/self")
        response.raise_for_status()
        user = UserSelfLite.model_validate(parse_json_or_error(response, "/users/self"))
        return user.id

    async def get_events(self) -> EventsResponse:
        """Get available events and competitions."""
        await self.ensure_authenticated()
        response = self.session.get(f"{self.base_url}/events")
        response.raise_for_status()
        return EventsResponse.model_validate(parse_json_or_error(response, "/events"))

    async def get_leaderboard(self, user_id: Optional[str] = None) -> LeaderboardResponse:
        """Get leaderboard data."""
        await self.ensure_authenticated()
        resolved_user_id = await self._resolve_user_id(user_id)
        response = self.session.get(f"{self.base_url}/consultant/boards/leader", params={"user": resolved_user_id})
        response.raise_for_status()
        return LeaderboardResponse.model_validate(
            parse_json_or_error(response, "/consultant/boards/leader")
        )

    async def get_user_competitions(self, user_id: Optional[str] = None) -> UserCompetitionsResponse:
        """Get list of competitions that the user is participating in."""
        await self.ensure_authenticated()
        resolved_user_id = await self._resolve_user_id(user_id)
        response = self.session.get(f"{self.base_url}/users/{resolved_user_id}/competitions")
        response.raise_for_status()
        return UserCompetitionsResponse.model_validate(
            parse_json_or_error(response, f"/users/{resolved_user_id}/competitions")
        )

    async def get_competition_details(self, competition_id: str) -> CompetitionDetailsResponse:
        """Get detailed information about a specific competition."""
        await self.ensure_authenticated()
        response = self.session.get(f"{self.base_url}/competitions/{competition_id}")
        response.raise_for_status()
        return CompetitionDetailsResponse.model_validate(
            parse_json_or_error(response, f"/competitions/{competition_id}")
        )

    async def get_competition_agreement(self, competition_id: str) -> CompetitionAgreementResponse:
        """Get the rules, terms, and agreement for a specific competition."""
        await self.ensure_authenticated()
        response = self.session.get(f"{self.base_url}/competitions/{competition_id}/agreement")
        response.raise_for_status()
        return CompetitionAgreementResponse.model_validate(
            parse_json_or_error(response, f"/competitions/{competition_id}/agreement")
        )

    async def get_documentations(self) -> TutorialsResponse:
        """Get available documentations and learning materials."""
        await self.ensure_authenticated()
        response = self.session.get(f"{self.base_url}/tutorials")
        response.raise_for_status()
        return TutorialsResponse.model_validate(parse_json_or_error(response, "/tutorials"))

    async def get_documentation_page(self, page_id: str) -> TutorialPageResponse:
        """Retrieve detailed content of a specific documentation page/article."""
        await self.ensure_authenticated()
        response = self.session.get(f"{self.base_url}/tutorial-pages/{page_id}")
        response.raise_for_status()
        return TutorialPageResponse.model_validate(parse_json_or_error(response, f"/tutorial-pages/{page_id}"))
