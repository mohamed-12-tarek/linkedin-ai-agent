from contextlib import AbstractContextManager

from app.core.config import Settings


class WorkflowCheckpointStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._manager: AbstractContextManager | None = None
        self.saver = None

    def connect(self) -> None:
        if self.settings.database_url.startswith("sqlite"):
            try:
                from langgraph.checkpoint.memory import InMemorySaver
            except ModuleNotFoundError:
                self.saver = None
                return

            self.saver = InMemorySaver()
            return
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ModuleNotFoundError:
            self.saver = None
            return

        connection_url = self.settings.database_url.replace("postgresql+psycopg://", "postgresql://")
        self._manager = PostgresSaver.from_conn_string(connection_url)
        self.saver = self._manager.__enter__()
        self.saver.setup()

    def disconnect(self) -> None:
        if self._manager is not None:
            self._manager.__exit__(None, None, None)
        self._manager = None
        self.saver = None
