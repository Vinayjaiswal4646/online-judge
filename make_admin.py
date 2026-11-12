from app.database import SessionLocal
from app.models import User

db = SessionLocal()
user = db.query(User).filter_by(username="Vinay").one()
user.is_admin = True
db.commit()
print("Done, you are admin")