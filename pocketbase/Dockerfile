FROM alpine:3.20

ARG PB_VERSION=0.22.22

RUN apk add --no-cache ca-certificates unzip wget

WORKDIR /pb
RUN wget -q https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_amd64.zip \
    && unzip pocketbase_${PB_VERSION}_linux_amd64.zip \
    && rm pocketbase_${PB_VERSION}_linux_amd64.zip \
    && chmod +x pocketbase

# Migrations and hooks ship with the image — PB auto-applies migrations on startup
# and loads hooks for runtime policy such as signup disablement.
COPY pb_migrations /pb/pb_migrations
COPY pb_hooks /pb/pb_hooks

# Content seed JSON is consumed by 1700000100_seed_data.js. Kept
# outside /pb/pb_data so it is never written to at runtime.
COPY seeds /pb_seeds

EXPOSE 8090

CMD ["/pb/pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb/pb_data", "--migrationsDir=/pb/pb_migrations", "--hooksDir=/pb/pb_hooks"]
