"""
API Routes for Book Web App
Handles AJAX requests from frontend
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models.database import get_db
from app.services.book_service import BookService, SessionService
from app.routers.pages import get_session_id

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["API"])

@router.post("/save-book/{book_id}")
async def toggle_save_book(
    book_id: int,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db)
):
    """Toggle save/unsave book for current session"""
    try:
        # Check if book exists
        book = BookService.get_book_by_id(db, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Toggle saved status
        is_saved = SessionService.toggle_saved_book(db, session_id, book_id)
        
        return {
            "success": True,
            "saved": is_saved,
            "book_id": book_id,
            "message": f"Book {'saved to' if is_saved else 'removed from'} your list"
        }
        
    except Exception as e:
        logger.error(f"Error toggling save book: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-saved/{book_id}")
async def check_if_saved(
    book_id: int,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db)
):
    """Check if a book is saved by current session"""
    try:
        saved_books = SessionService.get_saved_books(db, session_id)
        is_saved = book_id in saved_books
        
        return {
            "book_id": book_id,
            "is_saved": is_saved
        }
        
    except Exception as e:
        logger.error(f"Error checking saved status: {e}")
        return {"book_id": book_id, "is_saved": False}

@router.get("/saved-books")
async def get_all_saved_books(
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db)
):
    """Get all saved book IDs for current session"""
    try:
        saved_ids = SessionService.get_saved_books(db, session_id)
        return {
            "saved_books": list(saved_ids),
            "count": len(saved_ids)
        }
    except Exception as e:
        logger.error(f"Error getting saved books: {e}")
        return {"saved_books": [], "count": 0}
