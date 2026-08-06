import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.security import EncryptionService
from app.db.base import Base
from app.models import LLMModel, User, UserSettings
from app.repositories.model_registry import ModelRegistryRepository
from app.schemas.models import ModelCreate, ModelUpdate
from app.services.model_registry import ModelNotFoundError, ModelRegistryService


def make_service() -> tuple[Session, ModelRegistryService]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    encryption = EncryptionService(Settings())
    return session, ModelRegistryService(ModelRegistryRepository(session), encryption)


def add_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4()}@example.com",
        password_hash="hash",
    )
    session.add(user)
    session.commit()
    return user


def test_model_registry_is_tenant_scoped_and_redacts_api_key() -> None:
    session, service = make_service()
    owner = add_user(session)
    other_user = add_user(session)

    created = service.create_model(
        owner.id,
        ModelCreate(
            name="llama-3.3-70b",
            provider="groq",
            role_type="writer",
            api_key="owner-secret",
        ),
    )

    assert created.has_api_key is True
    assert not hasattr(created, "api_key")
    assert len(service.list_models(owner.id)) == 1
    assert service.list_models(other_user.id) == []

    stored = session.scalar(select(LLMModel).where(LLMModel.id == created.id))
    assert stored is not None
    assert stored.api_key_encrypted != "owner-secret"
    assert service.decrypt_api_key(stored) == "owner-secret"

    try:
        service.update_model(other_user.id, created.id, ModelUpdate(name="hijack"))
    except ModelNotFoundError:
        pass
    else:
        raise AssertionError("A different tenant must not update this model")


def test_role_resolution_honors_user_default_model() -> None:
    session, service = make_service()
    user = add_user(session)
    first = service.create_model(
        user.id,
        ModelCreate(name="first", provider="groq", role_type="reviewer"),
    )
    second = service.create_model(
        user.id,
        ModelCreate(name="preferred", provider="gemini", role_type="reviewer"),
    )
    session.add(UserSettings(user_id=user.id, default_models_json=f'{{"reviewer":"{second.id}"}}'))
    session.commit()

    selected = service.resolve_model(user.id, "reviewer")

    assert selected.id == second.id
    assert selected.id != first.id
