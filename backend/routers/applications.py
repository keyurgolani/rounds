import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Application, InterviewRound
from schemas import (
    ApplicationCreate, ApplicationResponse,
    InterviewRoundCreate, InterviewRoundResponse,
)

router = APIRouter(prefix="/api", tags=["applications"])


def slugify(text: str) -> str:
    if not text:
        return ""
    s = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def _app_slug(app: Application) -> str:
    return slugify(f"{app.company} {app.role}")


def _resolve_app(ref: str, db: Session):
    try:
        aid = int(ref)
        return db.query(Application).filter(Application.id == aid).first()
    except ValueError:
        pass
    slug = slugify(ref)
    for a in db.query(Application).all():
        if _app_slug(a) == slug:
            return a
    return None


# --- Applications ---
@router.get("/applications", response_model=List[ApplicationResponse])
def list_applications(db: Session = Depends(get_db)):
    return db.query(Application).order_by(Application.id.desc()).all()


@router.get("/applications/{ref}", response_model=ApplicationResponse)
def get_application(ref: str, db: Session = Depends(get_db)):
    a = _resolve_app(ref, db)
    if not a:
        raise HTTPException(404, "Application not found")
    return a


@router.post("/applications", response_model=ApplicationResponse, status_code=201)
def create_application(data: ApplicationCreate, db: Session = Depends(get_db)):
    a = Application(**data.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.put("/applications/{ref}", response_model=ApplicationResponse)
def update_application(ref: str, data: ApplicationCreate, db: Session = Depends(get_db)):
    a = _resolve_app(ref, db)
    if not a:
        raise HTTPException(404, "Application not found")
    for k, v in data.model_dump().items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/applications/{ref}", status_code=204)
def delete_application(ref: str, db: Session = Depends(get_db)):
    a = _resolve_app(ref, db)
    if not a:
        raise HTTPException(404, "Application not found")
    db.delete(a)
    db.commit()


# --- Interview Rounds ---
@router.get("/applications/{ref}/rounds", response_model=List[InterviewRoundResponse])
def list_rounds(ref: str, db: Session = Depends(get_db)):
    a = _resolve_app(ref, db)
    if not a:
        raise HTTPException(404, "Application not found")
    return db.query(InterviewRound).filter(InterviewRound.application_id == a.id).order_by(InterviewRound.id).all()


@router.post("/applications/{ref}/rounds", response_model=InterviewRoundResponse, status_code=201)
def create_round(ref: str, data: InterviewRoundCreate, db: Session = Depends(get_db)):
    app = _resolve_app(ref, db)
    if not app:
        raise HTTPException(404, "Application not found")
    r = InterviewRound(**data.model_dump(), application_id=app.id)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/rounds/{rid}", response_model=InterviewRoundResponse)
def update_round(rid: int, data: InterviewRoundCreate, db: Session = Depends(get_db)):
    r = db.query(InterviewRound).filter(InterviewRound.id == rid).first()
    if not r:
        raise HTTPException(404, "Round not found")
    for k, v in data.model_dump().items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/rounds/{rid}", status_code=204)
def delete_round(rid: int, db: Session = Depends(get_db)):
    r = db.query(InterviewRound).filter(InterviewRound.id == rid).first()
    if not r:
        raise HTTPException(404, "Round not found")
    db.delete(r)
    db.commit()


# --- Stats ---
@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    apps = db.query(Application).all()
    return {
        "total_applications": len(apps),
        "by_status": {s: len([a for a in apps if a.status == s]) for s in set(a.status for a in apps)},
    }
