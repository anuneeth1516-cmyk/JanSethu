"""real problem reporting and ownership tracking"""

from alembic import op
import sqlalchemy as sa

revision = "0002_problem_reporting_real"
down_revision = "0001_database_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "problems" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("problems")}

    if "summary" not in existing_columns:
        op.add_column("problems", sa.Column("summary", sa.Text(), nullable=False, server_default=""))
    if "description" not in existing_columns:
        op.add_column("problems", sa.Column("description", sa.Text(), nullable=False, server_default=""))
    if "category" not in existing_columns:
        op.add_column("problems", sa.Column("category", sa.String(length=120), nullable=True))
    if "updated_at" not in existing_columns:
        op.add_column("problems", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    if "location_text" not in existing_columns:
        op.add_column("problems", sa.Column("location_text", sa.String(length=255), nullable=False, server_default=""))
    if "latitude" not in existing_columns:
        op.add_column("problems", sa.Column("latitude", sa.Float(), nullable=True))
    if "longitude" not in existing_columns:
        op.add_column("problems", sa.Column("longitude", sa.Float(), nullable=True))
    if "metadata" not in existing_columns:
        op.add_column("problems", sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if "creator_id" not in existing_columns:
        op.add_column("problems", sa.Column("creator_id", sa.String(length=36), nullable=True))
        if bind.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_problems_creator_id_users",
                "problems",
                "users",
                ["creator_id"],
                ["id"],
                ondelete="SET NULL",
            )

    op.execute("UPDATE problems SET summary = COALESCE(summary, '') WHERE summary IS NULL")
    op.execute("UPDATE problems SET description = COALESCE(description, summary) WHERE description IS NULL OR description = ''")
    op.execute("UPDATE problems SET location_text = COALESCE(location_text, '') WHERE location_text IS NULL")
    op.execute("UPDATE problems SET updated_at = created_at WHERE updated_at IS NULL")

    index_names = {index["name"] for index in inspector.get_indexes("problems")}
    if "ix_problems_creator_id" not in index_names:
        op.create_index(op.f("ix_problems_creator_id"), "problems", ["creator_id"], unique=False)
    if "ix_problems_created_at" not in index_names:
        op.create_index(op.f("ix_problems_created_at"), "problems", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "problems" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("problems")}
    for column in ["creator_id", "metadata", "longitude", "latitude", "location_text", "updated_at", "category", "description", "summary"]:
        if column in existing_columns:
            op.drop_column("problems", column)

    for index_name in ["ix_problems_creator_id", "ix_problems_created_at"]:
        try:
            op.drop_index(index_name, table_name="problems")
        except Exception:
            pass
