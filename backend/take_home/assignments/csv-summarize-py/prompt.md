# CSV Summarizer

Implement `summarize(csv_path, out_path)` in `summarize.py`.

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
- Optional: `NOTES.md` with any trade-off you made (e.g., one-pass vs two-pass, how you handled malformed rows).

## Time budget

~45 minutes.
