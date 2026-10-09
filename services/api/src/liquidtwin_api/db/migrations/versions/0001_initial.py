"""Create terminal, availability, and confirmed route tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "terminal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.CheckConstraint("length(name) BETWEEN 1 AND 120", name="ck_terminal_name_length"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_terminal_name"),
    )
    op.create_table(
        "terminal_version",
        sa.Column("terminal_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.CheckConstraint("version >= 1", name="ck_terminal_version_positive"),
        sa.ForeignKeyConstraint(["terminal_id"], ["terminal.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("terminal_id", "version"),
    )
    op.create_table(
        "availability_window",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("terminal_id", sa.Uuid(), nullable=False),
        sa.Column("element_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=120), server_default="manual", nullable=False),
        sa.Column("external_ref", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            "status IN ('AVAILABLE', 'MAINTENANCE', 'FLUSHING', 'CLEANING', 'OUT_OF_SERVICE')",
            name="ck_availability_window_status",
        ),
        sa.CheckConstraint('"to" IS NULL OR "to" >= "from"', name="ck_availability_window_time_order"),
        sa.ForeignKeyConstraint(["terminal_id"], ["terminal.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "terminal_id", "element_id", "source", "external_ref", name="uq_availability_window_source_ref"
        ),
    )
    op.create_index(
        "ix_availability_window_terminal_time",
        "availability_window",
        ["terminal_id", "from", "to"],
    )
    op.create_table(
        "confirmed_route",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("terminal_id", sa.Uuid(), nullable=False),
        sa.Column("terminal_version", sa.Integer(), nullable=False),
        sa.Column("request", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("route", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("outdated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("outdated_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actor", sa.String(length=120), server_default="anonymous", nullable=False),
        sa.ForeignKeyConstraint(
            ["terminal_id", "terminal_version"],
            ["terminal_version.terminal_id", "terminal_version.version"],
            ondelete="CASCADE",
            name="fk_confirmed_route_terminal_version",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_confirmed_route_terminal_created", "confirmed_route", ["terminal_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_confirmed_route_terminal_created", table_name="confirmed_route")
    op.drop_table("confirmed_route")
    op.drop_index("ix_availability_window_terminal_time", table_name="availability_window")
    op.drop_table("availability_window")
    op.drop_table("terminal_version")
    op.drop_table("terminal")