"""Database schema (PostgreSQL). Migrations live in backend/migrations."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON, CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String, Text, Uuid, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from .db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _now_column() -> Mapped[datetime]:
    # Python-side default keeps a stable order for rows created in the same transaction.
    return mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False)


class User(Base):
    """A registered user. Identity and email come from Clerk; age is collected at onboarding."""
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("age IS NULL OR (age >= 14 AND age <= 120)", name="ck_users_age"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    clerk_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320))
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    age: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = _now_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), onupdate=_utcnow, nullable=False,
    )

    profiles: Mapped[list["Profile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True,
    )


class Profile(Base):
    """A Luméra Profile: one portrait with its boards and try-ons."""
    __tablename__ = "lumera_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="created")
    original_image_id: Mapped[Optional[str]] = mapped_column(String(32))
    # Current board per kind: {"SEASON": image_id, ...}
    boards: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    # Last style request (history in style_choices)
    style_request: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    created_at: Mapped[datetime] = _now_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), onupdate=_utcnow, nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="profiles")


class Image(Base):
    """Every image (original, board, try-on). Bytes stored in the DB: Railway disks are ephemeral."""
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("lumera_profiles.id", ondelete="CASCADE"), index=True)
    parent_image_id: Mapped[Optional[str]] = mapped_column(String(32))
    operation: Mapped[str] = mapped_column(String(20))
    board_kind: Mapped[Optional[str]] = mapped_column(String(20))
    reference_board_id: Mapped[Optional[str]] = mapped_column(String(32))
    option: Mapped[Optional[int]] = mapped_column(Integer)
    setting: Mapped[Optional[str]] = mapped_column(String(30))
    prompt_version: Mapped[Optional[str]] = mapped_column(String(60))
    prompt: Mapped[Optional[str]] = deferred(mapped_column(Text))
    quality: Mapped[Optional[str]] = mapped_column(String(20))
    size: Mapped[Optional[str]] = mapped_column(String(20))
    mime: Mapped[str] = mapped_column(String(30))
    data: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))
    created_at: Mapped[datetime] = _now_column()


class StyleChoice(Base):
    """History of every style selection made by a user."""
    __tablename__ = "style_choices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("lumera_profiles.id", ondelete="CASCADE"), index=True)
    selected_styles: Mapped[list[str]] = mapped_column(JSONType)
    trend_preference: Mapped[str] = mapped_column(String(20))
    occasion: Mapped[str] = mapped_column(String(200), default="")
    comfort_preferences: Mapped[str] = mapped_column(String(300), default="")
    free_text_style_request: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = _now_column()


class FeedbackEvent(Base):
    """Explicit user signals (LIKE, DISLIKE, SAVE, …) — Prompt Pack section 21."""
    __tablename__ = "feedback_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("lumera_profiles.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20))
    entity_type: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = _now_column()
