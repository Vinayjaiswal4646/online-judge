import enum
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Enum, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Difficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class Verdict(str, enum.Enum):
    pending = "pending"
    running = "running"
    accepted = "accepted"
    wrong_answer = "wrong_answer"
    runtime_error = "runtime_error"
    time_limit_exceeded = "time_limit_exceeded"
    memory_limit_exceeded = "memory_limit_exceeded"
    internal_error = "internal_error"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submissions: Mapped[list["Submission"]] = relationship(back_populates="user")


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), unique=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty), default=Difficulty.easy)
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=256)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(back_populates="problem")


class TestCase(Base):
    __tablename__ = "test_cases"
    __test__ = False  # stop pytest from collecting this class

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    input_data: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)

    problem: Mapped[Problem] = relationship(back_populates="test_cases")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    language: Mapped[str] = mapped_column(String(20), default="python")
    code: Mapped[str] = mapped_column(Text)
    verdict: Mapped[Verdict] = mapped_column(Enum(Verdict), default=Verdict.pending)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="submissions")
    problem: Mapped[Problem] = relationship(back_populates="submissions")
