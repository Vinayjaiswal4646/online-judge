# Online Judge

A mini LeetCode: users submit code, it runs in a sandbox, and gets graded against hidden test cases.

**Status:** Week 2 done (submissions + local Python runner). Next: Docker sandbox.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API docs.

To use PostgreSQL instead of SQLite: `docker compose up -d`, then set `DATABASE_URL` in `.env`
(the Postgres line is in `.env.example`).

## Run tests

```bash
pytest
```

## Make yourself admin (needed to create problems)

1. Sign up through `/docs` (POST /auth/signup).
2. Run:

```bash
python -c "
from app.database import SessionLocal
from app.models import User
db = SessionLocal()
u = db.query(User).filter_by(username='YOUR_USERNAME').one()
u.is_admin = True
db.commit()
"
```

## API so far

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /auth/signup | - | Create account |
| POST | /auth/login | - | Get JWT |
| GET | /auth/me | user | Current user |
| POST | /problems | admin | Create problem with test cases |
| GET | /problems | - | List (filter by difficulty, paginate) |
| GET | /problems/{slug} | - | Problem details + sample cases only |
| POST | /submissions | user | Submit Python code, get a verdict |
| GET | /submissions | user | Your submission history |
| GET | /submissions/{id} | user | One of your submissions |

## Roadmap

- [x] Week 1: auth, problems, tests
- [x] Week 2: submissions + subprocess runner
- [ ] Week 3: Docker sandbox, time/memory limits
- [ ] Week 4: Redis queue + workers
- [ ] Week 5: frontend (React + Monaco)
- [ ] Week 6: rate limiting, CI, deploy
