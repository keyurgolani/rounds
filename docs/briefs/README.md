# Brief catalogs

This directory holds curated catalogs of interview-style problem briefs.
Each brief is a structured block — slug, scenario, tasks, evaluation signals,
companies — that describes one problem at enough specificity to later be
implemented as a full seed migration (starter code, hidden tests, harness,
rubric).

Catalogs:

- [`ai-assisted-coding.md`](./ai-assisted-coding.md) — 20 briefs for the
  AI Assisted Coding track (`/ai-coding`). Five flavor families:
  audit, drive, debug-refactor, prompt-spec, mini-app.
- [`real-world-problems.md`](./real-world-problems.md) — 20 briefs for the
  Real World Problems track (`/take-home`, formerly "Builder Problems").
  Four flavor families: services-apis, data-etl, concurrency-systems,
  domain-modeled.

**Schema reference:** see the design spec at
`docs/superpowers/specs/2026-05-15-real-world-and-ai-coding-catalog-design.md`.

**Sourcing posture:** sources lean heavily on Meta's AI-assisted coding
round material (2024–2025) and adjacent FAANG/scaleup take-home archetypes.
The `companies` field on each brief tags actual companies, not "X-style"
hedges.

**Lifecycle:** these briefs feed later sessions that build full seed
migrations under `pocketbase/pb_migrations/1700001200_ai_coding_seed.js`
(AI Coding) and `pocketbase/pb_migrations/1700001400_take_home_seed.js`
(Real World Problems). Those seed migrations were emptied in place
during the same round that produced this catalog.
