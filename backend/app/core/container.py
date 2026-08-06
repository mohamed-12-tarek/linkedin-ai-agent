from dataclasses import dataclass

from app.core.config import Settings
from app.core.security import EncryptionService
from app.db.session import Database
from app.integrations.images import (
    ImageProviderRegistry,
    LocalImageStorage,
    build_image_provider_registry,
)
from app.integrations.publishers import PublisherRegistry, build_publisher_registry
from app.workflows.checkpoints import WorkflowCheckpointStore
from app.workflows.prompts import PromptEngine
from app.workflows.registry import GraphRegistry, NodeRegistry
from app.workflows.styles import StyleEngine


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    settings: Settings
    database: Database
    encryption: EncryptionService
    style_engine: StyleEngine
    prompt_engine: PromptEngine
    node_registry: NodeRegistry
    graph_registry: GraphRegistry
    checkpoint_store: WorkflowCheckpointStore
    image_providers: ImageProviderRegistry
    image_storage: LocalImageStorage
    publishers: PublisherRegistry


def create_container(settings: Settings) -> ApplicationContainer:
    style_engine = StyleEngine()
    return ApplicationContainer(
        settings=settings,
        database=Database(settings),
        encryption=EncryptionService(settings),
        style_engine=style_engine,
        prompt_engine=PromptEngine(style_engine),
        node_registry=NodeRegistry(),
        graph_registry=GraphRegistry(),
        checkpoint_store=WorkflowCheckpointStore(settings),
        image_providers=build_image_provider_registry(settings),
        image_storage=LocalImageStorage(settings),
        publishers=build_publisher_registry(settings),
    )
