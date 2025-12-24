"""
AI Integration Routes for Book Recommendation System
Provides endpoints for AI Assistant to interact with the system
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import logging

from app.models.database import get_db
from app.services.book_service import BookService, SessionService
from app.models.schemas import BookResponse, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Integration"])

@router.get("/search", response_model=SearchResponse)
async def ai_search_books(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    AI endpoint to search books
    Used by AI assistant to find books based on user queries
    """
    try:
        books = BookService.search_books(db, q)[:limit]
        
        return {
            "query": q,
            "count": len(books),
            "books": books
        }
    except Exception as e:
        logger.error(f"AI search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommend")
async def ai_get_recommendations(
    genre: Optional[str] = None,
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """
    AI endpoint to get book recommendations based on criteria
    """
    try:
        if genre:
            # Find genre ID
            all_genres = BookService.get_all_genres(db)
            genre_obj = next((g for g in all_genres if g.name.lower() == genre.lower()), None)
            if genre_obj:
                books = BookService.get_books_by_genre(db, genre_obj.id)
            else:
                books = []
        else:
            # Get top-rated books
            books = BookService.get_featured_books(db, limit=limit*2)
        
        # Filter by rating if specified
        if min_rating:
            books = [b for b in books if b.rating and float(b.rating) >= min_rating]
        
        # Limit results
        books = books[:limit]
        
        return {
            "criteria": {
                "genre": genre,
                "min_rating": min_rating,
                "limit": limit
            },
            "count": len(books),
            "recommendations": [
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "rating": float(book.rating) if book.rating else None,
                    "genres": [g.name for g in book.genres],
                    "description": book.description[:200] if book.description else None
                }
                for book in books
            ]
        }
    except Exception as e:
        logger.error(f"AI recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user-action")
async def ai_user_action(
    action: str,
    book_id: Optional[int] = None,
    session_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    AI endpoint to perform actions on behalf of user
    Actions: save_book, unsave_book, get_saved
    """
    try:
        if action == "save_book" and book_id:
            is_saved = SessionService.toggle_saved_book(db, session_id, book_id)
            book = BookService.get_book_by_id(db, book_id)
            return {
                "success": True,
                "action": "save_book",
                "book_id": book_id,
                "book_title": book.title if book else "Unknown",
                "is_saved": is_saved,
                "message": f"Book {'saved to' if is_saved else 'removed from'} your list"
            }
        
        elif action == "get_saved":
            saved_ids = SessionService.get_saved_books(db, session_id)
            saved_books = []
            for book_id in saved_ids:
                book = BookService.get_book_by_id(db, book_id)
                if book:
                    saved_books.append({
                        "id": book.id,
                        "title": book.title,
                        "author": book.author
                    })
            return {
                "success": True,
                "action": "get_saved",
                "count": len(saved_books),
                "saved_books": saved_books
            }
        
        else:
            return {
                "success": False,
                "message": "Invalid action or missing parameters"
            }
            
    except Exception as e:
        logger.error(f"AI action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/book-details/{book_id}")
async def ai_get_book_details(
    book_id: int,
    db: Session = Depends(get_db)
):
    """
    AI endpoint to get detailed information about a specific book
    """
    try:
        book = BookService.get_book_by_id(db, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "publication_year": book.publication_year,
            "publisher": book.publisher,
            "page_count": book.page_count,
            "language": book.language,
            "rating": float(book.rating) if book.rating else None,
            "total_reviews": book.total_reviews,
            "genres": [g.name for g in book.genres],
            "description": book.description,
            "summary": book.summary,
            "cover_image_url": book.cover_image_url,
            "web_url": f"/book/{book.id}"  # URL to view in web interface
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI book details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/genres")
async def ai_get_genres(db: Session = Depends(get_db)):
    """
    AI endpoint to get all available genres
    """
    try:
        genres = BookService.get_all_genres(db)
        return {
            "count": len(genres),
            "genres": [g.name for g in genres]  # Fixed: Return list of strings instead of objects
        }
    except Exception as e:
        logger.error(f"AI genres error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
