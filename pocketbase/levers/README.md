# Account-scope emergency levers

Operator templates for ROUNDS-00B-L01 (server-derived ownership on create and
update). These are NOT migrations: nothing in this folder runs automatically.
Copy a template into `pocketbase/pb_migrations/` with a real timestamp to use
it.

- `lock_collection.template.js` freezes one collection (create and update
  rules become `null`, superuser only) when its rules turn out too loose and a
  forward fix is not ready yet.
- `restore_collection.template.js` restores the server-derived ownership rules
  once the fix ships.
- `replay_quarantine.template.js` (ROUNDS-00B-L02) writes listed
  `relation_quarantine` entries back: a moved row exactly as it was, created
  and updated included, and a cleared field back to its target, through the
  relation triggers so only a same-owner entry replays. Run it with
  `pocketbase migrate up` pointed at a folder holding only the filled-in copy;
  `docs/operations.md` under "Relation endpoint authorization and quarantine"
  has the command, and `harness/probes/relation_quarantine_check.py` exercises
  it.

When to reach for the lock, and the alert that triggers it, are in
`docs/operations.md` under "Account-scope rules". Never run a lever against a
live deployment without a `pb_data` backup taken with PocketBase stopped.
`harness/migration_check.sh` exercises both templates on a throwaway stack.
