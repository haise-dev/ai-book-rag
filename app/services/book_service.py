"""
Book service for database operations
"""

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
import json
import logging

from app.models.database import Book, Genre, UserSession, get_db

logger = logging.getLogger(__name__)

class BookService:
    """Service class for book-related operations"""
    
    @staticmethod
    def get_all_books(db: Session, skip: int = 0, limit: int = 100) -> List[Book]:
        """Get all books with pagination"""
        return db.query(Book).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_featured_books(db: Session, limit: int = 4) -> List[Book]:
        """Get featured books (highest rated)"""
        return db.query(Book).order_by(desc(Book.rating)).limit(limit).all()
    
    @staticmethod
    def get_recent_books(db: Session, limit: int = 4) -> List[Book]:
        """Get recently added books"""
        return db.query(Book).order_by(desc(Book.created_at)).limit(limit).all()
    
    @staticmethod
    def get_book_by_id(db: Session, book_id: int) -> Optional[Book]:
        """Get book by ID"""
        return db.query(Book).filter(Book.id == book_id).first()
    
    @staticmethod
    def search_books(db: Session, query: str) -> List[Book]:
        """Search books by title, author, or description"""
        search_term = f"%{query}%"
        return db.query(Book).filter(
            or_(
                Book.title.ilike(search_term),
                Book.author.ilike(search_term),
                Book.description.ilike(search_term)
            )
        ).all()
    
    @staticmethod
    def create_book(db: Session, book_data: dict) -> Book:
        """Create a new book"""
        # Extract genres
        genre_ids = book_data.pop('genres', [])
        
        # Create book
        book = Book(**book_data)
        
        # Add genres
        if genre_ids:
            genres = db.query(Genre).filter(Genre.id.in_(genre_ids)).all()
            book.genres = genres
        
        db.add(book)
        db.commit()
        db.refresh(book)
        
        logger.info(f"Created book: {book.title} (ID: {book.id})")
        return book
    
    @staticmethod
    def update_book(db: Session, book_id: int, book_data: dict) -> Optional[Book]:
        """Update existing book"""
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None
        
        # Update genres if provided
        if 'genres' in book_data:
            genre_ids = book_data.pop('genres')
            genres = db.query(Genre).filter(Genre.id.in_(genre_ids)).all()
            book.genres = genres
        
        # Update other fields
        for key, value in book_data.items():
            setattr(book, key, value)
        
        db.commit()
        db.refresh(book)
        return book
    
    @staticmethod
    def delete_book(db: Session, book_id: int) -> bool:
        """Delete a book"""
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return False
        
        db.delete(book)
        db.commit()
        return True
    
    @staticmethod
    def get_all_genres(db: Session) -> List[Genre]:
        """Get all available genres"""
        return db.query(Genre).order_by(Genre.name).all()
    
    @staticmethod
    def get_books_by_genre(db: Session, genre_id: int) -> List[Book]:
        """Get books by genre"""
        genre = db.query(Genre).filter(Genre.id == genre_id).first()
        if genre:
            return genre.books
        return []


class SessionService:
    """Service for managing user sessions"""
    
    @staticmethod
    def get_or_create_session(db: Session, session_id: str) -> UserSession:
        """Get existing session or create new one"""
        session = db.query(UserSession).filter(
            UserSession.session_id == session_id
        ).first()
        
        if not session:
            session = UserSession(
                session_id=session_id,
                preferences=json.dumps({}),  # Convert dict to JSON string
                reading_history=json.dumps([])  # Convert list to JSON string
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        
        return session
    
    @staticmethod
    def get_saved_books(db: Session, session_id: str) -> List[int]:
        """Get saved book IDs for a session"""
        session = db.query(UserSession).filter(
            UserSession.session_id == session_id
        ).first()
        
        if session and session.preferences:
            prefs = json.loads(session.preferences) if isinstance(session.preferences, str) else session.preferences
            return prefs.get('saved_books', [])
        return []
    
    @staticmethod
    def toggle_saved_book(db: Session, session_id: str, book_id: int) -> bool:
        """Toggle book saved status"""
        session = SessionService.get_or_create_session(db, session_id)
        
        # Parse preferences
        if session.preferences:
            prefs = json.loads(session.preferences) if isinstance(session.preferences, str) else session.preferences
        else:
            prefs = {}
        
        saved_books = prefs.get('saved_books', [])
        
        # Toggle
        if book_id in saved_books:
            saved_books.remove(book_id)
            is_saved = False
        else:
            saved_books.append(book_id)
            is_saved = True
        
        # Update preferences
        prefs['saved_books'] = saved_books
        session.preferences = json.dumps(prefs)  # Convert back to JSON string
        
        db.commit()
        return is_saved
# Export SessionService
# from .session import SessionService
# __all__ = ['BookService', 'SessionService']
