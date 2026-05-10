# CSV Summarizer

A small data team you're joining keeps re-implementing the same five
lines of CSV math in every script — count, mean, max, min. Today they
want **one** tiny library function that does it once, predictably, with
a JSON output the rest of the pipeline can rely on. The shape is
simple, but the empty-input case has bitten them twice.

Your job: implement `summarize(csv_path, out_path)` in `summarize.py`
so a teammate can drop it into any script and trust the contract.

## Contract

Read a CSV file at `csv_path`. The file has two columns:

```csv
name,score
Alice,87
Bob,92
Carol,71
```

Write a JSON file to `out_path`:

```json
{"count": 3, "mean_score": 83.33, "max": {"name": "Bob", "score": 92}, "min": {"name": "Carol", "score": 71}}
```

For an **empty** CSV (header row only, no data), the output is exactly:

```json
{"count": 0}
```

(no other keys.)

## Constraints

- Use Python's standard library only (`csv`, `json`).
- Names may contain spaces; CSV quoting follows the default `csv` module dialect.
- The score column is integer-valued.
- Mean precision: use float; the harness allows up to 0.001 absolute error.

## Deliverables

- `summarize.py` implementing the function.
- `NOTES.md` — a short paragraph on the trade-off you made (one-pass
  vs two-pass, how you'd handle malformed rows, what you'd add next).
  The reviewer reads this alongside your code.

## Time budget

~45 minutes. The grading harness runs in a few seconds; iterate freely.
