"""Clerk authentication.

The frontend sends the Clerk session token as `Authorization: Bearer <jwt>`.
The token is verified locally against Clerk's JWKS (RS256, exp/nbf, azp).
On the first authenticated request the user row is created from Clerk's
Backend API (email, first/last name).
"""

import asyncio
from functools import lru_cache

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import NotConfigured, get_settings
from .db import get_session
from .db_models import User

CLERK_API = "https://api.clerk.com/v1"


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(get_settings().jwks_url, cache_keys=True, lifespan=3600)


def _unauthorized(detail: str = "Accesso richiesto") -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def verify_token(token: str) -> dict:
    settings = get_settings()
    try:
        key = _jwks_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"], leeway=5,
            options={"require": ["exp", "nbf", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise _unauthorized("Sessione non valida o scaduta") from exc
    azp = claims.get("azp")
    if azp and azp not in settings.authorized_parties:
        raise _unauthorized("Origine non autorizzata")
    if claims.get("sts") == "pending":
        raise _unauthorized("Sessione non ancora attiva")
    return claims


async def _fetch_clerk_user(clerk_user_id: str) -> dict:
    if not get_settings().clerk_secret_key:
        raise NotConfigured("Clerk non configurato: imposta CLERK_SECRET_KEY nel backend")
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(
            f"{CLERK_API}/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {get_settings().clerk_secret_key}"},
        )
    if res.status_code != 200:
        raise HTTPException(502, "Impossibile recuperare l'utente da Clerk")
    return res.json()


def _primary_email(data: dict) -> str:
    primary = data.get("primary_email_address_id")
    emails = data.get("email_addresses") or []
    for e in emails:
        if e.get("id") == primary:
            return e["email_address"]
    return emails[0]["email_address"] if emails else ""


async def _get_or_create_user(session: AsyncSession, clerk_user_id: str) -> User:
    user = await session.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    if user:
        return user
    data = await _fetch_clerk_user(clerk_user_id)
    user = User(
        clerk_user_id=clerk_user_id,
        email=_primary_email(data),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        # Concurrent first requests: another one created the row.
        await session.rollback()
        user = await session.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    return user


async def current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise _unauthorized()
    claims = await asyncio.to_thread(verify_token, header.removeprefix("Bearer ").strip())
    return await _get_or_create_user(session, claims["sub"])


async def onboarded_user(user: User = Depends(current_user)) -> User:
    """Users must complete name, surname and age before using the stylist."""
    if not (user.first_name and user.last_name and user.age):
        raise HTTPException(403, "Completa il tuo profilo (nome, cognome, età) per continuare")
    return user
