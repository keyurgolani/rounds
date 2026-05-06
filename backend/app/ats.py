"""Rule-based ATS scoring half.

Returns a deterministic score in [0, 100] derived from the resume's
structure and content. The AI half (impact / clarity / semantic
relevance) is layered on top in ``routers/ai.py`` when a provider key
is configured; this module is the always-on fallback so the ATS tab
shows something useful even before AI is set up.

Scoring weights (out of 100):

* contact (15)        — fullName, email, phone, location present
* sections (15)       — at least one work entry, education, skills group
* keywords (15)       — keyword density vs JD (or vs sane defaults if no JD)
* formatting (15)     — section headings, no super-long bullets
* dates (10)          — start dates present and formatted as YYYY-MM
* bullets (15)        — most experience entries have >= 2 bullets
* action verbs (15)   — ratio of bullets starting with strong action verbs

Suggestions are produced as we score so the user sees what's missing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Common, broadly-relevant strong verbs. Not exhaustive; the goal is
# to reward bullets that lead with action language.
ACTION_VERBS = {
    "achieved", "automated", "built", "championed", "coached", "collaborated",
    "consolidated", "coordinated", "created", "cut", "decreased", "delivered",
    "deployed", "designed", "developed", "drove", "engineered", "enabled",
    "established", "evaluated", "executed", "expanded", "facilitated",
    "founded", "generated", "grew", "guided", "headed", "implemented",
    "improved", "increased", "initiated", "instituted", "introduced",
    "launched", "led", "leveraged", "managed", "mentored", "migrated",
    "modernized", "optimized", "orchestrated", "organized", "owned",
    "partnered", "pioneered", "planned", "presented", "produced",
    "programmed", "redesigned", "reduced", "refactored", "researched",
    "resolved", "saved", "scaled", "secured", "shaped", "shipped",
    "simplified", "spearheaded", "standardized", "streamlined",
    "strengthened", "structured", "supervised", "supported", "tested",
    "trained", "transformed", "translated", "unblocked", "upgraded",
    "validated",
}


@dataclass
class ATSResult:
    score: int
    breakdown: dict[str, int]
    suggestions: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)


def score_resume(data: dict[str, Any], job_description: str | None = None) -> ATSResult:
    breakdown: dict[str, int] = {}
    suggestions: list[str] = []

    breakdown["contact"], cs = _score_contact(data)
    suggestions.extend(cs)

    breakdown["sections"], ss = _score_sections(data)
    suggestions.extend(ss)

    breakdown["keywords"], ks, missing = _score_keywords(data, job_description)
    suggestions.extend(ks)

    breakdown["formatting"], fs = _score_formatting(data)
    suggestions.extend(fs)

    breakdown["dates"], ds = _score_dates(data)
    suggestions.extend(ds)

    breakdown["bullets"], bs = _score_bullets(data)
    suggestions.extend(bs)

    breakdown["action_verbs"], avs = _score_action_verbs(data)
    suggestions.extend(avs)

    total = sum(breakdown.values())
    # Trim suggestion noise: keep at most 6, prefer the lowest-scoring
    # categories first.
    if len(suggestions) > 6:
        suggestions = suggestions[:6]

    return ATSResult(
        score=min(100, max(0, total)),
        breakdown=breakdown,
        suggestions=suggestions,
        missing_keywords=missing,
    )


# ----- individual scorers ------------------------------------------------


def _score_contact(data: dict[str, Any]) -> tuple[int, list[str]]:
    p = data.get("personalInfo") or {}
    bits = [
        ("name", bool((p.get("fullName") or "").strip())),
        ("email", bool((p.get("email") or "").strip())),
        ("phone", bool((p.get("phone") or "").strip())),
        ("location", bool((p.get("location") or "").strip())),
    ]
    present = sum(1 for _, ok in bits if ok)
    score = round((present / 4) * 15)
    suggestions: list[str] = []
    missing = [name for name, ok in bits if not ok]
    if missing:
        suggestions.append(f"Add contact info: {', '.join(missing)}.")
    return score, suggestions


def _score_sections(data: dict[str, Any]) -> tuple[int, list[str]]:
    has_exp = len(data.get("experience") or []) > 0
    has_edu = len(data.get("education") or []) > 0
    has_skills = len(data.get("skills") or []) > 0
    present = sum([has_exp, has_edu, has_skills])
    score = round((present / 3) * 15)
    suggestions: list[str] = []
    if not has_exp:
        suggestions.append("Add at least one work experience entry.")
    if not has_skills:
        suggestions.append("Add a Skills section grouped by category.")
    if not has_edu:
        suggestions.append("Add an Education section, even briefly.")
    return score, suggestions


def _score_keywords(
    data: dict[str, Any], jd: str | None
) -> tuple[int, list[str], list[str]]:
    text_blob = _resume_text(data).lower()
    if not jd or not jd.strip():
        # No JD — reward simply having a non-trivial skill section.
        skill_count = sum(len(g.get("items") or []) for g in data.get("skills") or [])
        score = min(15, round(skill_count * 1.5))
        suggestions: list[str] = []
        if skill_count < 8:
            suggestions.append(
                "Add more skills (target 8+) grouped into categories like Languages, Frameworks, Cloud."
            )
        return score, suggestions, []

    jd_terms = _extract_keywords(jd)
    if not jd_terms:
        return 8, [], []
    matched = [t for t in jd_terms if t in text_blob]
    missing = [t for t in jd_terms if t not in text_blob]
    coverage = len(matched) / max(1, len(jd_terms))
    score = round(coverage * 15)
    suggestions: list[str] = []
    if missing:
        suggestions.append(
            f"Missing JD keywords: {', '.join(missing[:6])}{'…' if len(missing) > 6 else ''}."
        )
    return score, suggestions, missing[:20]


def _score_formatting(data: dict[str, Any]) -> tuple[int, list[str]]:
    score = 15
    suggestions: list[str] = []
    long_bullets = 0
    for entry in (data.get("experience") or []) + (data.get("projects") or []):
        for b in entry.get("highlights") or []:
            if len(b) > 240:
                long_bullets += 1
    if long_bullets > 0:
        penalty = min(8, long_bullets * 2)
        score -= penalty
        suggestions.append(
            f"Shorten {long_bullets} long bullet(s) — aim for ~140–180 characters each."
        )
    summary = (data.get("personalInfo") or {}).get("summary") or ""
    if summary and len(summary) > 600:
        score -= 3
        suggestions.append("Trim the summary to 2–3 sentences.")
    return max(0, score), suggestions


def _score_dates(data: dict[str, Any]) -> tuple[int, list[str]]:
    entries = (data.get("experience") or []) + (data.get("education") or [])
    if not entries:
        return 0, []
    valid = 0
    for e in entries:
        s = (e.get("startDate") or "").strip()
        if re.match(r"^\d{4}-\d{2}", s):
            valid += 1
    ratio = valid / max(1, len(entries))
    score = round(ratio * 10)
    suggestions: list[str] = []
    if ratio < 1:
        suggestions.append("Format every start/end date as YYYY-MM.")
    return score, suggestions


def _score_bullets(data: dict[str, Any]) -> tuple[int, list[str]]:
    exp = data.get("experience") or []
    if not exp:
        return 0, []
    well_filled = sum(1 for e in exp if len(e.get("highlights") or []) >= 2)
    ratio = well_filled / max(1, len(exp))
    score = round(ratio * 15)
    suggestions: list[str] = []
    if ratio < 1:
        suggestions.append("Aim for 2–4 bullet points per work experience entry.")
    return score, suggestions


def _score_action_verbs(data: dict[str, Any]) -> tuple[int, list[str]]:
    bullets: list[str] = []
    for entry in (data.get("experience") or []) + (data.get("projects") or []):
        bullets.extend(entry.get("highlights") or [])
    if not bullets:
        return 0, []
    leads = [_first_word(b) for b in bullets if b.strip()]
    matched = sum(1 for w in leads if w.lower() in ACTION_VERBS)
    ratio = matched / max(1, len(leads))
    score = round(ratio * 15)
    suggestions: list[str] = []
    if ratio < 0.6:
        suggestions.append(
            "Lead more bullets with strong action verbs (e.g. led, built, shipped, reduced)."
        )
    return score, suggestions


# ----- helpers -----------------------------------------------------------


def _resume_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    p = data.get("personalInfo") or {}
    parts.extend(filter(None, [p.get("summary"), p.get("title")]))
    for e in data.get("experience") or []:
        parts.extend(filter(None, [e.get("position"), e.get("company"), e.get("description")]))
        parts.extend(e.get("highlights") or [])
    for ed in data.get("education") or []:
        parts.extend(filter(None, [ed.get("institution"), ed.get("degree"), ed.get("field"), ed.get("description")]))
    for sk in data.get("skills") or []:
        parts.append(sk.get("category") or "")
        parts.extend(sk.get("items") or [])
    for pr in data.get("projects") or []:
        parts.extend(filter(None, [pr.get("name"), pr.get("description")]))
        parts.extend(pr.get("technologies") or [])
        parts.extend(pr.get("highlights") or [])
    return "\n".join(s for s in parts if isinstance(s, str))


_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "for", "to", "of", "in", "on", "at",
    "by", "with", "from", "into", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "doing",
    "you", "your", "we", "our", "they", "their", "this", "that", "these",
    "those", "it", "its", "if", "then", "than", "so", "such", "via",
    "will", "would", "should", "could", "can", "may", "might", "must",
    "about", "across", "against", "around", "between", "during", "out",
    "over", "through", "while", "all", "any", "more", "most", "other",
    "some", "no", "not", "only", "own", "same", "very", "just", "up", "down",
    "off", "also", "like", "well", "us", "you'll", "we'll", "etc",
}


def _extract_keywords(text: str) -> list[str]:
    """Pull candidate keywords out of a JD. Heuristic: nouns-ish single
    words and short bigrams that appear at least twice or look like
    technical tokens (camelCase, ALL-CAPS, has digits)."""
    text = text.lower()
    words = re.findall(r"[a-zA-Z0-9+#./-]{2,}", text)
    counts: dict[str, int] = {}
    for w in words:
        if w in _STOPWORDS:
            continue
        if len(w) < 3 and not any(c.isdigit() for c in w):
            continue
        counts[w] = counts.get(w, 0) + 1
    # Also add compound terms like "react native" if both words are nearby.
    compound: dict[str, int] = {}
    for i in range(len(words) - 1):
        a, b = words[i], words[i + 1]
        if a in _STOPWORDS or b in _STOPWORDS:
            continue
        if len(a) < 3 or len(b) < 3:
            continue
        token = f"{a} {b}"
        compound[token] = compound.get(token, 0) + 1
    keep = [w for w, n in counts.items() if n >= 2]
    keep.extend([w for w, n in compound.items() if n >= 2])
    # De-dup, preserve order, cap.
    seen: set[str] = set()
    out: list[str] = []
    for w in keep:
        if w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out[:40]


def _first_word(s: str) -> str:
    s = s.strip()
    if not s:
        return ""
    # Strip leading bullet glyphs / punctuation.
    s = re.sub(r"^[\W_]+", "", s)
    return (s.split() or [""])[0]
