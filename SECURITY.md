# Security Policy

## Reporting

Please report security issues privately by opening a GitHub security advisory or contacting the project maintainer directly. Do not publish exploit details before a fix is available.

## Supported Versions

The first public release line is `1.x`.

## Hosted Instances

- Set `ROUNDS_DISABLE_SIGNUPS=true` and `VITE_DISABLE_SIGNUPS=true` for invite-only deployments.
- Set strong `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD` only through deployment secrets or a private `.env` file.
- Restrict `CORS_ALLOW_ORIGINS` to your production domain.
- Back up the PocketBase volume regularly.
