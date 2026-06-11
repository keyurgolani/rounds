FROM python:3.12-slim

# Runtime deps for the code runner:
#   - Node 22 (LTS) — required for `node --test` over TS files via the
#     tsx loader, and for the modern fetch global some rounds exercise.
#   - tsx (pinned major) — a TypeScript loader so test commands like
#     `node --import tsx --test path/to/foo.test.ts` resolve TS imports
#     cleanly without depending on Node's --experimental-strip-types.
#   - Python ships with the base image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g tsx@4 \
    && apt-get purge -y curl gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent volume mount point. Hosts with ephemeral filesystems (Render
# free tier, etc.) should attach a disk here; single-box hosts with a
# durable volume (Fly.io, Railway) should mount it to /app/data.
RUN mkdir -p /app/data

# Deploy platforms (Fly/Render/Railway/Cloud Run) set $PORT; fall back to
# 8000 for docker-compose and local usage. --reload is dev-only and is
# intentionally omitted here.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
