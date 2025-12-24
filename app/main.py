"""
AI Book Recommendation System - Main Application
Academic project demonstrating RAG and Vector Search
"""

from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
from pathlib import Path
import uuid
import json

from app.models.database import get_db, init_db, test_connection
from app.services.book_service import BookService, SessionService
from app.routers import ai, chat
from app.routers.api import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Create FastAPI app
app = FastAPI(
    title="AI Book Recommendation System",
    description="Local web platform with AI-powered book recommendations using RAG and Vector Search",
    version="1.0.0"
)

# Mount static files
static_path = BASE_DIR / "app" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    logger.info(f"Static files mounted from: {static_path}")

# Setup templates
template_path = BASE_DIR / "app" / "templates"
templates = Jinja2Templates(directory=str(template_path))
logger.info(f"Templates loaded from: {template_path}")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database connection"""
    logger.info("Starting up Book Recommendation System...")
    if test_connection():
        logger.info("Database connection successful!")
        init_db()
    else:
        logger.error("Failed to connect to database!")

# Dependency to get session ID
def get_session_id(request: Request) -> str:
    """Get or create session ID from cookies"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Created new session ID: {session_id}")
    else:
        logger.info(f"Using existing session ID: {session_id}")
    return session_id

# Homepage
@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id)
):
    """Homepage with book previews"""
    try:
        # Fetch books from database
        featured_books = BookService.get_featured_books(db, limit=4)
        recent_books = BookService.get_recent_books(db, limit=4)
        
        # Get saved books
        saved_book_ids = SessionService.get_saved_books(db, session_id)
        logger.info(f"Homepage - Session {session_id} has {len(saved_book_ids)} saved books: {saved_book_ids}")
        
        saved_books = []
        if saved_book_ids:
            saved_books = [BookService.get_book_by_id(db, book_id) for book_id in saved_book_ids[:4]]
            saved_books = [book for book in saved_books if book]  # Filter None values
        
        context = {
            "request": request,
            "title": "AI Book Library - Home",
            "featured_books": featured_books,
            "recent_books": recent_books,
            "saved_books": saved_books
        }
        
        logger.info(f"Rendering home.html with {len(featured_books)} featured, {len(recent_books)} recent, {len(saved_books)} saved books")
        response = templates.TemplateResponse("home.html", context)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response
        
    except Exception as e:
        logger.error(f"Error in home page: {str(e)}")
        return HTMLResponse(content=f"Error: {str(e)}", status_code=500)

# All books page
@app.get("/books", response_class=HTMLResponse)
async def books_page(
    request: Request,
    db: Session = Depends(get_db),
    search: Optional[str] = None
):
    """Display all books in the catalog"""
    try:
        if search:
            books = BookService.search_books(db, search)
        else:
            books = BookService.get_all_books(db)
        
        context = {
            "request": request,
            "title": "All Books",
            "books": books,
            "search_query": search or ""
        }
        return templates.TemplateResponse("books.html", context)
    except Exception as e:
        logger.error(f"Error in books page: {str(e)}")
        return HTMLResponse(content=f"Error: {str(e)}", status_code=500)

# Book detail page
@app.get("/book/{book_id}", response_class=HTMLResponse)
async def book_detail(
    request: Request,
    book_id: int,
    db: Session = Depends(get_db)
):
    """Display individual book details"""
    try:
        book = BookService.get_book_by_id(db, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        context = {
            "request": request,
            "title": f"{book.title} - Book Details",
            "book": book
        }
        return templates.TemplateResponse("book_detail.html", context)
    except Exception as e:
        logger.error(f"Error in book detail page: {str(e)}")
        return HTMLResponse(content=f"Error: {str(e)}", status_code=500)

# Saved books page
@app.get("/saved", response_class=HTMLResponse)
async def saved_books(
    request: Request,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id)
):
    """Display user's saved books"""
    try:
        saved_book_ids = SessionService.get_saved_books(db, session_id)
        logger.info(f"Saved page - Session {session_id} has {len(saved_book_ids)} saved books: {saved_book_ids}")
        
        saved_books = []
        if saved_book_ids:
            saved_books = [BookService.get_book_by_id(db, book_id) for book_id in saved_book_ids]
            saved_books = [book for book in saved_books if book]
            logger.info(f"Retrieved {len(saved_books)} book objects from database")
        
        context = {
            "request": request,
            "title": "My Saved Books",
            "saved_books": saved_books
        }
        
        response = templates.TemplateResponse("saved.html", context)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response
    except Exception as e:
        logger.error(f"Error in saved books page: {str(e)}")
        return HTMLResponse(content=f"Error: {str(e)}", status_code=500)

# Add book page
@app.get("/add-book", response_class=HTMLResponse)
async def add_book_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Form to add new books"""
    try:
        genres = BookService.get_all_genres(db)
        context = {
            "request": request,
            "title": "Add New Book",
            "genres": genres
        }
        return templates.TemplateResponse("add_book.html", context)
    except Exception as e:
        logger.error(f"Error in add book page: {str(e)}")
        return HTMLResponse(content=f"Error: {str(e)}", status_code=500)

@app.get("/genres", response_class=HTMLResponse)
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
            selected_ids = [int(id) for id in selected.split(',') if id.isdigit()]
            selected_genres = [g for g in all_genres if g.id in selected_ids]
            
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

# API: Add book
@app.post("/api/books/add")
async def add_book_api(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    author: str = Form(...),
    isbn: Optional[str] = Form(None),
    publication_year: Optional[int] = Form(None),
    publisher: Optional[str] = Form(None),
    page_count: Optional[int] = Form(None),
    language: str = Form("English"),
    description: Optional[str] = Form(None),
    summary: Optional[str] = Form(None),
    cover_image_url: Optional[str] = Form(None),
    rating: Optional[float] = Form(None),
    genres: List[int] = Form([])
):
    """API endpoint to add a new book"""
    try:
        book_data = {
            "title": title,
            "author": author,
            "isbn": isbn,
            "publication_year": publication_year,
            "publisher": publisher,
            "page_count": page_count,
            "language": language,
            "description": description,
            "summary": summary,
            "cover_image_url": cover_image_url,
            "rating": rating,
            "genres": genres
        }
        
        # Remove None values
        book_data = {k: v for k, v in book_data.items() if v is not None}
        
        book = BookService.create_book(db, book_data)
        return RedirectResponse(url=f"/book/{book.id}", status_code=303)
        
    except Exception as e:
        logger.error(f"Error adding book: {str(e)}")
        return RedirectResponse(url="/add-book?error=1", status_code=303)

# API: Update book cover image
@app.post("/api/books/{book_id}/update-cover")
async def update_book_cover(
    book_id: int,
    request: Request,
    db: Session = Depends(get_db),
    cover_image_url: str = Form(...)
):
    """Update book cover image URL"""
    try:
        book = BookService.get_book_by_id(db, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Update only the cover image
        book_data = {"cover_image_url": cover_image_url}
        updated_book = BookService.update_book(db, book_id, book_data)
        
        if updated_book:
            return RedirectResponse(url=f"/book/{book_id}", status_code=303)
        else:
            return RedirectResponse(url=f"/book/{book_id}?error=1", status_code=303)
            
    except Exception as e:
        logger.error(f"Error updating book cover: {str(e)}")
        return RedirectResponse(url=f"/book/{book_id}?error=1", status_code=303)

# Health check
@app.get("/health")
async def health_check():
    """Check if the application is running"""
    return {
        "status": "healthy",
        "service": "book-web-app",
        "version": "1.0.0",
        "database": "connected" if test_connection() else "disconnected"
    }

# Include routers
app.include_router(ai.router)
app.include_router(chat.router)
app.include_router(api_router, prefix="/api")

# Shortcuts for JS and CSS files
@app.get("/js/{filename}")
async def get_js(filename: str):
    """Shortcut for JavaScript files"""
    return StaticFiles(directory=str(static_path / "js")).get_response(filename)

@app.get("/css/{filename}")
async def get_css(filename: str):
    """Shortcut for CSS files"""
    return StaticFiles(directory=str(static_path / "css")).get_response(filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
