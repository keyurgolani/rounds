"""Scan service logs for issued credentials (ROUNDS-00B-L05).

No session token and no account or admin password may appear in a
service's logs. The scanner looks for the shapes the harness issues
(PocketBase session tokens, the account factory's passwords) and for any
literal value the caller registers, and reports only how many of each kind
it found and where, never the value.

Text logs are scanned line by line; a SQLite log database is opened
read-only and every text column of every table is scanned.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from receipts import JWT_RE, PASSWORD_RE


@dataclass
class Findings:
    tokens: int = 0
    passwords: int = 0
    literals: int = 0
    where: set[str] = field(default_factory=set)

    @property
    def clean(self) -> bool:
        return not (self.tokens or self.passwords or self.literals)

    def summary(self) -> str:
        if self.clean:
            return "clean"
        return (f"tokens={self.tokens} passwords={self.passwords} literals={self.literals} "
                f"in={','.join(sorted(self.where))}")


def scan_text(text: str, source: str, literals: tuple[str, ...] = (), into: Findings | None = None) -> Findings:
    out = into or Findings()
    for line in text.splitlines():
        hits = (len(JWT_RE.findall(line)), len(PASSWORD_RE.findall(line)),
                sum(line.count(v) for v in literals if v))
        if any(hits):
            out.tokens += hits[0]
            out.passwords += hits[1]
            out.literals += hits[2]
            out.where.add(source)
    return out


def scan_sqlite(path: str, source: str, literals: tuple[str, ...] = (), into: Findings | None = None) -> Findings:
    out = into or Findings()
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            for row in con.execute(f"SELECT * FROM {quoted}"):
                for value in row:
                    if isinstance(value, bytes):
                        value = value.decode("utf-8", "replace")
                    if isinstance(value, str):
                        scan_text(value, f"{source}:{table}", literals, out)
    finally:
        con.close()
    return out
