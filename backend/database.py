import os
from sqlalchemy import create_engine  # pyre-ignore[21]
from sqlalchemy.orm import sessionmaker  # pyre-ignore[21]
from sqlalchemy.orm import declarative_base  # pyre-ignore[21]

# Default to SQLite for local development
# Set DATABASE_URL env var to postgresql://... for production / docker
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./cloud_cost.db"
)

# SQLite requires check_same_thread=False; ignored by PostgreSQL engine
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

