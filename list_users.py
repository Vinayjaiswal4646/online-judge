from app.database import SessionLocal
from app.models import User

db = SessionLocal()
for u in db.query(User).all():
    print(u.id, u.username, u.is_admin)