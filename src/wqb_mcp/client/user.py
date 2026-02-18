"""User mixin for BrainApiClient."""

import base64
import math
import os
import pathlib
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..utils import dataframe_markdown_preview, parse_json_or_error

IMG_TAG_PATTERN = re.compile(r"<img[^>]+src=\"(data:image/[^\"]+)\"[^>]*>", re.IGNORECASE)
BASE64_IMG_HEURISTIC_PATTERN = re.compile(r"([A-Za-z0-9+/]{500,}={0,2})\"\s*</img>")


class ValueFactorTrendScoreResponse(BaseModel):
    diversity_score: float
    N: int
    A: int
    P: int
    P_max: int
    S_A: float
    S_P: float
    S_H: float
    per_pyramid_counts: Dict[str, int] = Field(default_factory=dict)

    def __str__(self) -> str:
        sorted_pyramids = sorted(self.per_pyramid_counts.items(), key=lambda x: -x[1])
        top5 = sorted_pyramids[:5]
        pyramids = "\n".join(f"  {name}: {count}" for name, count in top5) or "  (none)"
        remaining = len(sorted_pyramids) - len(top5)
        if remaining > 0:
            pyramids += f"\n  ... and {remaining} more"
        return (
            f"diversity score = {self.diversity_score:.6f} (S_A * S_P * S_H)\n"
            f"N={self.N}(total REGULAR OS alphas) A={self.A}(number of submitted atom alphas) P={self.P}(pyramids covered) P_max={self.P_max}\n"
            f"S_A = A/N = {self.A}/{self.N} = {self.S_A:.4f} (atom alpha ratio)\n"
            f"S_P = P/P_max = {self.P}/{self.P_max} = {self.S_P:.4f} (pyramid coverage)\n"
            f"S_H = {self.S_H:.4f} (entropy of alpha distribution over pyramid)\n"
            f"pyramids:\n{pyramids}"
        )


class UserAddress(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class UserEducation(BaseModel):
    university: Optional[str] = None
    major: Optional[str] = None
    degree: Optional[str] = None
    stem: Optional[bool] = None
    graduationYear: Optional[int] = None
    gpa: Optional[float] = None
    maxGPA: Optional[float] = None


class UserCommunicationSettings(BaseModel):
    allowSMS: Optional[bool] = None


class UserSettings(BaseModel):
    allowTracking: Optional[bool] = None
    communication: Optional[UserCommunicationSettings] = None
    privacy: Dict[str, Any] = Field(default_factory=dict)
    client: Dict[str, Any] = Field(default_factory=dict)


class UserOnboarding(BaseModel):
    status: Optional[str] = None


class UserCampaign(BaseModel):
    campaign: Optional[str] = None
    source: Optional[str] = None
    medium: Optional[str] = None
    term: Optional[str] = None
    content: Optional[str] = None


class UserAuxiliary(BaseModel):
    campaign: Optional[UserCampaign] = None


class UserProfileResponse(BaseModel):
    id: str
    email: Optional[str] = None
    telephone: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    fullName: Optional[str] = None
    gender: Optional[str] = None
    dateCreated: Optional[str] = None
    dateVerified: Optional[str] = None
    dateApproved: Optional[str] = None
    verified: Optional[bool] = None
    approved: Optional[bool] = None
    address: Optional[UserAddress] = None
    education: Optional[UserEducation] = None
    employment: Optional[Dict[str, Any]] = None
    recruitment: Optional[Dict[str, Any]] = None
    resume: Optional[str] = None
    image: Optional[str] = None
    settings: Optional[UserSettings] = None
    onboarding: Optional[UserOnboarding] = None
    auxiliary: Optional[UserAuxiliary] = None
    geniusLevel: Optional[str] = None

    def __str__(self) -> str:
        return (
            f"user: {self.id} | "
            f"name={self.fullName or '-'} | "
            f"email={self.email or '-'} | "
            f"approved={self.approved} | "
            f"level={self.geniusLevel or '-'}"
        )


class PaginatedResponseBase(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None


class MessageItem(BaseModel):
    id: str
    type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    dateCreated: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    read: Optional[bool] = None
    extracted_images: Optional[List[str]] = None
    sanitized: Optional[bool] = None


class MessagesResponse(PaginatedResponseBase):
    results: List[MessageItem] = Field(default_factory=list)
    image_handling: Optional[str] = None

    def __str__(self) -> str:
        unread = sum(1 for item in self.results if item.read is False)
        lines = [f"messages: count={self.count} showing={len(self.results)} unread_in_page={unread}"]
        for i, item in enumerate(self.results, start=1):
            lines.append(
                f"\n---\n{i}. {item.id} | {item.type or '-'} | {item.title or '-'} | "
                f"date={item.dateCreated or '-'} | read={item.read}"
            )
            if item.description:
                lines.append(item.description)
        if self.image_handling:
            lines.append(f"\nimage_handling={self.image_handling}")
        return "\n".join(lines)


class UserActivityItem(BaseModel):
    name: str
    title: str


class UserActivitiesResponse(PaginatedResponseBase):
    results: List[UserActivityItem] = Field(default_factory=list)

    def __str__(self) -> str:
        rows = [{"name": item.name, "title": item.title} for item in self.results]
        table = dataframe_markdown_preview(
            rows, preferred_cols=["name", "title"], max_rows=len(rows),
        )
        return f"activities: count={self.count}\n\n{table}"


class PyramidCategory(BaseModel):
    id: str
    name: str


class PyramidMultiplierItem(BaseModel):
    category: PyramidCategory
    region: str
    delay: int
    multiplier: float


class PyramidMultipliersResponse(BaseModel):
    pyramids: List[PyramidMultiplierItem] = Field(default_factory=list)

    def __str__(self) -> str:
        regions = sorted({item.region for item in self.pyramids})
        rows = [
            {"id": item.category.id, "category": item.category.name,
             "region": item.region, "delay": item.delay,
             "multiplier": item.multiplier}
            for item in sorted(self.pyramids, key=lambda x: x.multiplier, reverse=True)
        ]
        header = (
            f"pyramid-multipliers: {len(self.pyramids)} categories | "
            f"regions={','.join(regions) if regions else '-'}"
        )
        table = dataframe_markdown_preview(
            rows, preferred_cols=["id", "category", "region", "delay", "multiplier"],
            max_rows=5,
        )
        return f"{header}\n\nTop 5 by multiplier:\n{table}"


class PyramidAlphaItem(BaseModel):
    category: PyramidCategory
    region: str
    delay: int
    alphaCount: int


class PyramidAlphasResponse(BaseModel):
    pyramids: List[PyramidAlphaItem] = Field(default_factory=list)

    def __str__(self) -> str:
        total = sum(item.alphaCount for item in self.pyramids)
        non_zero = [item for item in self.pyramids if item.alphaCount > 0]
        rows = [
            {"category": item.category.name, "region": item.region,
             "delay": item.delay, "alphaCount": item.alphaCount}
            for item in sorted(non_zero, key=lambda x: x.alphaCount, reverse=True)
        ]
        header = (
            f"pyramid-alphas: {len(self.pyramids)} categories | "
            f"total_alphas={total} | with_alphas={len(non_zero)}"
        )
        table = dataframe_markdown_preview(
            rows, preferred_cols=["category", "region", "delay", "alphaCount"],
            max_rows=len(rows),
        )
        return f"{header}\n\n{table}"


class PaymentWindowValue(BaseModel):
    start: str
    end: str
    value: float


class PaymentRecordSetProperty(BaseModel):
    name: str
    title: str
    type: str


class PaymentRecordSetSchema(BaseModel):
    name: str
    title: str
    properties: List[PaymentRecordSetProperty] = Field(default_factory=list)


class PaymentRecords(BaseModel):
    record_schema: PaymentRecordSetSchema = Field(alias="schema")
    records: List[List[Any]] = Field(default_factory=list)


class BasePaymentsPayload(BaseModel):
    yesterday: PaymentWindowValue
    current: PaymentWindowValue
    previous: PaymentWindowValue
    ytd: PaymentWindowValue
    total: PaymentWindowValue
    records: PaymentRecords
    currency: str
    type: str


class OtherPaymentsPayload(BaseModel):
    total: PaymentWindowValue
    records: PaymentRecords
    currency: str
    type: str


class DailyAndQuarterlyPaymentResponse(BaseModel):
    base_payments: BasePaymentsPayload
    other_payments: OtherPaymentsPayload

    def __str__(self) -> str:
        base_rows = len(self.base_payments.records.records)
        other_rows = len(self.other_payments.records.records)
        return (
            f"payments: base_total={self.base_payments.total.value} {self.base_payments.currency} "
            f"(rows={base_rows}) | "
            f"other_total={self.other_payments.total.value} {self.other_payments.currency} "
            f"(rows={other_rows})"
        )


class UserMixin:
    """Handles profile, messages, activities, pyramids, docs, payments, forum delegation."""

    def _get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}{path}", params=params)
        response.raise_for_status()
        return parse_json_or_error(response, path)

    def _process_message_description(
        self,
        desc: Optional[str],
        message_id: str,
        image_handling: str,
        save_dir: pathlib.Path,
    ) -> tuple[Optional[str], List[str]]:
        if not desc or image_handling == "keep":
            return desc, []

        attachments: List[str] = []
        matches = list(IMG_TAG_PATTERN.finditer(desc))
        if not matches:
            if image_handling != "keep" and BASE64_IMG_HEURISTIC_PATTERN.search(desc):
                placeholder = "[Embedded image removed - large base64 sequence truncated]"
                return BASE64_IMG_HEURISTIC_PATTERN.sub(placeholder + "</img>", desc), []
            return desc, []

        if image_handling == "placeholder":
            try:
                save_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.log(f"Could not create image save directory: {e}", "WARNING")

        new_desc = desc
        for idx, match in enumerate(matches, start=1):
            data_uri = match.group(1)
            if not data_uri.lower().startswith("data:image") or "," not in data_uri:
                continue

            header, b64_data = data_uri.split(",", 1)
            mime_part = header.split(";")[0]
            ext = "png"
            if "/" in mime_part:
                ext = mime_part.split("/")[1]
            safe_ext = (ext or "img").split("?")[0]

            if image_handling == "ignore":
                replacement = f"[Image removed: {safe_ext}]"
            elif image_handling == "placeholder":
                file_name = f"{message_id}_{idx}.{safe_ext}"
                file_path = save_dir / file_name
                try:
                    if len(b64_data) > 7_000_000:
                        raise ValueError("Image too large to decode safely")
                    with open(file_path, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    attachments.append(str(file_path))
                    replacement = f"[Image extracted -> {file_path}]"
                except Exception as e:
                    self.log(f"Failed to decode embedded image in message {message_id}: {e}", "WARNING")
                    replacement = "[Image extraction failed - content omitted]"
            else:
                replacement = "[Embedded image]"

            new_desc = new_desc.replace(match.group(0), replacement, 1)

        return new_desc, attachments

    async def value_factor_trendScore(self, start_date: str, end_date: str) -> ValueFactorTrendScoreResponse:
        """Compute diversity score for regular alphas in a submission-date window."""
        await self.ensure_authenticated()
        alphas_resp = await self.get_user_alphas(
            stage="OS",
            limit=500,
            submission_start_date=start_date,
            submission_end_date=end_date,
        )
        regular = [a for a in alphas_resp.results if a.type == "REGULAR"]

        atom_count = 0
        per_pyramid: Dict[str, int] = {}
        for a in regular:
            try:
                detail = await self.get_alpha_details(a.id)
            except Exception:
                continue

            if detail.is_atom():
                atom_count += 1

            for p in detail.pyramid_names():
                per_pyramid[p] = per_pyramid.get(p, 0) + 1

        N = len(regular)
        A = atom_count
        P = len(per_pyramid)

        P_max = None
        try:
            pm = await self.get_pyramid_multipliers()
            P_max = len(pm.pyramids)
        except Exception:
            P_max = None

        if not P_max or P_max <= 0:
            P_max = max(P, 1)

        S_A = (A / N) if N > 0 else 0.0
        S_P = (P / P_max) if P_max > 0 else 0.0

        S_H = 0.0
        if P > 1 and per_pyramid:
            total_occ = sum(per_pyramid.values())
            H = 0.0
            for cnt in per_pyramid.values():
                q = cnt / total_occ if total_occ > 0 else 0
                if q > 0:
                    H -= q * math.log2(q)
            max_H = math.log2(P)
            S_H = (H / max_H) if max_H > 0 else 0.0

        diversity_score = S_A * S_P * S_H
        return ValueFactorTrendScoreResponse(
            diversity_score=diversity_score,
            N=N,
            A=A,
            P=P,
            P_max=P_max,
            S_A=S_A,
            S_P=S_P,
            S_H=S_H,
            per_pyramid_counts=per_pyramid,
        )

    async def get_user_profile(self, user_id: str = "self") -> UserProfileResponse:
        """Get user profile information."""
        await self.ensure_authenticated()
        return UserProfileResponse.model_validate(self._get_json(f"/users/{user_id}"))

    async def get_messages(self, limit: Optional[int] = None, offset: int = 0) -> MessagesResponse:
        """Get messages for the current user with optional pagination."""
        await self.ensure_authenticated()

        image_handling = os.environ.get("BRAIN_MESSAGE_IMAGE_MODE", "placeholder").lower()
        save_dir = pathlib.Path("message_images")

        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset > 0:
            params["offset"] = offset

        payload = self._get_json("/users/self/messages", params=params)
        results = payload.get("results", [])
        if isinstance(results, list):
            for msg in results:
                if not isinstance(msg, dict):
                    continue
                desc = msg.get("description")
                processed_desc, attachments = self._process_message_description(
                    desc=desc,
                    message_id=str(msg.get("id", "msg")),
                    image_handling=image_handling,
                    save_dir=save_dir,
                )
                if attachments or desc != processed_desc:
                    msg["description"] = processed_desc
                    if attachments:
                        msg["extracted_images"] = attachments
                    else:
                        msg["sanitized"] = True

        payload["image_handling"] = image_handling
        return MessagesResponse.model_validate(payload)

    async def get_user_activities(self, user_id: str, grouping: Optional[str] = None) -> UserActivitiesResponse:
        """Get user activity diversity data."""
        await self.ensure_authenticated()
        params: Dict[str, Any] = {}
        if grouping:
            params["grouping"] = grouping
        return UserActivitiesResponse.model_validate(self._get_json(f"/users/{user_id}/activities", params=params))

    async def get_pyramid_multipliers(self) -> PyramidMultipliersResponse:
        """Get current pyramid multipliers showing BRAIN's encouragement levels."""
        await self.ensure_authenticated()
        return PyramidMultipliersResponse.model_validate(self._get_json("/users/self/activities/pyramid-multipliers"))

    async def get_pyramid_alphas(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> PyramidAlphasResponse:
        """Get user's current alpha distribution across pyramid categories."""
        await self.ensure_authenticated()

        params: Dict[str, Any] = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        path = "/users/self/activities/pyramid-alphas"
        response = self.session.get(f"{self.base_url}{path}", params=params)
        response.raise_for_status()
        return PyramidAlphasResponse.model_validate(parse_json_or_error(response, path))

    async def get_daily_and_quarterly_payment(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ) -> DailyAndQuarterlyPaymentResponse:
        """Get daily and quarterly payment information for the authenticated user."""
        from ..config import load_credentials

        stored_email, stored_password = load_credentials()
        email = email or stored_email
        password = password or stored_password
        if email and password:
            await self.authenticate(email, password)
        else:
            await self.ensure_authenticated()

        base_path = "/users/self/activities/base-payment"
        base_response = self.session.get(f"{self.base_url}{base_path}")
        base_response.raise_for_status()
        base_payments = parse_json_or_error(base_response, base_path)

        other_path = "/users/self/activities/other-payment"
        other_response = self.session.get(f"{self.base_url}{other_path}")
        other_response.raise_for_status()
        other_payments = parse_json_or_error(other_response, other_path)

        return DailyAndQuarterlyPaymentResponse(
            base_payments=base_payments,
            other_payments=other_payments,
        )
