# rounds-worker (ROUNDS-00A-L05): the image every code worker runs.
#
# Builds from backend/:
#
#   docker build -f backend/worker/Dockerfile backend
#
# Dockerfile.dockerignore, next to this file, admits only the worker
# package, its two lockfiles, backend/drivers/, and the harness runtime, so
# no app code, definition, or secret reaches the image. It holds Python 3.12,
# Node 22, tsx, pytest, httpx, and bash, runs as 65532, and starts the
# worker's init as PID 1. The launcher runs it by digest only.
ARG TARGETARCH

# Python 3.12 by its multi-arch index digest, from
# https://hub.docker.com/v2/repositories/library/python/tags/3.12-slim
# (read 2026-11-11).
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS base

# Node 22.23.3 from nodejs.org, each tarball held to its published checksum,
# from https://nodejs.org/dist/v22.23.3/SHASUMS256.txt.
FROM base AS node-amd64
ADD --checksum=sha256:1084aa36196bba4c3a5e69a1ee388a6e4ff729dad09445fbcd434b28fe3c24af \
    https://nodejs.org/dist/v22.23.3/node-v22.23.3-linux-x64.tar.gz /node.tar.gz

FROM base AS node-arm64
ADD --checksum=sha256:5ced2d48d1d7198739b7f86804de0171aefb6823b684b12341d3321afc3cb0b2 \
    https://nodejs.org/dist/v22.23.3/node-v22.23.3-linux-arm64.tar.gz /node.tar.gz

FROM node-${TARGETARCH} AS node
RUN mkdir /opt/node \
    && tar -xzf /node.tar.gz -C /opt/node --strip-components=1 --no-same-owner \
    && rm -rf /node.tar.gz /opt/node/include /opt/node/share

FROM base AS tools
COPY --from=node /opt/node /opt/node
ENV PATH=/opt/node/bin:$PATH
# tsx exactly as worker/node/package-lock.json pins it, which was made with
# `npm install --package-lock-only --ignore-scripts` against
# https://registry.npmjs.org/. Install scripts stay off: esbuild finds its
# binary through its platform package.
COPY worker/node/package.json worker/node/package-lock.json /opt/rounds/node/
RUN cd /opt/rounds/node \
    && npm ci --omit=dev --ignore-scripts --no-audit --no-fund \
    && rm -rf /root/.npm
# pytest, httpx, and their dependencies, each by hash (worker/requirements.txt).
COPY worker/requirements.txt /tmp/worker-requirements.txt
RUN pip install --no-cache-dir --require-hashes --no-deps --only-binary=:all: -r /tmp/worker-requirements.txt

FROM base
COPY --from=node /opt/node /opt/node
COPY --from=tools /opt/rounds/node /opt/rounds/node
COPY --from=tools /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=tools /usr/local/bin/pytest /usr/local/bin/py.test /usr/local/bin/
# No package manager for Node in the worker.
RUN rm -rf /opt/node/lib/node_modules/npm /opt/node/lib/node_modules/corepack \
       /opt/node/bin/npm /opt/node/bin/npx /opt/node/bin/corepack
# The drivers, the harness runtime, and the worker's own init and protocol.
COPY drivers/ /opt/rounds/drivers/
COPY definitions/harness/rounds_harness.py /opt/rounds/harness/rounds_harness.py
COPY worker/__init__.py worker/frames.py worker/manifest.py worker/seccomp.py worker/init.py /opt/rounds/worker/
# Nothing the worker's user can change, and the mount point its tmpfs takes.
RUN chmod -R a-w /opt/rounds /opt/node \
    && mkdir -p /work
ENV PATH=/opt/node/bin:/opt/rounds/node/node_modules/.bin:/usr/local/bin:/usr/bin:/bin \
    LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1
USER 65532:65532
WORKDIR /work
ENTRYPOINT ["/usr/local/bin/python3", "-I", "-S", "/opt/rounds/worker/init.py"]
