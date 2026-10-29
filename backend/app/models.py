"""Таблицы базы данных.

Важно: никаких имён, телефонов и email пользователей мы не храним.
Сессия — это просто случайный идентификатор в браузере.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # ключ виджета
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(50), default="")  # круглосуточный телефон клиники
    address: Mapped[str] = mapped_column(String(300), default="")
    admin_token: Mapped[str] = mapped_column(String(128))  # доступ к статистике клиники


class ChatSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clinic_id: Mapped[int | None] = mapped_column(ForeignKey("clinics.id"), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), default="patient")  # patient | relative
    sober_since: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    clinic: Mapped[Clinic | None] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user | bot
    text: Mapped[str] = mapped_column(Text)
    is_crisis: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 помогло, -1 нет
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class Event(Base):
    """Обезличенные события для статистики клиники.

    Не связаны с сессией и не содержат текста — поэтому остаются,
    даже если пользователь удалил свою историю.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clinic_id: Mapped[int | None] = mapped_column(ForeignKey("clinics.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(30))  # session | message | crisis | blocked | rating_up | rating_down
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
