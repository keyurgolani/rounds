import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from app import admission, definitions, errors, gates, obs
from execution import runtime as execution_runtime
from routers import ai, ai_coding, pdf, runner, sd_practice, share, take_home


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Gates are read once per process; the startup log lists each value.
    gates.init()
    # Every stored definition's checksum is checked once per process; a
    # mismatch logs definition.rejected and that version fails closed.
    definitions.init()
    # The execution worker runs only while ROUNDS_GATE_EXECUTION_STORE is
    # on and ROUNDS_EXECUTION_SECRET logs in (ROUNDS-00A-L03).
    await execution_runtime.start()
    try:
        yield
    finally:
        await execution_runtime.stop()


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

# Middleware runs outermost-last-added: CORS (so denials still carry
# CORS headers), then admission for the execution and render routes.
app.add_middleware(admission.AdmissionMiddleware)
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


# Readiness (ROUNDS-00A-L03). With the execution store on and the worker
# secret set, ready only while the worker is logged in and the store
# answers; otherwise the same as /health. /health stays liveness.
@app.get("/ready")
def ready():
    state = execution_runtime.readiness()
    body = {"status": "ok" if state["ready"] else "unready", "store": state["store"]}
    return JSONResponse(body, status_code=200 if state["ready"] else 503)
