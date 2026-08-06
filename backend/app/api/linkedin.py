import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Header, HTTPException
from jose import JWTError, jwt

from app.core.config import Settings
from app.core.dependencies import Container, CurrentUserId, DatabaseSession
from app.integrations.publishers import LinkedInPublisher
from app.repositories.publishing import PublishingRepository
from app.schemas.publishing import LinkedInConnectionRead, PublishHistoryRead
from app.services.publishing import (
    PostNotPublishableError,
    PublisherAccountRequiredError,
    PublisherService,
    PublishFailedError,
)

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


def _state_token(settings: Settings, user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "purpose": "linkedin_oauth",
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _service(db, container) -> PublisherService:
    return PublisherService(
        PublishingRepository(db),
        container.publishers,
        container.encryption,
        container.settings,
    )


@router.get("/oauth/start")
def linkedin_oauth_start(user_id: CurrentUserId, container: Container) -> dict[str, str]:
    settings = container.settings
    if not settings.linkedin_client_id or not settings.linkedin_client_secret:
        raise HTTPException(status_code=503, detail="LinkedIn OAuth is not configured")
    state = _state_token(settings, user_id)
    params = urlencode(
        {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": settings.linkedin_redirect_uri,
            "state": state,
            "scope": " ".join(settings.linkedin_scopes.split(",")),
        }
    )
    return {"authorization_url": f"https://www.linkedin.com/oauth/v2/authorization?{params}"}


@router.get("/oauth/callback")
def linkedin_oauth_callback(
    code: str,
    state: str,
    db: DatabaseSession,
    container: Container,
) -> dict[str, str]:
    try:
        claims = jwt.decode(
            state,
            container.settings.jwt_secret_key,
            algorithms=[container.settings.jwt_algorithm],
        )
        if claims.get("purpose") != "linkedin_oauth":
            raise ValueError
        user_id = uuid.UUID(claims["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc
    publisher = container.publishers.get("linkedin")
    if not isinstance(publisher, LinkedInPublisher):
        raise HTTPException(status_code=500, detail="LinkedIn publisher unavailable")
    token_data = publisher.exchange_code(code)
    profile_urn = publisher.fetch_profile_urn(token_data["access_token"])
    _service(db, container).save_linkedin_account(user_id, token_data, profile_urn)
    return {"status": "connected", "profile_urn": profile_urn}


@router.get("/connection", response_model=LinkedInConnectionRead)
def linkedin_connection(user_id: CurrentUserId, db: DatabaseSession) -> LinkedInConnectionRead:
    account = PublishingRepository(db).get_account(user_id)
    return LinkedInConnectionRead(
        connected=account is not None,
        profile_urn=account.profile_urn if account else None,
        expires_at=account.expires_at if account else None,
    )


@router.post("/publish/{post_id}", response_model=PublishHistoryRead)
def publish_linkedin(
    post_id: uuid.UUID,
    user_id: CurrentUserId,
    db: DatabaseSession,
    container: Container,
    x_idempotency_key: Annotated[str | None, Header()] = None,
    dry_run: bool | None = None,
) -> PublishHistoryRead:
    try:
        history = _service(db, container).publish(
            user_id,
            post_id,
            idempotency_key=x_idempotency_key,
            dry_run=dry_run,
        )
        return PublishHistoryRead.model_validate(history)
    except PublisherAccountRequiredError as exc:
        raise HTTPException(status_code=409, detail="LinkedIn account is not connected") from exc
    except PostNotPublishableError as exc:
        raise HTTPException(status_code=409, detail="Post is not publishable") from exc
    except PublishFailedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
