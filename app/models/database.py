"""
Database connection and models for Book Recommendation System
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, Table, DECIMAL, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import logging

logger = logging.getLogger(__name__)

# Try different host options
def get_database_url():
    """Get database URL with proper host"""
    # Check if we're running inside Docker
    if os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER'):
        # Try environment variable first
        if os.getenv('POSTGRES_HOST'):
            host = os.getenv('POSTGRES_HOST')
        else:
            # Default Docker network name
            host = 'postgres'
    else:
        # Local development
        host = 'localhost'
    
    user = os.getenv('POSTGRES_USER', 'admin_haise')
    password = os.getenv('POSTGRES_PASSWORD', 'Duonghoang22!')
    db = os.getenv('POSTGRES_DB', 'n8n')
    port = os.getenv('POSTGRES_PORT', '5432')
    
    url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    logger.info(f"Using database host: {host}")
    return url

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL") or get_database_url()

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Association tables
book_genres = Table(
    'book_genres',
    Base.metadata,
    Column('book_id', Integer, ForeignKey('books.id'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.id'), primary_key=True)
)

book_authors = Table(
    'book_authors', 
    Base.metadata,
    Column('book_id', Integer, ForeignKey('books.id'), primary_key=True),
    Column('author_id', Integer, ForeignKey('authors.id'), primary_key=True),
    Column('role', String(50), default='author')
)

# Models
class Book(Base):
    __tablename__ = 'books'
    
    id = Column(Integer, primary_key=True)
    isbn = Column(String(20), unique=True)
    title = Column(String(500), nullable=False)
    author = Column(String(300), nullable=False)
    publication_year = Column(Integer)
    publisher = Column(String(200))
    page_count = Column(Integer)
    language = Column(String(50), default='English')
    description = Column(Text)
    summary = Column(Text)
    cover_image_url = Column(Text)
    pdf_path = Column(String(500))
    rating = Column(DECIMAL(3, 2))
    total_reviews = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    genres = relationship("Genre", secondary=book_genres, back_populates="books")
    chunks = relationship("BookChunk", back_populates="book")

class Genre(Base):
    __tablename__ = 'genres'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    
    # Relationships
    books = relationship("Book", secondary=book_genres, back_populates="genres")

class Author(Base):
    __tablename__ = 'authors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    biography = Column(Text)
    birth_year = Column(Integer)
    nationality = Column(String(100))
    website = Column(String(200))

class UserSession(Base):
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)
    preferences = Column(Text)  # JSON
    reading_history = Column(Text)  # JSON
    created_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, server_default=func.now())

class BookChunk(Base):
    __tablename__ = 'book_chunks'
    
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('books.id'))
    chunk_text = Column(Text, nullable=False)
    chunk_order = Column(Integer)
    chunk_type = Column(String(50))
    embedding_id = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    book = relationship("Book", back_populates="chunks")

# Database helper functions
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database - create tables if not exist"""
    try:
        # This won't drop existing tables, just create if not exist
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# Test connection
def test_connection():
    """Test database connection"""
    try:
        db = SessionLocal()
        # Fix the SQLAlchemy syntax error
        result = db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
