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

When to reach for the lock, and the alert that triggers it, are in
`docs/operations.md` under "Account-scope rules". Never run a lever against a
live deployment without a `pb_data` backup taken with PocketBase stopped.
`harness/migration_check.sh` exercises both templates on a throwaway stack.
