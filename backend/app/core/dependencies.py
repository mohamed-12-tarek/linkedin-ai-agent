import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.container import ApplicationContainer
from app.db.session import get_db
from app.models import User

DatabaseSession = Annotated[Session, Depends(get_db)]


def get_container(request: Request) -> ApplicationContainer:
    return request.app.state.container


def get_current_user_id(
    db: DatabaseSession,
    x_user_id: Annotated[uuid.UUID, Header(alias="X-User-ID")],
) -> uuid.UUID:
    user_id = db.scalar(select(User.id).where(User.id == x_user_id))
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user_id


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
Container = Annotated[ApplicationContainer, Depends(get_container)]
