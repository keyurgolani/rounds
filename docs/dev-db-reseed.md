# Dev DB cleanup: clearing legacy seed samples

On 2026-05-16, the AI Coding and Take-Home seed migrations
(`pocketbase/pb_migrations/1700001200_ai_coding_seed.js` and
`pocketbase/pb_migrations/1700001400_take_home_seed.js`) were edited in place
to remove their original sample problems. The samples are being replaced by
curated brief catalogs under `docs/briefs/`, which will be turned into new
seed entries in later sessions.

PocketBase doesn't re-run a migration whose filename is already recorded in
`_migrations`. So any dev DB that was created or updated before 2026-05-16
still has the legacy samples sitting in `ai_coding_rounds` and
`take_home_assignments`. This doc covers how to clean them out.

## Slugs to remove

AI Coding (`ai_coding_rounds`):
- `async-bugs-py`
- `cart-bugfix-py`
- `log-parser-ts`
- `rate-limiter-ts`
- `word-count-py`

Take-Home (`take_home_assignments`):
- `csv-summarize-py`
- `event-bus-ts`
- `kv-store-py`

## Option 1: Admin UI delete (recommended for one-offs)

1. Start PocketBase: `cd pocketbase && ./pocketbase serve`
2. Open `http://127.0.0.1:8090/_/` and log in as admin.
3. In the **Collections** sidebar, click `ai_coding_rounds`. Select each of the
   5 slugs above and delete (or filter by `slug ~ "async-bugs-py" || ...`).
4. Repeat for `take_home_assignments` and the 3 slugs above.

## Option 2: Rebuild the dev DB

If you don't care about local progress / draft data, the simplest path:

```bash
cd pocketbase
rm -rf pb_data
./pocketbase serve
# Migrations re-run on a fresh DB; the now-empty seed arrays produce no rows.
```

After this, the seed catalog implementation sessions can add new entries to
the (still-named) `1700001200_ai_coding_seed.js` and `1700001400_take_home_seed.js`
migration files, and editing those files in place will work cleanly on the
fresh DB.

## Why we didn't add a new "cleanup" migration

A separate migration that explicitly deleted the legacy slugs would split
source of truth (creates X here, deletes X over there) and leave migration
history detritus that the eventual end-of-roadmap migration squash would have
to reconcile. Editing the seed files in place keeps one file = final state
and makes the squash trivial. See
`docs/superpowers/specs/2026-05-15-real-world-and-ai-coding-catalog-design.md`,
"Seed cleanup" section.
