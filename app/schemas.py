from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import Difficulty, Verdict


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    is_admin: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TestCaseCreate(BaseModel):
    input_data: str
    expected_output: str
    is_sample: bool = False


class SampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    input_data: str
    expected_output: str


class ProblemCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str
    difficulty: Difficulty = Difficulty.easy
    time_limit_ms: int = Field(default=2000, ge=100, le=10000)
    memory_limit_mb: int = Field(default=256, ge=16, le=1024)
    test_cases: list[TestCaseCreate] = Field(min_length=1)


class ProblemListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    slug: str
    difficulty: Difficulty


class ProblemDetail(ProblemListItem):
    description: str
    time_limit_ms: int
    memory_limit_mb: int
    created_at: datetime
    samples: list[SampleOut] = []


class SubmissionCreate(BaseModel):
    problem_slug: str
    language: str = "python"
    code: str = Field(min_length=1, max_length=50_000)


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    problem_id: int
    language: str
    verdict: Verdict
    runtime_ms: int | None
    created_at: datetime
    code: str
