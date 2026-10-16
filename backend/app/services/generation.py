"""GPT Image 2: analysis boards and try-on edits.

DB transactions are committed before each image call (which can take a
minute) so no connection is held open while waiting for OpenAI.
"""

import asyncio
import base64
from functools import lru_cache

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..config import get_settings
from ..db_models import Image, Profile, User
from ..models import StyleRequest
from ..prompts import boards as B
from ..prompts import image_templates as T
from .imaging import output_size_for

TREND_IT = {"low": "timeless, low trend influence", "moderate": "balanced, moderate trend influence",
            "high": "trend-forward, high trend influence"}

EXTENSION = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}

# Full-body outfit photos are always vertical, whatever the source framing.
FULL_BODY_SIZE = "1024x1536"

ImageFile = tuple[str, bytes, str]


@lru_cache
def client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key or None)


def output_mime() -> str:
    return f"image/{get_settings().image_output_format}"


async def _file(session: AsyncSession, image: Image) -> ImageFile:
    data = await storage.image_bytes(session, image)
    return f"{image.id}.{EXTENSION[image.mime]}", data, image.mime


async def _edit(images: list[ImageFile], prompt: str, size: str, quality: str) -> bytes:
    settings = get_settings()
    # NB: input_fidelity is intentionally NOT sent for gpt-image-2.
    result = await client().images.edit(
        model=settings.image_model,
        image=images,
        prompt=prompt,
        size=size,
        quality=quality,
        output_format=settings.image_output_format,
        n=1,
    )
    return base64.b64decode(result.data[0].b64_json)


def style_text(req: StyleRequest | None) -> str:
    if req is None:
        return "Not specified."
    lines = [f"Primary style: {req.selected_styles[0]}"]
    if len(req.selected_styles) > 1:
        lines.append(f"Secondary style (blend coherently): {req.selected_styles[1]}")
    lines.append(f"Trend preference: {TREND_IT[req.trend_preference]}")
    # Free text is user-provided: passed as quoted preferences, never as instructions.
    if req.occasion:
        lines.append(f'Occasion (user words): "{req.occasion}"')
    if req.comfort_preferences:
        lines.append(f'Comfort and wardrobe preferences (user words): "{req.comfort_preferences}"')
    if req.free_text_style_request:
        lines.append(f'Additional style wishes (user words): "{req.free_text_style_request}"')
    lines.append("Explicit user preferences override generic style conventions.")
    return "\n".join(lines)


# ---------------------------------------------------------------- boards
async def _board_request(session: AsyncSession, profile: Profile, kind: str) -> tuple[list[ImageFile], str]:
    """Collects input images and prompt for one board (DB reads only)."""
    boards = profile.boards or {}
    images = [await _file(session, await storage.get_image(session, profile, None))]
    if kind != "SEASON":
        images.append(await _file(session, await storage.get_image(session, profile, boards["SEASON"])))

    liked: list[int] = []
    disliked: list[int] = []
    previous = boards.get(kind)
    if previous and kind != "SEASON":
        fb = await storage.feedback_state(session, profile)
        pick = lambda pool: sorted(int(e.split(":")[1]) for e in pool if e.startswith(f"{previous}:"))
        liked, disliked = pick(fb.liked), pick(fb.disliked)
        if liked or disliked:
            images.append(await _file(session, await storage.get_image(session, profile, previous)))

    req = StyleRequest(**profile.style_request) if profile.style_request else None
    return images, B.build(kind, style_text(req), liked, disliked)


def _store_board(session: AsyncSession, profile: Profile, kind: str, data: bytes, prompt: str) -> Image:
    settings = get_settings()
    image = storage.add_image(
        session, profile, data, output_mime(), operation="BOARD", board_kind=kind,
        prompt_version=B.BOARDS[kind].version_tag, prompt=prompt,
        quality=settings.board_quality, size=settings.board_size,
    )
    storage.set_board(profile, kind, image.id)
    return image


async def _generate_boards(session: AsyncSession, profile: Profile, kinds: list[str]) -> None:
    settings = get_settings()
    requests = [await _board_request(session, profile, k) for k in kinds]
    await session.commit()  # release the connection during the image calls
    results = await asyncio.gather(*(
        _edit(images, prompt, settings.board_size, settings.board_quality) for images, prompt in requests
    ))
    for kind, (_, prompt), data in zip(kinds, requests, results):
        _store_board(session, profile, kind, data, prompt)


async def analyze(session: AsyncSession, profile: Profile) -> None:
    """Upload → season & palette board."""
    await _generate_boards(session, profile, ["SEASON"])
    profile.status = "analyzed"
    await session.commit()


async def build_style_boards(session: AsyncSession, user: User, profile: Profile, req: StyleRequest) -> None:
    """Style choice → hair, hair color, outfit and accessories boards in parallel."""
    if "SEASON" not in (profile.boards or {}):
        raise ValueError("Il profilo deve essere analizzato prima di scegliere lo stile")
    storage.add_style_choice(session, user, profile, req)
    await _generate_boards(session, profile, list(B.STYLE_BOARDS))
    profile.status = "styled"
    await session.commit()


async def regenerate_board(session: AsyncSession, profile: Profile, kind: str) -> None:
    if kind != "SEASON" and profile.style_request is None:
        raise ValueError("Scegli prima il tuo stile")
    await _generate_boards(session, profile, [kind])
    await session.commit()


# ---------------------------------------------------------------- try-on
async def try_on(session: AsyncSession, profile: Profile, operation: str, option: int,
                 parent_image_id: str | None = None, mode: str = "preview",
                 setting: str = "auto") -> Image:
    """One targeted edit on top of parent_image_id using a board panel as reference."""
    settings = get_settings()
    _, board_kind = T.TEMPLATES[operation]
    board_id = (profile.boards or {}).get(board_kind)
    if board_id is None:
        raise ValueError("Board non ancora generata: scegli prima il tuo stile")

    parent = await storage.get_image(session, profile, parent_image_id)
    if parent.operation == "BOARD":
        raise ValueError("Le prove si applicano a una foto, non a una board")
    parent_file = await _file(session, parent)
    board_file = await _file(session, await storage.get_image(session, profile, board_id))

    # Outfits are full-body and vertical; other edits keep the parent's framing.
    size = FULL_BODY_SIZE if operation == "OUTFIT" else output_size_for(parent_file[1])
    quality = settings.final_quality if mode == "final" else settings.preview_quality
    version, prompt = T.build(operation, option, B.OPTION_LABELS[option], setting)

    await session.commit()
    data = await _edit([parent_file, board_file], prompt, size, quality)
    image = storage.add_image(
        session, profile, data, output_mime(), parent_image_id=parent.id, operation=operation,
        reference_board_id=board_id, option=option,
        setting=setting if operation == "OUTFIT" else None,
        prompt_version=version, prompt=prompt, quality=quality, size=size,
    )
    await session.commit()
    return image
