"""Image normalization helpers (EXIF orientation, size)."""

import io

from PIL import Image, ImageOps

MAX_EDGE = 2048


def normalize_upload(data: bytes) -> bytes:
    """Fix EXIF rotation, drop alpha/metadata, cap size. Returns PNG bytes."""
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
    except Exception as exc:  # noqa: BLE001 — Pillow raises many types
        raise ValueError("Immagine non valida") from exc
    img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def output_size_for(data: bytes) -> str:
    """Match the source aspect so the edit does not reframe the photo.

    Portrait → 1024x1536 (pack default), landscape → 1536x1024, ~square → 1024x1024.
    """
    w, h = Image.open(io.BytesIO(data)).size
    ratio = w / h
    if ratio < 0.85:
        return "1024x1536"
    if ratio > 1.18:
        return "1536x1024"
    return "1024x1024"
