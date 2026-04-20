import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import (
    SystemDesignQuestion, CodingQuestion,
    BehavioralQuestion, BehavioralCategory,
    Anecdote, UserProgress,
)
from schemas import (
    SystemDesignQuestionCreate, SystemDesignQuestionResponse,
    CodingQuestionCreate, CodingQuestionResponse,
    BehavioralQuestionCreate, BehavioralQuestionResponse,
    BehavioralCategoryCreate, BehavioralCategoryResponse,
    AnecdoteCreate, AnecdoteResponse,
    UserProgressCreate, UserProgressResponse,
    CodeExecutionRequest, CodeExecutionResult,
    CodeRunRequest, CodeRunResult,
    CodeEvaluateRequest, CodeEvaluateResult, EvaluateCaseResult,
)
from runner import run_one

router = APIRouter(prefix="/api", tags=["questions"])


def slugify(text: str) -> str:
    if not text:
        return ""
    s = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


# --- Resolve helpers ---

def _resolve_sd(ref: str, db: Session):
    try:
        qid = int(ref)
        return db.query(SystemDesignQuestion).filter(SystemDesignQuestion.id == qid).first()
    except ValueError:
        pass
    slug = slugify(ref)
    for q in db.query(SystemDesignQuestion).all():
        if slugify(q.title) == slug:
            return q
    return None


def _resolve_coding(ref: str, db: Session):
    try:
        qid = int(ref)
        return db.query(CodingQuestion).filter(CodingQuestion.id == qid).first()
    except ValueError:
        pass
    slug = slugify(ref)
    for q in db.query(CodingQuestion).all():
        if slugify(q.title) == slug:
            return q
    return None


def _resolve_behavioral(ref: str, db: Session):
    try:
        qid = int(ref)
        return db.query(BehavioralQuestion).filter(BehavioralQuestion.id == qid).first()
    except ValueError:
        pass
    slug = slugify(ref)
    for q in db.query(BehavioralQuestion).all():
        if slugify(q.title) == slug:
            return q
    return None


def _resolve_anecdote(ref: str, db: Session):
    try:
        aid = int(ref)
        return db.query(Anecdote).filter(Anecdote.id == aid).first()
    except ValueError:
        pass
    slug = slugify(ref)
    for a in db.query(Anecdote).all():
        if slugify(a.title) == slug:
            return a
    return None


# --- System Design ---
@router.get("/system-design", response_model=List[SystemDesignQuestionResponse])
def list_system_design(db: Session = Depends(get_db)):
    return db.query(SystemDesignQuestion).order_by(SystemDesignQuestion.id).all()


@router.get("/system-design/{ref}", response_model=SystemDesignQuestionResponse)
def get_system_design(ref: str, db: Session = Depends(get_db)):
    q = _resolve_sd(ref, db)
    if not q:
        raise HTTPException(404, "Question not found")
    return q


@router.post("/system-design", response_model=SystemDesignQuestionResponse, status_code=201)
def create_system_design(data: SystemDesignQuestionCreate, db: Session = Depends(get_db)):
    q = SystemDesignQuestion(**data.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.put("/system-design/{ref}", response_model=SystemDesignQuestionResponse)
def update_system_design(ref: str, data: SystemDesignQuestionCreate, db: Session = Depends(get_db)):
    q = _resolve_sd(ref, db)
    if not q:
        raise HTTPException(404, "Question not found")
    for k, v in data.model_dump().items():
        setattr(q, k, v)
    db.commit()
    db.refresh(q)
    return q


@router.delete("/system-design/{ref}", status_code=204)
def delete_system_design(ref: str, db: Session = Depends(get_db)):
    q = _resolve_sd(ref, db)
    if not q:
        raise HTTPException(404, "Question not found")
    db.delete(q)
    db.commit()


# --- Coding ---
@router.get("/coding", response_model=List[CodingQuestionResponse])
def list_coding(db: Session = Depends(get_db)):
    return db.query(CodingQuestion).order_by(CodingQuestion.id).all()


@router.get("/coding/{ref}", response_model=CodingQuestionResponse)
def get_coding(ref: str, db: Session = Depends(get_db)):
    q = _resolve_coding(ref, db)
    if not q:
        raise HTTPException(404, "Question not found")
    return q


@router.post("/coding", response_model=CodingQuestionResponse, status_code=201)
def create_coding(data: CodingQuestionCreate, db: Session = Depends(get_db)):
    q = CodingQuestion(**data.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.put("/coding/{ref}", response_model=CodingQuestionResponse)
def update_coding(ref: str, data: CodingQuestionCreate, db: Session = Depends(get_db)):
    q = _resolve_coding(ref, db)
    if not q:
        raise HTTPException(404, "Question not found")
    for k, v in data.model_dump().items():
        setattr(q, k, v)
    db.commit()
    db.refresh(q)
    return q


@router.delete("/coding/{ref}", status_code=204)
def delete_coding(ref: str, db: Session = Depends(get_db)):
    q = _resolve_coding(ref, db)
    if not q:
        raise HTTPException(404, "Question not found")
    db.delete(q)
    db.commit()


# --- Code Run (custom input, console capture) ---
LARGE_TAG_TIMEOUT_S = 10
DEFAULT_TIMEOUT_S = 3


@router.post("/run", response_model=CodeRunResult)
def run_code(req: CodeRunRequest):
    outcome = run_one(
        req.code,
        req.language,
        req.function_name,
        req.input,
        timeout_s=DEFAULT_TIMEOUT_S,
    )
    return CodeRunResult(
        stdout=outcome.stdout,
        stderr=outcome.stderr,
        return_value=outcome.return_value,
        error=outcome.error,
        duration_ms=outcome.duration_ms,
        truncated=outcome.truncated,
    )


# --- Code Evaluate (test_cases with optional tag/index filter) ---
def _select_cases(test_cases, flt):
    """Return (selected_index, test_case) tuples respecting the filter."""
    selected = []
    for i, tc in enumerate(test_cases):
        if flt and flt.indices is not None and i not in flt.indices:
            continue
        if flt and flt.tags is not None:
            case_tags = set(tc.get("tags") or [])
            if not case_tags & set(flt.tags):
                continue
        selected.append((i, tc))
    return selected


def _timeout_for(tc) -> int:
    tags = tc.get("tags") or []
    return LARGE_TAG_TIMEOUT_S if "large" in tags else DEFAULT_TIMEOUT_S


@router.post("/evaluate", response_model=CodeEvaluateResult)
def evaluate_code(req: CodeEvaluateRequest):
    selected = _select_cases(req.test_cases, req.filter)
    results = []
    passed = 0
    failed = 0
    for i, tc in selected:
        outcome = run_one(
            req.code,
            req.language,
            req.function_name,
            tc.get("input", {}),
            timeout_s=_timeout_for(tc),
        )
        expected = tc.get("expected")
        case_passed = outcome.error is None and outcome.return_value == expected
        results.append(EvaluateCaseResult(
            index=i,
            passed=case_passed,
            description=tc.get("description") or "",
            tags=list(tc.get("tags") or []),
            output=outcome.return_value,
            expected=expected,
            error=outcome.error,
            duration_ms=outcome.duration_ms,
        ))
        if case_passed:
            passed += 1
        else:
            failed += 1
    return CodeEvaluateResult(passed=passed, failed=failed, results=results)


# --- Legacy alias (deprecated) ---
@router.post("/execute", response_model=CodeExecutionResult)
def execute_code(req: CodeExecutionRequest):
    """Deprecated: forwards to /api/evaluate with no filter."""
    evaluate_req = CodeEvaluateRequest(
        code=req.code,
        language=req.language,
        function_name=req.function_name,
        test_cases=req.test_cases,
        filter=None,
    )
    full = evaluate_code(evaluate_req)
    return CodeExecutionResult(
        passed=full.passed,
        failed=full.failed,
        results=[
            {
                "passed": r.passed,
                "output": r.output,
                "expected": r.expected,
                "error": r.error,
                "description": r.description,
            }
            for r in full.results
        ],
    )


# --- Behavioral Categories ---
@router.get("/behavioral-categories", response_model=List[BehavioralCategoryResponse])
def list_behavioral_categories(db: Session = Depends(get_db)):
    return db.query(BehavioralCategory).order_by(BehavioralCategory.name).all()


@router.post("/behavioral-categories", response_model=BehavioralCategoryResponse, status_code=201)
def create_behavioral_category(data: BehavioralCategoryCreate, db: Session = Depends(get_db)):
    c = BehavioralCategory(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# --- Behavioral Questions ---
@router.get("/behavioral", response_model=List[BehavioralQuestionResponse])
def list_behavioral(db: Session = Depends(get_db)):
    return db.query(BehavioralQuestion).order_by(BehavioralQuestion.id).all()


@router.get("/behavioral/{ref}", response_model=BehavioralQuestionResponse)
def get_behavioral(ref: str, db: Session = Depends(get_db)):
    q = _resolve_behavioral(ref, db)
    if not q:
        raise HTTPException(404, "Question not found")
    return q


@router.post("/behavioral", response_model=BehavioralQuestionResponse, status_code=201)
def create_behavioral(data: BehavioralQuestionCreate, db: Session = Depends(get_db)):
    q = BehavioralQuestion(**data.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.put("/behavioral/{ref}", response_model=BehavioralQuestionResponse)
def update_behavioral(ref: str, data: BehavioralQuestionCreate, db: Session = Depends(get_db)):
    q = _resolve_behavioral(ref, db)
    if not q:
        raise HTTPException(404, "Question not found")
    for k, v in data.model_dump().items():
        setattr(q, k, v)
    db.commit()
    db.refresh(q)
    return q


@router.delete("/behavioral/{ref}", status_code=204)
def delete_behavioral(ref: str, db: Session = Depends(get_db)):
    q = _resolve_behavioral(ref, db)
    if not q:
        raise HTTPException(404, "Question not found")
    db.delete(q)
    db.commit()


# --- Anecdotes ---
@router.get("/anecdotes", response_model=List[AnecdoteResponse])
def list_anecdotes(db: Session = Depends(get_db)):
    return db.query(Anecdote).order_by(Anecdote.id).all()


@router.get("/anecdotes/{ref}", response_model=AnecdoteResponse)
def get_anecdote(ref: str, db: Session = Depends(get_db)):
    a = _resolve_anecdote(ref, db)
    if not a:
        raise HTTPException(404, "Anecdote not found")
    return a


@router.post("/anecdotes", response_model=AnecdoteResponse, status_code=201)
def create_anecdote(data: AnecdoteCreate, db: Session = Depends(get_db)):
    a = Anecdote(**data.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.put("/anecdotes/{ref}", response_model=AnecdoteResponse)
def update_anecdote(ref: str, data: AnecdoteCreate, db: Session = Depends(get_db)):
    a = _resolve_anecdote(ref, db)
    if not a:
        raise HTTPException(404, "Anecdote not found")
    for k, v in data.model_dump().items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/anecdotes/{ref}", status_code=204)
def delete_anecdote(ref: str, db: Session = Depends(get_db)):
    a = _resolve_anecdote(ref, db)
    if not a:
        raise HTTPException(404, "Anecdote not found")
    db.delete(a)
    db.commit()


# --- User Progress ---
@router.get("/progress", response_model=List[UserProgressResponse])
def list_progress(question_type: str = None, db: Session = Depends(get_db)):
    q = db.query(UserProgress)
    if question_type:
        q = q.filter(UserProgress.question_type == question_type)
    return q.all()


@router.get("/progress/{question_type}/{question_id}", response_model=UserProgressResponse)
def get_progress(question_type: str, question_id: int, db: Session = Depends(get_db)):
    p = db.query(UserProgress).filter(
        UserProgress.question_type == question_type,
        UserProgress.question_id == question_id,
    ).first()
    if not p:
        return UserProgressResponse(
            id=0, question_type=question_type, question_id=question_id,
            status="Not Started", notes="", confidence=0.0,
        )
    return p


@router.post("/progress", response_model=UserProgressResponse, status_code=201)
def create_progress(data: UserProgressCreate, db: Session = Depends(get_db)):
    existing = db.query(UserProgress).filter(
        UserProgress.question_type == data.question_type,
        UserProgress.question_id == data.question_id,
    ).first()
    if existing:
        for k, v in data.model_dump().items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    p = UserProgress(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p
