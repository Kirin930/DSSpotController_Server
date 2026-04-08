from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260408_0001"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "admin_users"):
        op.create_table(
            "admin_users",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("password_hash", sa.String(length=512), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
        )
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "admin_users", "ix_admin_users_username"):
        op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=True)

    if not _table_exists(inspector, "nodes"):
        op.create_table(
            "nodes",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("display_name", sa.String(length=128), nullable=False),
            sa.Column("auth_token_hash", sa.String(length=512), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("app_version", sa.String(length=32), nullable=True),
            sa.Column("device_model", sa.String(length=128), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("autoplay_selected", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("connection_state", sa.String(length=16), nullable=False),
            sa.Column("operational_state", sa.String(length=16), nullable=False),
            sa.Column("current_spot_id", sa.String(length=36), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "spots"):
        op.create_table(
            "spots",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("mime_type", sa.String(length=64), nullable=False),
            sa.Column("checksum", sa.String(length=128), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("storage_path", sa.String(length=512), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)
    if not _index_exists(inspector, "spots", "ix_spots_checksum"):
        op.create_index("ix_spots_checksum", "spots", ["checksum"], unique=False)

    if not _table_exists(inspector, "scheduler_config"):
        op.create_table(
            "scheduler_config",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("current_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("spot_sequence", sa.JSON(), nullable=False),
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    if not _table_exists(inspector, "event_logs"):
        op.create_table(
            "event_logs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("node_id", sa.String(length=64), nullable=True),
            sa.Column("spot_id", sa.String(length=36), nullable=True),
            sa.Column("actor_type", sa.String(length=32), nullable=True),
            sa.Column("actor_id", sa.String(length=64), nullable=True),
            sa.Column("details", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)
    for index_name, columns in (
        ("ix_event_logs_event_type", ["event_type"]),
        ("ix_event_logs_node_id", ["node_id"]),
        ("ix_event_logs_spot_id", ["spot_id"]),
        ("ix_event_logs_created_at", ["created_at"]),
    ):
        if not _index_exists(inspector, "event_logs", index_name):
            op.create_index(index_name, "event_logs", columns, unique=False)

    if not _table_exists(inspector, "node_enrollments"):
        op.create_table(
            "node_enrollments",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("node_id", sa.String(length=64), nullable=False),
            sa.Column("pairing_code", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("display_name", sa.String(length=128), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("app_version", sa.String(length=32), nullable=True),
            sa.Column("device_model", sa.String(length=128), nullable=True),
            sa.Column("approved_auth_token", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("autoplay_selected", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("rejection_reason", sa.String(length=255), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by", sa.String(length=64), nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_by", sa.String(length=64), nullable=True),
            sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)
    for index_name, columns in (
        ("ix_node_enrollments_node_id", ["node_id"]),
        ("ix_node_enrollments_pairing_code", ["pairing_code"]),
        ("ix_node_enrollments_status", ["status"]),
    ):
        if not _index_exists(inspector, "node_enrollments", index_name):
            op.create_index(index_name, "node_enrollments", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in (
        "node_enrollments",
        "event_logs",
        "scheduler_config",
        "spots",
        "nodes",
        "admin_users",
    ):
        if _table_exists(inspector, table_name):
            op.drop_table(table_name)
            inspector = sa.inspect(bind)
