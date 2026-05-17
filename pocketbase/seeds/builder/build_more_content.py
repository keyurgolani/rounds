"""Build the consolidated `more_content.json` seed file.

Generates 17 system-design questions + 17 behavioural questions + the
'Amazon Leadership Principles' category. The fresh-release data seed
migration consumes this artifact.

Run from the repo root:
    python -m pocketbase.seeds.builder.build_more_content

Or from pocketbase/seeds:
    python -m builder.build_more_content
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SEEDS_DIR = REPO_ROOT / "pocketbase" / "seeds"
OUT_FILE = SEEDS_DIR / "more_content.json"


def main() -> int:
    sys.path.insert(0, str(SEEDS_DIR))
    try:
        from builder.sd_questions import ALL_SDQS  # type: ignore
        from builder.bq_questions import ALL_BQS  # type: ignore
    finally:
        sys.path.pop(0)

    payload = {
        # New behavioural categories — questions reference these by name.
        "behavioral_categories": [
            {
                "name": "Amazon Leadership Principles",
                "description": "Amazon's 16 Leadership Principles framing for behavioural questions.",
                "color": "#FF9900",
                "icon": "Star",
            },
            {
                "name": "AI Collaboration",
                "description": "Stories about partnering with AI tools, verifying AI output, knowing when NOT to use AI, and adopting / updating beliefs as the tooling lands. Maps to Meta's AI-Native Behavioral signal areas (AI-Driven Impact, Continuous AI Learning, Safe & Responsible AI).",
                "color": "#6366f1",
                "icon": "Sparkles",
            },
        ],
        "system_design_questions": ALL_SDQS,
        "behavioral_questions": ALL_BQS,
    }
    OUT_FILE.write_text(json.dumps(payload, indent=2))
    size = OUT_FILE.stat().st_size
    print(
        f"Wrote {OUT_FILE.relative_to(REPO_ROOT)} "
        f"(sdqs={len(ALL_SDQS)}, bqs={len(ALL_BQS)}, {size:,} bytes)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
