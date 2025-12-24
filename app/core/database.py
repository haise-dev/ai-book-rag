from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Tạo kết nối Database
engine = create_engine(settings.DATABASE_URL)

# Tạo SessionLocal class để quản lý các phiên làm việc với DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho các Models kế thừa
Base = declarative_base()

# Dependency để lấy DB session (Dùng trong FastAPI Router)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
