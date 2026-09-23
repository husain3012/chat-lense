from alembic import context
from app.models.database import Base, engine
from app.models import chat  # noqa: F401


def run():
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


run()
