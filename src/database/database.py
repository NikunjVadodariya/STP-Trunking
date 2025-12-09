"""
Database Configuration and Session Management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import yaml
from pathlib import Path

# Import Base from models to avoid circular import
from .models import Base

# Default database URL
DATABASE_URL = "sqlite:///./sip_trunking.db"

# Load database URL from config
try:
    config_path = Path("config/server_config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if config and 'database' in config:
                DATABASE_URL = config['database'].get('url', DATABASE_URL)
except Exception:
    pass

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

