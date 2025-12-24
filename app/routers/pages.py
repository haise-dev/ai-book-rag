from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.models.database import get_db
from app.services.book_service import BookService
from app.config import templates

logger = logging.getLogger(__name__)

# QUAN TRỌNG: Định nghĩa router
router = APIRouter()

@router.get("/genres", response_class=HTMLResponse)
async def genres_page(
    request: Request,
    selected: Optional[str] = None,  # comma-separated genre IDs
    db: Session = Depends(get_db)
):
    """Browse books by genres with multi-select"""
    try:
        all_genres = BookService.get_all_genres(db)
        selected_genres = []
        books = []
        
        if selected:
            # Parse selected genre IDs
            selected_ids = [int(id) for id in selected.split(',') if id.isdigit()]
            selected_genres = [g for g in all_genres if g.id in selected_ids]
            
            # Get books that have ALL selected genres
            all_books = BookService.get_all_books(db)
            books = []
            for book in all_books:
                book_genre_ids = [g.id for g in book.genres]
                if all(gid in book_genre_ids for gid in selected_ids):
                    books.append(book)
        
        context = {
            "request": request,
            "title": "Browse by Genres",
            "all_genres": all_genres,
            "selected_genres": selected_genres,
            "books": books,
            "selected_ids": [g.id for g in selected_genres]
        }
        return templates.TemplateResponse("genres.html", context)
    except Exception as e:
        logger.error(f"Error in genres page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/genres", response_class=HTMLResponse)
async def genres_page(
    request: Request,
    selected: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Browse books by genres with multi-select"""
    try:
        all_genres = BookService.get_all_genres(db)
        selected_genres = []
        books = []
        
        if selected:
            # Parse selected genre IDs
            selected_ids = [int(id) for id in selected.split(',') if id.isdigit()]
            selected_genres = [g for g in all_genres if g.id in selected_ids]
            
            # Get books that have ALL selected genres
            all_books = BookService.get_all_books(db)
            books = []
            for book in all_books:
                book_genre_ids = [g.id for g in book.genres]
                if all(gid in book_genre_ids for gid in selected_ids):
                    books.append(book)
        
        context = {
            "request": request,
            "title": "Browse by Genres",
            "all_genres": all_genres,
            "selected_genres": selected_genres,
            "books": books,
            "selected_ids": [g.id for g in selected_genres]
        }
        return templates.TemplateResponse("genres.html", context)
    except Exception as e:
        logger.error(f"Error in genres page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
