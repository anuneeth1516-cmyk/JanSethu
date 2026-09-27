"""create the Phase 1 database foundation"""
from alembic import op
from sqlalchemy import inspect

revision = "0001_database_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    from app import models  # noqa: F401
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.db import Base
    from app import models  # noqa: F401
    bind = op.get_bind()
    inspector = inspect(bind)
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in inspector.get_table_names():
            table.drop(bind=bind)