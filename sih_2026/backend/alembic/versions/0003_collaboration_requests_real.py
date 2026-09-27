"""make collaboration requests real and updatable"""

from alembic import op
import sqlalchemy as sa

revision = "0003_collaboration_requests_real"
down_revision = "0002_problem_reporting_real"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "collaboration_requests" not in inspector.get_table_names():
        op.create_table(
            "collaboration_requests",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("problem_id", sa.String(length=36), nullable=False),
            sa.Column("requester_id", sa.String(length=36), nullable=False),
            sa.Column("recipient_id", sa.String(length=36), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("message", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["problem_id"], ["problems.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "uq_collaboration_pending_pair",
            "collaboration_requests",
            ["problem_id", "requester_id", "recipient_id"],
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
            sqlite_where=sa.text("status = 'pending'"),
        )
        return

    columns = {column["name"] for column in inspector.get_columns("collaboration_requests")}
    if "requester_id" not in columns and "sender_id" in columns:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("collaboration_requests") as batch_op:
                batch_op.alter_column("sender_id", new_column_name="requester_id")
        else:
            op.alter_column("collaboration_requests", "sender_id", new_column_name="requester_id")
    if "updated_at" not in columns:
        op.add_column(
            "collaboration_requests",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        )
        op.execute("UPDATE collaboration_requests SET updated_at = created_at WHERE updated_at IS NULL")
        if bind.dialect.name != "sqlite":
            op.alter_column("collaboration_requests", "updated_at", nullable=False)

    index_names = {index["name"] for index in inspector.get_indexes("collaboration_requests")}
    if "uq_collaboration_pending_pair" not in index_names:
        op.create_index(
            "uq_collaboration_pending_pair",
            "collaboration_requests",
            ["problem_id", "requester_id", "recipient_id"],
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
            sqlite_where=sa.text("status = 'pending'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "collaboration_requests" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("collaboration_requests")}
    if "updated_at" in columns:
        op.drop_column("collaboration_requests", "updated_at")
    index_names = {index["name"] for index in inspector.get_indexes("collaboration_requests")}
    if "uq_collaboration_pending_pair" in index_names:
        op.drop_index("uq_collaboration_pending_pair", table_name="collaboration_requests")
    if "requester_id" in columns:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("collaboration_requests") as batch_op:
                batch_op.alter_column("requester_id", new_column_name="sender_id")
        else:
            op.alter_column("collaboration_requests", "requester_id", new_column_name="sender_id")
