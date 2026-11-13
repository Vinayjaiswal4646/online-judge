import logging

from sqlalchemy.orm import Session

from . import models
from .runner import SandboxError, outputs_match, run_python

log = logging.getLogger("judge")


def judge_submission(db: Session, submission: models.Submission) -> None:
    """Run the submission against every test case and store the verdict."""
    problem = submission.problem
    submission.verdict = models.Verdict.running
    db.commit()

    verdict = models.Verdict.accepted
    slowest = 0

    try:
        for case in problem.test_cases:
            result = run_python(
                submission.code, case.input_data, problem.time_limit_ms, problem.memory_limit_mb
            )
            slowest = max(slowest, result.runtime_ms)

            if result.status == "time_limit_exceeded":
                verdict = models.Verdict.time_limit_exceeded
                break
            if result.status == "memory_limit_exceeded":
                verdict = models.Verdict.memory_limit_exceeded
                break
            if result.status == "runtime_error":
                verdict = models.Verdict.runtime_error
                break
            if not outputs_match(result.stdout, case.expected_output):
                verdict = models.Verdict.wrong_answer
                break
    except SandboxError as exc:
        log.error("Sandbox failure while judging submission %s: %s", submission.id, exc)
        verdict = models.Verdict.internal_error

    submission.verdict = verdict
    submission.runtime_ms = slowest
    db.commit()
    db.refresh(submission)
