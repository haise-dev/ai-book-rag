"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# Genre schemas
class GenreBase(BaseModel):
    name: str
    description: Optional[str] = None

class GenreResponse(GenreBase):
    id: int
    
    class Config:
        from_attributes = True

# Book schemas
class BookBase(BaseModel):
    title: str = Field(..., max_length=500)
    author: str = Field(..., max_length=300)
    isbn: Optional[str] = Field(None, max_length=20)
    publication_year: Optional[int] = None
    publisher: Optional[str] = Field(None, max_length=200)
    page_count: Optional[int] = None
    language: str = Field(default="English", max_length=50)
    description: Optional[str] = None
    summary: Optional[str] = None
    cover_image_url: Optional[str] = None
    pdf_path: Optional[str] = None
    rating: Optional[Decimal] = Field(None, ge=0, le=5)
    total_reviews: int = 0

class BookCreate(BookBase):
    genres: List[int] = []

class BookUpdate(BookBase):
    title: Optional[str] = None
    author: Optional[str] = None
    genres: Optional[List[int]] = None

class BookResponse(BookBase):
    id: int
    created_at: datetime
    updated_at: datetime
    genres: List[GenreResponse] = []
    
    class Config:
        from_attributes = True

# Session schemas
class SessionResponse(BaseModel):
    session_id: str
    saved_books: List[int] = []
    preferences: dict = {}
    
# API Response schemas
class SaveBookResponse(BaseModel):
    saved: bool
    message: str
    book_id: int

class SearchResponse(BaseModel):
    query: str
    count: int
    books: List[BookResponse]