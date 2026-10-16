from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user
from ..db import get_session
from ..db_models import User
from ..models import UserOut, UserUpdate

router = APIRouter(prefix="/api/me", tags=["users"])


def _out(user: User) -> UserOut:
    return UserOut(
        id=user.id, email=user.email, first_name=user.first_name, last_name=user.last_name,
        age=user.age, profile_complete=bool(user.first_name and user.last_name and user.age),
    )


@router.get("", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> UserOut:
    """Current user; the row is created from Clerk on the first call."""
    return _out(user)


@router.put("", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    """Onboarding / profile edit: first name, last name, age. Email is managed by Clerk."""
    user.first_name = body.first_name.strip()
    user.last_name = body.last_name.strip()
    user.age = body.age
    await session.commit()
    return _out(user)


@router.delete("", status_code=204)
async def delete_me(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Deletes all Luméra data of the user (profiles, images, choices, feedback).

    The Clerk account itself is managed by Clerk.
    """
    await session.delete(user)
    await session.commit()
