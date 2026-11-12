import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/problems", tags=["problems"])


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


@router.post("", response_model=schemas.ProblemDetail, status_code=201)
def create_problem(
    data: schemas.ProblemCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    slug = slugify(data.title)
    exists = db.scalar(
        select(models.Problem).where(
            (models.Problem.slug == slug) | (models.Problem.title == data.title)
        )
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Problem already exists")
    problem = models.Problem(
        title=data.title,
        slug=slug,
        description=data.description,
        difficulty=data.difficulty,
        time_limit_ms=data.time_limit_ms,
        memory_limit_mb=data.memory_limit_mb,
        test_cases=[models.TestCase(**tc.model_dump()) for tc in data.test_cases],
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return _to_detail(problem)


@router.get("", response_model=list[schemas.ProblemListItem])
def list_problems(
    difficulty: models.Difficulty | None = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    stmt = select(models.Problem).order_by(models.Problem.id).offset(skip).limit(min(limit, 100))
    if difficulty:
        stmt = stmt.where(models.Problem.difficulty == difficulty)
    return db.scalars(stmt).all()


@router.get("/{slug}", response_model=schemas.ProblemDetail)
def get_problem(slug: str, db: Session = Depends(get_db)):
    problem = db.scalar(select(models.Problem).where(models.Problem.slug == slug))
    if not problem:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")
    return _to_detail(problem)


def _to_detail(problem: models.Problem) -> schemas.ProblemDetail:
    # Only sample test cases are shown to users; hidden ones stay on the server.
    detail = schemas.ProblemDetail.model_validate(problem)
    detail.samples = [
        schemas.SampleOut.model_validate(tc) for tc in problem.test_cases if tc.is_sample
    ]
    return detail
