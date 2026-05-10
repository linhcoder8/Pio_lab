"""Initial structured memory schema.

Revision ID: 20260505_0001
Revises:
Create Date: 2026-05-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260505_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=True),
        sa.Column("final_output", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_channel"), "tasks", ["channel"], unique=False)
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)
    op.create_index(op.f("ix_tasks_user_id"), "tasks", ["user_id"], unique=False)

    op.create_table(
        "providers",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("sdk", sa.String(length=64), nullable=True),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_channel"), "conversations", ["channel"], unique=False)
    op.create_index(op.f("ix_conversations_role"), "conversations", ["role"], unique=False)
    op.create_index(op.f("ix_conversations_task_id"), "conversations", ["task_id"], unique=False)
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)

    op.create_table(
        "provider_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quota_exhausted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider"], ["providers.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "account_id", name="uq_provider_account"),
    )
    op.create_index(op.f("ix_provider_accounts_provider"), "provider_accounts", ["provider"], unique=False)
    op.create_index(op.f("ix_provider_accounts_status"), "provider_accounts", ["status"], unique=False)

    op.create_table(
        "traces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("routing_key", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("messages_in", sa.JSON(), nullable=False),
        sa.Column("messages_out", sa.JSON(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_traces_agent_id"), "traces", ["agent_id"], unique=False)
    op.create_index(op.f("ix_traces_provider"), "traces", ["provider"], unique=False)
    op.create_index(op.f("ix_traces_routing_key"), "traces", ["routing_key"], unique=False)
    op.create_index(op.f("ix_traces_status"), "traces", ["status"], unique=False)
    op.create_index(op.f("ix_traces_task_id"), "traces", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_traces_task_id"), table_name="traces")
    op.drop_index(op.f("ix_traces_status"), table_name="traces")
    op.drop_index(op.f("ix_traces_routing_key"), table_name="traces")
    op.drop_index(op.f("ix_traces_provider"), table_name="traces")
    op.drop_index(op.f("ix_traces_agent_id"), table_name="traces")
    op.drop_table("traces")
    op.drop_index(op.f("ix_provider_accounts_status"), table_name="provider_accounts")
    op.drop_index(op.f("ix_provider_accounts_provider"), table_name="provider_accounts")
    op.drop_table("provider_accounts")
    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_task_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_role"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_channel"), table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("providers")
    op.drop_index(op.f("ix_tasks_user_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_channel"), table_name="tasks")
    op.drop_table("tasks")
