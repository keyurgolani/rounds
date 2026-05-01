# Contributing

Thanks for considering a contribution to Rounds.

## Development Setup

1. Copy `.env.example` to `.env`.
2. Run `docker compose up -d` for the full stack.
3. For frontend-only work, run `npm ci` and `npm run dev` inside `frontend/`.

## Verification

Run these before opening a pull request:

```sh
npm --prefix frontend test
npm --prefix frontend run build
python3.12 -m venv /tmp/rounds-backend-venv
/tmp/rounds-backend-venv/bin/python -m pip install -r backend/requirements.txt
/tmp/rounds-backend-venv/bin/python -m pytest backend
```

## Guidelines

- Keep changes focused and small.
- Do not commit `.env`, local PocketBase data, caches, or build output.
- Update docs when behavior, deployment, migrations, or environment variables change.
- Shared PocketBase content belongs in `pocketbase/seeds/` and is loaded by the consolidated seed migration.
