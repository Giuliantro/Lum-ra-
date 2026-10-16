import logging

import openai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import NotConfigured, get_settings
from .routers import profiles, users
from .storage import NotFound

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("lumera")

settings = get_settings()
app = FastAPI(title="Luméra API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(users.router)
app.include_router(profiles.router)


def _error(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


@app.exception_handler(NotConfigured)
async def _not_configured(_: Request, exc: NotConfigured):
    log.error(str(exc))
    return _error(503, str(exc))


@app.exception_handler(NotFound)
async def _not_found(_: Request, exc: NotFound):
    return _error(404, "Profilo non trovato")


@app.exception_handler(KeyError)
async def _key_error(_: Request, exc: KeyError):
    return _error(404, str(exc.args[0]) if exc.args else "Non trovato")


@app.exception_handler(ValueError)
async def _value_error(_: Request, exc: ValueError):
    return _error(400, str(exc))


@app.exception_handler(openai.APIError)
async def _openai_error(_: Request, exc: openai.APIError):
    log.exception("OpenAI error")
    return _error(502, f"Errore del servizio AI: {exc.message}")


@app.get("/api/health")
def health():
    return {"ok": True, "image_model": settings.image_model}
