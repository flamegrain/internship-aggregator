import os
from sqlmodel import SQLModel, create_engine, Session

sqlite_file_name = "database.db"
base_dir = os.path.dirname(os.path.abspath(__file__))
sqlite_url = f"sqlite:///{os.path.join(base_dir, sqlite_file_name)}"

echo = os.environ.get("SQL_ECHO", "").lower() in ("true", "1")
engine = create_engine(
    sqlite_url,
    connect_args={"check_same_thread": False},
    echo=echo
)

def create_db_and_tables():
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        print(f"Skipping table creation (read-only environment or existing tables): {e}")

def get_session():
    with Session(engine) as session:
        yield session
