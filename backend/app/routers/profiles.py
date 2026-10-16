from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..auth import onboarded_user
from ..db import get_session
from ..db_models import Profile, User
from ..models import (
    FeedbackEntry, ImageNode, LookVisualizeRequest, LumeraProfile, ProfileSummary,
    StyleRequest, TryOnRequest,
)
from ..prompts.boards import BOARDS
from ..services import generation
from ..services.imaging import normalize_upload

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024


async def _read_portrait(photo: UploadFile) -> bytes:
    data = await photo.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Foto troppo grande (max 15 MB)")
    return normalize_upload(data)


def _set_original(session: AsyncSession, profile: Profile, png: bytes) -> None:
    image = storage.add_image(session, profile, png, "image/png", operation="ORIGINAL")
    profile.original_image_id = image.id


@router.get("", response_model=list[ProfileSummary])
async def list_profiles(
    user: User = Depends(onboarded_user), session: AsyncSession = Depends(get_session),
) -> list[ProfileSummary]:
    """The user's Luméra Profiles, newest first."""
    return await storage.list_profiles(session, user)


@router.post("", response_model=LumeraProfile)
async def create_profile(
    photo: UploadFile,
    user: User = Depends(onboarded_user),
    session: AsyncSession = Depends(get_session),
) -> LumeraProfile:
    """Upload portrait → season & palette board."""
    png = await _read_portrait(photo)
    profile = storage.create_profile(session, user)
    await session.flush()
    _set_original(session, profile, png)
    await generation.analyze(session, profile)
    return await storage.to_api(session, profile)


@router.post("/{profile_id}/photo", response_model=LumeraProfile)
async def replace_photo(
    profile_id: str,
    photo: UploadFile,
    user: User = Depends(onboarded_user),
    session: AsyncSession = Depends(get_session),
) -> LumeraProfile:
    """Replace the portrait and re-run the analysis. Style and saved items are kept."""
    profile = await storage.get_profile(session, user, profile_id)
    _set_original(session, profile, await _read_portrait(photo))
    profile.boards = {}
    profile.status = "created"
    await generation.analyze(session, profile)
    if profile.style_request:
        await generation.build_style_boards(session, user, profile, StyleRequest(**profile.style_request))
    return await storage.to_api(session, profile)


@router.get("/{profile_id}", response_model=LumeraProfile)
async def get_profile(
    profile_id: str, user: User = Depends(onboarded_user), session: AsyncSession = Depends(get_session),
) -> LumeraProfile:
    return await storage.to_api(session, await storage.get_profile(session, user, profile_id))


@router.post("/{profile_id}/style", response_model=LumeraProfile)
async def set_style(
    profile_id: str,
    req: StyleRequest,
    user: User = Depends(onboarded_user),
    session: AsyncSession = Depends(get_session),
) -> LumeraProfile:
    """Style preferences (saved in style_choices) → hair, hair color, outfit and accessories boards."""
    profile = await storage.get_profile(session, user, profile_id)
    await generation.build_style_boards(session, user, profile, req)
    return await storage.to_api(session, profile)


@router.post("/{profile_id}/boards/{kind}/regenerate", response_model=LumeraProfile)
async def regenerate_board(
    profile_id: str, kind: str,
    user: User = Depends(onboarded_user), session: AsyncSession = Depends(get_session),
) -> LumeraProfile:
    """New version of one board; liked/disliked options of the previous one guide it."""
    if kind not in BOARDS:
        raise HTTPException(404, "Board sconosciuta")
    profile = await storage.get_profile(session, user, profile_id)
    await generation.regenerate_board(session, profile, kind)
    return await storage.to_api(session, profile)


@router.post("/{profile_id}/images", response_model=ImageNode)
async def try_on(
    profile_id: str,
    req: TryOnRequest,
    user: User = Depends(onboarded_user),
    session: AsyncSession = Depends(get_session),
) -> ImageNode:
    """One targeted edit on top of parent_image_id (default: original)."""
    profile = await storage.get_profile(session, user, profile_id)
    image = await generation.try_on(session, profile, req.operation, req.option,
                                    req.parent_image_id, req.mode, req.setting)
    return storage.to_node(image)


@router.post("/{profile_id}/looks/{option}/visualize", response_model=list[ImageNode])
async def visualize_look(
    profile_id: str,
    option: int,
    req: LookVisualizeRequest,
    user: User = Depends(onboarded_user),
    session: AsyncSession = Depends(get_session),
) -> list[ImageNode]:
    """Full look = same option from every board, applied as a chain of single edits."""
    if option not in (1, 2, 3):
        raise HTTPException(404, "Look non trovato")
    profile = await storage.get_profile(session, user, profile_id)
    steps = ["HAIR", "HAIR_COLOR", "OUTFIT"] + (["EYEWEAR"] if req.include_eyewear else [])
    nodes: list[ImageNode] = []
    parent = req.parent_image_id
    for operation in steps:
        image = await generation.try_on(session, profile, operation, option, parent, req.mode, req.setting)
        nodes.append(storage.to_node(image))
        parent = image.id
    return nodes


@router.get("/{profile_id}/images/{image_id}/file")
async def image_file(
    profile_id: str, image_id: str,
    user: User = Depends(onboarded_user), session: AsyncSession = Depends(get_session),
) -> Response:
    profile = await storage.get_profile(session, user, profile_id)
    image = await storage.get_image(session, profile, image_id)
    data = await storage.image_bytes(session, image)
    # Images are immutable: let the browser cache them privately.
    return Response(data, media_type=image.mime, headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.post("/{profile_id}/feedback", response_model=LumeraProfile)
async def add_feedback(
    profile_id: str,
    entry: FeedbackEntry,
    user: User = Depends(onboarded_user),
    session: AsyncSession = Depends(get_session),
) -> LumeraProfile:
    """Section 21 — explicit signals, stored as events; votes steer the next board version."""
    profile = await storage.get_profile(session, user, profile_id)
    await storage.get_image(session, profile, entry.entity_id.split(":")[0])
    storage.add_feedback(session, user, profile, entry)
    await session.commit()
    return await storage.to_api(session, profile)
