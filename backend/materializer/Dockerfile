# Legacy Artifact Snapshot materializer (ROUNDS-00A-L04).
#
# Builds from the repository root, because it bundles the frontend's resume
# templates:
#
#   docker build -f backend/materializer/Dockerfile .
#
# Dockerfile.dockerignore, next to this file, admits only
# backend/materializer/, the template, type, util, and export shell
# sources, and frontend/package.json for its module type, so nothing else
# in the repository reaches the build. The image holds the bundle and the
# server, no package manager cache, no secret, and runs as an unprivileged
# user.
# TODO(ROUNDS-34-L08): #182's root build contexts absorb this one.

FROM node:22-alpine AS build
WORKDIR /build

COPY backend/materializer/package.json backend/materializer/package-lock.json backend/materializer/
RUN npm ci --prefix backend/materializer --no-audit --no-fund

COPY frontend/src/features/resume/templates/ frontend/src/features/resume/templates/
COPY frontend/src/features/resume/types.ts frontend/src/features/resume/utils.ts frontend/src/features/resume/
COPY frontend/src/features/resume/links/types.ts frontend/src/features/resume/links/
COPY frontend/src/features/resume/export/shell.ts frontend/src/features/resume/export/
# esbuild reads the frontend's module type from here to choose how the
# templates import React, so the image bundles what a checkout does, byte
# for byte.
COPY frontend/package.json frontend/
COPY backend/materializer/build.mjs backend/materializer/
COPY backend/materializer/src/ backend/materializer/src/
RUN node backend/materializer/build.mjs

FROM node:22-alpine
ENV NODE_ENV=production \
    PORT=4100
WORKDIR /app
COPY --from=build /build/backend/materializer/dist/materialize.mjs dist/materialize.mjs
COPY backend/materializer/server.mjs ./
USER 10001:10001
EXPOSE 4100
CMD ["node", "--max-old-space-size=192", "server.mjs"]
