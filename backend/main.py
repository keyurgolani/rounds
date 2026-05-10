import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import ai, ai_coding, pdf, runner, share

app = FastAPI(title="Rounds — Code Runner", version="1.0.0")

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
)

app.include_router(runner.router)
app.include_router(pdf.router)
app.include_router(ai.router)
app.include_router(ai_coding.router)
app.include_router(share.router)


# Plain /health (no /api prefix) — the top-level /api/health path is
# owned by PocketBase in production, so we expose this for container
# health checks only.
@app.get("/health")
def health():
    return {"status": "ok"}
