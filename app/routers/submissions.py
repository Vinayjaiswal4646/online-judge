from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..judge import judge_submission

router = APIRouter(prefix="/submissions", tags=["submissions"])

SUPPORTED_LANGUAGES = {"python"}


@router.post("", response_model=schemas.SubmissionOut, status_code=201)
def submit(
    data: schemas.SubmissionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if data.language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only python is supported for now")

    problem = db.scalar(select(models.Problem).where(models.Problem.slug == data.problem_slug))
    if not problem:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")

    submission = models.Submission(
        user_id=user.id, problem_id=problem.id, language=data.language, code=data.code
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Week 2: judged right here, so the request waits for the result.
    # Week 4 moves this into a background worker with a queue.
    judge_submission(db, submission)
    return submission


@router.get("", response_model=list[schemas.SubmissionOut])
def my_submissions(
    problem_slug: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    stmt = (
        select(models.Submission)
        .where(models.Submission.user_id == user.id)
        .order_by(models.Submission.id.desc())
    )
    if problem_slug:
        stmt = stmt.join(models.Problem).where(models.Problem.slug == problem_slug)
    return db.scalars(stmt).all()


@router.get("/{submission_id}", response_model=schemas.SubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    submission = db.get(models.Submission, submission_id)
    # Same 404 for "doesn't exist" and "not yours" so IDs can't be probed.
    if not submission or submission.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    return submission
