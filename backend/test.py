from sqlalchemy import text
from app.db.database import engine

with engine.connect() as conn:
    print(conn.execute(text("SELECT current_database()")).scalar())