import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


engine = create_engine(
    os.getenv(
        "DATABASE_URL", "postgresql+psycopg://chatlens:chatlens@localhost:5432/chatlens"
    ),
    pool_pre_ping=True,
)
if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def enable_fk(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(engine)


def get_db():
    with SessionLocal() as session:
        yield session
