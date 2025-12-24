"""
Session Service for handling user sessions and saved books
"""

from sqlalchemy.orm import Session
from typing import Set
import json
import logging

logger = logging.getLogger(__name__)

class SessionService:
    """Service for managing user sessions and saved books"""
    
    # In-memory storage for saved books (in production, use Redis or database)
    _saved_books = {}
    
    @classmethod
    def get_saved_books(cls, db: Session, session_id: str) -> Set[int]:
        """Get saved book IDs for a session"""
        if session_id not in cls._saved_books:
            cls._saved_books[session_id] = set()
        return cls._saved_books[session_id]
    
    @classmethod
    def toggle_saved_book(cls, db: Session, session_id: str, book_id: int) -> bool:
        """Toggle book saved status. Returns True if saved, False if unsaved"""
        if session_id not in cls._saved_books:
            cls._saved_books[session_id] = set()
        
        saved_set = cls._saved_books[session_id]
        
        if book_id in saved_set:
            saved_set.remove(book_id)
            logger.info(f"Book {book_id} removed from session {session_id}")
            return False
        else:
            saved_set.add(book_id)
            logger.info(f"Book {book_id} saved to session {session_id}")
            return True
    
    @classmethod
    def is_book_saved(cls, db: Session, session_id: str, book_id: int) -> bool:
        """Check if a book is saved"""
        saved_books = cls.get_saved_books(db, session_id)
        return book_id in saved_books
    
    @classmethod
    def clear_saved_books(cls, db: Session, session_id: str):
        """Clear all saved books for a session"""
        if session_id in cls._saved_books:
            cls._saved_books[session_id].clear()
