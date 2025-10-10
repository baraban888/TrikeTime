# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_PATH = "database.db"

# движок SQLite (при желании потом заменим на Postgres)
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

# фабрика сессий
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def create_tables() -> None:
    """Создаёт все таблицы из models.py, если их ещё нет."""
    # импорт внутри функции, чтобы избежать циклических импортов
    from models import Base
    Base.metadata.create_all(bind=engine)

