"""Форматы запросов и ответов API."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    clinic_key: str | None = None
    mode: Literal["patient", "relative"] = "patient"


class HelpContact(BaseModel):
    title: str
    subtitle: str
    phone: str


class ClinicInfo(BaseModel):
    key: str
    name: str


class SessionOut(BaseModel):
    session_id: str
    mode: str
    clinic: ClinicInfo | None
    sober_since: date | None
    sober_days: int | None


class ChatIn(BaseModel):
    session_id: str
    text: str = Field(min_length=1)


class ChatOut(BaseModel):
    message_id: int
    reply: str
    crisis: bool
    blocked: bool
    help: list[HelpContact] | None = None


class MessageOut(BaseModel):
    id: int
    role: str
    text: str
    is_crisis: bool
    rating: int | None
    created_at: datetime


class SoberDateIn(BaseModel):
    sober_since: date | None


class RatingIn(BaseModel):
    session_id: str
    value: Literal[1, -1]


class StatsOut(BaseModel):
    clinic: str
    sessions: int
    messages: int
    crisis: int
    distress: int
    blocked: int
    rating_up: int
    rating_down: int
    night_share: float
    by_hour: list[int]
