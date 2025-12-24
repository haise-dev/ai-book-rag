"""
API Routes for Book Web App
Handles AJAX requests from frontend
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
import uuid
import logging

from app.models.database import get_db
from app.services.book_service import BookService, SessionService

logger = logging.getLogger(__name__)

router = APIRouter()

# Local function to avoid circular import
def get_session_id(request: Request) -> str:
    """Get or create session ID from cookies"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

@router.post("/save-book/{book_id}")
async def toggle_save_book(
    book_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Toggle save/unsave book for current session"""
    try:
        session_id = get_session_id(request)
        logger.info(f"Toggle save book {book_id} for session {session_id}")
        
        # Check if book exists
        book = BookService.get_book_by_id(db, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Toggle saved status using database SessionService
        is_saved = SessionService.toggle_saved_book(db, session_id, book_id)
        
        logger.info(f"Book {book_id} saved status: {is_saved}")
        
        # Verify it was saved
        saved_books = SessionService.get_saved_books(db, session_id)
        logger.info(f"Session {session_id} now has saved books: {saved_books}")
        
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
    request: Request,
    db: Session = Depends(get_db)
):
    """Check if a book is saved by current session"""
    try:
        session_id = get_session_id(request)
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
    request: Request,
    db: Session = Depends(get_db)
):
    """Get all saved book IDs for current session"""
    try:
        session_id = get_session_id(request)
        saved_ids = SessionService.get_saved_books(db, session_id)
        logger.info(f"API: Session {session_id} has saved books: {saved_ids}")
        
        return {
            "saved_books": list(saved_ids),
            "count": len(saved_ids)
        }
    except Exception as e:
        logger.error(f"Error getting saved books: {e}")
        return {"saved_books": [], "count": 0}

@router.get("/test")
async def test_api():
    """Test endpoint to verify API router is working"""
    return {"message": "API router is working!", "status": "ok"}