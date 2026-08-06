from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: Engine | None = None
        self.session_factory: sessionmaker[Session] | None = None

    def connect(self) -> None:
        self.engine = create_engine(self.settings.database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(
            bind=self.engine, autoflush=False, expire_on_commit=False
        )

    def disconnect(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
        self.engine = None
        self.session_factory = None

    def create_session(self) -> Session:
        if self.session_factory is None:
            raise RuntimeError("Database has not been initialized")
        return self.session_factory()


def get_db(request: Request) -> Generator[Session, None, None]:
    db = request.app.state.container.database.create_session()
    try:
        yield db
    finally:
        db.close()
