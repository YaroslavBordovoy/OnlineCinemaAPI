from sqlalchemy.orm import Session
from database.fixtures import load_fixtures
from database.session_sqlite import SqliteSessionLocal

def init_db():
    db: Session = SqliteSessionLocal()
    try:
        load_fixtures(db)
        print("Database seeding completed successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
