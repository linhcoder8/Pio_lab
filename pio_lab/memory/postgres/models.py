"""SQLAlchemy models for the structured memory store."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from pio_lab.utils.helpers import utc_now


def _uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    """Base class for all Postgres models."""


class Task(Base):
    """A user-visible task handled by the agent system."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    channel: Mapped[str] = mapped_column(String(64), index=True)
    request: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    final_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    traces: Mapped[list[Trace]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class Trace(Base):
    """A provider call trace for observability and future distillation."""

    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_id: Mapped[str] = mapped_column(String(128), index=True)
    routing_key: Mapped[str] = mapped_column(String(128), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(128))
    messages_in: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    messages_out: Mapped[dict[str, Any] | list[dict[str, Any]]] = mapped_column(JSON, default=dict)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="success", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    task: Mapped[Task | None] = relationship(back_populates="traces")


class Conversation(Base):
    """A channel conversation message."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    channel: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    task: Mapped[Task | None] = relationship(back_populates="conversations")


class Provider(Base):
    """A configured LLM provider."""

    __tablename__ = "providers"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_type: Mapped[str] = mapped_column(String(32), default="cloud")
    sdk: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    accounts: Mapped[list[ProviderAccount]] = relationship(
        back_populates="provider_ref",
        cascade="all, delete-orphan",
    )


class ProviderAccount(Base):
    """A provider account that can be rotated by the provider router."""

    __tablename__ = "provider_accounts"
    __table_args__ = (UniqueConstraint("provider", "account_id", name="uq_provider_account"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("providers.name", ondelete="CASCADE"),
        index=True,
    )
    account_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="available", index=True)
    last_used: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quota_exhausted_until: Mapped[Any | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    provider_ref: Mapped[Provider] = relationship(back_populates="accounts")


__all__ = ["Base", "Conversation", "Provider", "ProviderAccount", "Task", "Trace"]
