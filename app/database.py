from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
from sqlalchemy.exc import ProgrammingError

from sqlalchemy.pool import NullPool

SQLALCHEMY_DATABASE_URL = settings.SQL_DATABASE_URL

if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}, 
        poolclass=NullPool
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Auto-create DB if not exists (MS SQL specific hack for demo)
    # Ideally checking 'master' db then creating 'TechDemoDB'
    # For now, we assume the DB is created or we rely on the connection string to create it if we use a different driver.
    # Actually, pyodbc won't create the DB. We might need a pre-start script.
    # Let's rely on SQLAlchemy to create *tables*.
    Base.metadata.create_all(bind=engine)
