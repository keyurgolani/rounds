FROM alpine:3.20

ARG PB_VERSION=0.22.22
# SHA-256 of the pinned release zips, published in the PocketBase release's
# checksums.txt. The download is verified against the digest for the build's
# target architecture so a tampered or truncated archive fails the build
# instead of shipping. Production and CI build linux/amd64 (PB_SHA256); the
# arm64 digest only exists so the security harness can build and run the same
# pinned version natively on an arm64 developer machine. Update both in
# lockstep whenever PB_VERSION changes.
ARG PB_SHA256=330714769484fcc77306ab9f14c25e9f4d9b4ffd8b5b16385a70199db4206978
ARG PB_SHA256_ARM64=a1c99caa1099de61968b66a4be536f7d85969d01ea4f8ae7e21c85194dbcc79f
# Injected automatically by BuildKit as the build's target architecture.
# Declared without a default so BuildKit's value is not shadowed; the RUN
# falls back to amd64 (prod/CI) when a non-BuildKit builder leaves it empty.
ARG TARGETARCH

RUN apk add --no-cache ca-certificates unzip wget

WORKDIR /pb
RUN PB_TARGETARCH="${TARGETARCH:-amd64}" \
    && case "${PB_TARGETARCH}" in \
      amd64) PB_ARCH=amd64; PB_EXPECTED_SHA256="${PB_SHA256}" ;; \
      arm64) PB_ARCH=arm64; PB_EXPECTED_SHA256="${PB_SHA256_ARM64}" ;; \
      *) echo "unsupported TARGETARCH=${PB_TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && wget -q "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_${PB_ARCH}.zip" \
    && echo "${PB_EXPECTED_SHA256}  pocketbase_${PB_VERSION}_linux_${PB_ARCH}.zip" | sha256sum -c - \
    && unzip "pocketbase_${PB_VERSION}_linux_${PB_ARCH}.zip" \
    && rm "pocketbase_${PB_VERSION}_linux_${PB_ARCH}.zip" \
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
