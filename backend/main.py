import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from app import errors, gates, obs
from routers import ai, ai_coding, pdf, runner, sd_practice, share, take_home


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Gates are read once per process; the startup log lists each value.
    gates.init()
    yield


class RunnerApp(FastAPI):
    """Puts the correlation id outside Starlette's error handler, so
    every response carries it, an uncaught exception's 500 included."""

    def build_middleware_stack(self) -> ASGIApp:
        return obs.CorrelationIdMiddleware(super().build_middleware_stack())


app = RunnerApp(title="Rounds — Code Runner", version="1.0.0", lifespan=lifespan)

# CORS_ALLOW_ORIGINS accepts a comma-separated list. Default is permissive
# for local dev; production deployments should lock this down to the
# frontend origin.
_cors_env = os.environ.get("CORS_ALLOW_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
_cors_allow_credentials = _cors_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    # Cross-origin SPAs read the wait on a 429 and the support id.
    expose_headers=["Retry-After", obs.CORRELATION_HEADER],
)
# RunnerApp wraps everything above in CorrelationIdMiddleware, so CORS
# preflights and denials carry the request's correlation id too.
errors.install(app)

app.include_router(runner.router)
app.include_router(pdf.router)
app.include_router(ai.router)
app.include_router(ai_coding.router)
app.include_router(sd_practice.router)
app.include_router(share.router)
app.include_router(take_home.router)


# Plain /health (no /api prefix) — the top-level /api/health path is
# owned by PocketBase in production, so we expose this for container
# health checks only.
@app.get("/health")
def health():
    return {"status": "ok"}
