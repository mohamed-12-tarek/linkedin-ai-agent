from dataclasses import dataclass

from app.core.config import Settings
from app.db.session import Database


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    settings: Settings
    database: Database


def create_container(settings: Settings) -> ApplicationContainer:
    return ApplicationContainer(settings=settings, database=Database(settings))
