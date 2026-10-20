"""Read one collection's create or update rule straight from a PocketBase data.db.

harness/migration_check.sh uses this to check a migration's result without a
running PocketBase. It prints the rule text, or a marker:

  <<NULL>>        the rule is null (superuser only)
  <<ABSENT>>      the collection, or the _collections table, is not there
  <<ERROR: ...>>  the database could not be read for any other reason

Only a missing _collections table (or collection) reads as absent; every other
SQLite error is an error, so a check in migration_check.sh can never pass on a
read that did not actually happen.
"""
from __future__ import annotations

import sqlite3
import sys

_COLUMN = {"create": "createRule", "update": "updateRule"}


def read_rule(db: str, name: str, which: str) -> str:
    col = _COLUMN[which]  # a fixed column name, never interpolated from input
    try:
        conn = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT %s FROM _collections WHERE name = ?" % col, (name,)
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error as err:
        msg = str(err).lower()
        if "no such table" in msg or "no such collection" in msg:
            return "<<ABSENT>>"
        return "<<ERROR: %s>>" % err
    if row is None:
        return "<<ABSENT>>"
    return "<<NULL>>" if row[0] is None else row[0]


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[2] not in _COLUMN:
        print("usage: read_collection_rule.py DB COLLECTION create|update", file=sys.stderr)
        return 2
    print(read_rule(argv[0], argv[1], argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
