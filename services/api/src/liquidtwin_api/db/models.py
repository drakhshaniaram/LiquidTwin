from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class Terminal(Base):
    __tablename__ = "terminal"
    __table_args__ = (
        CheckConstraint("length(name) BETWEEN 1 AND 120", name="ck_terminal_name_length"),
        UniqueConstraint("name", name="uq_terminal_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class TerminalVersion(Base):
    __tablename__ = "terminal_version"
    __table_args__ = (CheckConstraint("version >= 1", name="ck_terminal_version_positive"),)

    terminal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("terminal.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    document: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(String(500))


class AvailabilityWindow(Base):
    __tablename__ = "availability_window"
    __table_args__ = (
        CheckConstraint(
            "status IN ('AVAILABLE', 'MAINTENANCE', 'FLUSHING', 'CLEANING', 'OUT_OF_SERVICE')",
            name="ck_availability_window_status",
        ),
        CheckConstraint('"to" IS NULL OR "to" >= "from"', name="ck_availability_window_time_order"),
        UniqueConstraint(
            "terminal_id", "element_id", "source", "external_ref", name="uq_availability_window_source_ref"
        ),
        Index("ix_availability_window_terminal_time", "terminal_id", "from", "to"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    terminal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("terminal.id", ondelete="CASCADE"), nullable=False
    )
    element_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    starts_at: Mapped[datetime] = mapped_column("from", DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column("to", DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(120), nullable=False, default="manual", server_default="manual")
    external_ref: Mapped[str | None] = mapped_column(String(255))


class ConfirmedRoute(Base):
    __tablename__ = "confirmed_route"
    __table_args__ = (
        ForeignKeyConstraint(
            ["terminal_id", "terminal_version"],
            ["terminal_version.terminal_id", "terminal_version.version"],
            ondelete="CASCADE",
            name="fk_confirmed_route_terminal_version",
        ),
        Index("ix_confirmed_route_terminal_created", "terminal_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    terminal_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    terminal_version: Mapped[int] = mapped_column(Integer, nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    route: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    outdated: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    outdated_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str] = mapped_column(String(120), nullable=False, default="anonymous", server_default="anonymous")