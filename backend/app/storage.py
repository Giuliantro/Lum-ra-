"""Data access for profiles, images, style choices and feedback (PostgreSQL).

Every lookup is scoped to the authenticated user: a profile that belongs to
someone else is reported as not found.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db_models import FeedbackEvent, Image, Profile, StyleChoice, User
from .models import (
    FeedbackEntry, ImageNode, LumeraProfile, ProfileSummary, StyleRequest, UserFeedback,
)


class NotFound(Exception):
    pass


def new_id() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------- profiles
def create_profile(session: AsyncSession, user: User) -> Profile:
    profile = Profile(id=new_id(), user_id=user.id, status="created", boards={})
    session.add(profile)
    return profile


async def get_profile(session: AsyncSession, user: User, profile_id: str) -> Profile:
    profile = await session.scalar(
        select(Profile).where(Profile.id == profile_id, Profile.user_id == user.id)
    )
    if profile is None:
        raise NotFound(profile_id)
    return profile


async def list_profiles(session: AsyncSession, user: User) -> list[ProfileSummary]:
    rows = await session.scalars(
        select(Profile).where(Profile.user_id == user.id).order_by(Profile.created_at.desc())
    )
    return [
        ProfileSummary(id=p.id, status=p.status, original_image_id=p.original_image_id, created_at=p.created_at)
        for p in rows
    ]


def set_board(profile: Profile, kind: str, image_id: str) -> None:
    # Reassign: in-place mutation of a JSON column is not tracked.
    profile.boards = {**(profile.boards or {}), kind: image_id}


# ---------------------------------------------------------------- images
def add_image(session: AsyncSession, profile: Profile, data: bytes, mime: str, **fields) -> Image:
    image = Image(id=new_id(), profile_id=profile.id, data=data, mime=mime, **fields)
    session.add(image)
    return image


async def get_image(session: AsyncSession, profile: Profile, image_id: str | None) -> Image:
    """image_id None → the profile's original portrait."""
    target = image_id or profile.original_image_id
    image = await session.scalar(
        select(Image).where(Image.id == target, Image.profile_id == profile.id)
    )
    if image is None:
        raise KeyError(f"Immagine {target} non trovata")
    return image


async def image_bytes(session: AsyncSession, image: Image) -> bytes:
    return await session.scalar(select(Image.data).where(Image.id == image.id))


def to_node(image: Image) -> ImageNode:
    return ImageNode(
        image_id=image.id, parent_image_id=image.parent_image_id, operation=image.operation,
        board_kind=image.board_kind, reference_board_id=image.reference_board_id,
        option=image.option, setting=image.setting, prompt_version=image.prompt_version,
        quality=image.quality, size=image.size, created_at=image.created_at,
    )


# ---------------------------------------------------------------- style & feedback
def add_style_choice(session: AsyncSession, user: User, profile: Profile, req: StyleRequest) -> None:
    profile.style_request = req.model_dump()
    session.add(StyleChoice(user_id=user.id, profile_id=profile.id, **req.model_dump()))


def add_feedback(session: AsyncSession, user: User, profile: Profile, entry: FeedbackEntry) -> None:
    session.add(FeedbackEvent(user_id=user.id, profile_id=profile.id, **entry.model_dump()))


async def feedback_state(session: AsyncSession, profile: Profile) -> UserFeedback:
    """Replays events: LIKE and DISLIKE are mutually exclusive, the latest wins."""
    events = await session.scalars(
        select(FeedbackEvent).where(FeedbackEvent.profile_id == profile.id)
        .order_by(FeedbackEvent.created_at)
    )
    vote: dict[str, str] = {}
    saved: list[str] = []
    for e in events:
        if e.type in ("LIKE", "DISLIKE"):
            vote[e.entity_id] = e.type
        elif e.type == "SAVE" and e.entity_id not in saved:
            saved.append(e.entity_id)
    return UserFeedback(
        liked=[k for k, v in vote.items() if v == "LIKE"],
        disliked=[k for k, v in vote.items() if v == "DISLIKE"],
        saved=saved,
    )


async def to_api(session: AsyncSession, profile: Profile) -> LumeraProfile:
    images = await session.scalars(
        select(Image).where(Image.profile_id == profile.id).order_by(Image.created_at)
    )
    return LumeraProfile(
        id=profile.id,
        status=profile.status,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        original_image_id=profile.original_image_id,
        boards=profile.boards or {},
        style_request=StyleRequest(**profile.style_request) if profile.style_request else None,
        user_feedback=await feedback_state(session, profile),
        images=[to_node(i) for i in images],
    )
