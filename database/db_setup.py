#!/usr/bin/env python3
"""
Book Recommendation System - PostgreSQL Database Setup
This script creates and manages the database schema for the AI book recommendation system
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseManager:
    """Manages PostgreSQL database operations for the book recommendation system"""
    
    def __init__(self):
        """Initialize database connection parameters from environment variables"""
        self.host = os.getenv('POSTGRES_HOST', 'localhost')
        self.port = int(os.getenv('POSTGRES_PORT', 5432))
        self.database = os.getenv('POSTGRES_DB')
        self.user = os.getenv('POSTGRES_USER')
        self.password = os.getenv('POSTGRES_PASSWORD')
        self.connection = None
        self.cursor = None
        
        # Validate environment variables
        if not all([self.database, self.user, self.password]):
            raise ValueError("Missing required environment variables: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD")
    
    def connect(self):
        """Establish connection to PostgreSQL database"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.connection.cursor()
            logger.info(f"Successfully connected to PostgreSQL database '{self.database}' at {self.host}:{self.port}")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Disconnected from database")
    
    def execute_sql(self, sql_query, params=None, commit=True):
        """Execute SQL query with error handling"""
        try:
            if params:
                self.cursor.execute(sql_query, params)
            else:
                self.cursor.execute(sql_query)
            
            if commit:
                self.connection.commit()
            return True
        except psycopg2.Error as e:
            self.connection.rollback()
            logger.error(f"SQL execution error: {e}")
            logger.error(f"Query: {sql_query[:100]}...")
            return False
    
    def check_existing_tables(self):
        """Check and list existing tables in the database"""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
        """
        self.cursor.execute(query)
        tables = self.cursor.fetchall()
        
        if tables:
            logger.info("Existing tables found:")
            for table in tables:
                logger.info(f"  - {table[0]}")
            return [table[0] for table in tables]
        else:
            logger.info("No existing tables found in the database")
            return []
    
    def drop_all_tables(self):
        """Drop all existing tables (with confirmation)"""
        existing_tables = self.check_existing_tables()
        
        if not existing_tables:
            logger.info("No tables to drop")
            return True
        
        # In automated script, we'll proceed with dropping
        # In production, you'd want to add more safeguards
        logger.warning("Dropping all existing tables...")
        
        try:
            self.execute_sql("DROP SCHEMA public CASCADE;", commit=False)
            self.execute_sql("CREATE SCHEMA public;", commit=False)
            self.execute_sql("GRANT ALL ON SCHEMA public TO postgres;", commit=False)
            self.execute_sql("GRANT ALL ON SCHEMA public TO public;", commit=True)
            logger.info("Successfully dropped all tables")
            return True
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            return False
    
    def create_schema(self):
        """Create the complete database schema for book recommendation system"""
        
        # Schema definition
        schema_sql = """
        -- ============================================
        -- AI BOOK RECOMMENDATION SYSTEM DATABASE SCHEMA
        -- Complete SQL for PostgreSQL Implementation
        -- ============================================
        
        -- Main books table
        CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY,
            isbn VARCHAR(20) UNIQUE,
            title VARCHAR(500) NOT NULL,
            author VARCHAR(300) NOT NULL,
            publication_year INTEGER,
            publisher VARCHAR(200),
            page_count INTEGER,
            language VARCHAR(50) DEFAULT 'English',
            description TEXT,
            summary TEXT, -- For RAG purposes
            cover_image_url TEXT,
            pdf_path VARCHAR(500), -- Path to PDF file if available
            rating DECIMAL(3,2), -- Average rating
            total_reviews INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Genres table
        CREATE TABLE IF NOT EXISTS genres (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT
        );
        
        -- Book-Genre relationship (many-to-many)
        CREATE TABLE IF NOT EXISTS book_genres (
            book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
            genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
            PRIMARY KEY (book_id, genre_id)
        );
        
        -- Authors table (for detailed author info)
        CREATE TABLE IF NOT EXISTS authors (
            id SERIAL PRIMARY KEY,
            name VARCHAR(300) NOT NULL,
            biography TEXT,
            birth_year INTEGER,
            nationality VARCHAR(100),
            website VARCHAR(200)
        );
        
        -- Book-Author relationship (many-to-many for co-authors)
        CREATE TABLE IF NOT EXISTS book_authors (
            book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
            author_id INTEGER REFERENCES authors(id) ON DELETE CASCADE,
            role VARCHAR(50) DEFAULT 'author', -- author, co-author, editor, translator
            PRIMARY KEY (book_id, author_id)
        );
        
        -- User preferences and reading history
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(100) UNIQUE NOT NULL,
            preferences JSONB, -- Store user preferences as JSON
            reading_history JSONB, -- Books user has interacted with
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Book recommendations log
        CREATE TABLE IF NOT EXISTS recommendation_logs (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(100),
            query TEXT,
            recommended_books JSONB, -- Array of book IDs and scores
            feedback_rating INTEGER, -- 1-5 rating on recommendation quality
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Book content chunks for RAG
        CREATE TABLE IF NOT EXISTS book_chunks (
            id SERIAL PRIMARY KEY,
            book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
            chunk_text TEXT NOT NULL,
            chunk_order INTEGER,
            chunk_type VARCHAR(50), -- 'summary', 'chapter', 'review', 'description'
            embedding_id VARCHAR(100), -- Reference to Qdrant vector ID
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Execute schema creation
        logger.info("Creating database schema...")
        if self.execute_sql(schema_sql):
            logger.info("Successfully created all tables")
            
            # Create indexes
            self.create_indexes()
            
            # Insert sample genres
            self.insert_sample_genres()
            
            return True
        else:
            logger.error("Failed to create database schema")
            return False
    
    def create_indexes(self):
        """Create indexes for better query performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_books_title ON books USING gin(to_tsvector('english', title));",
            "CREATE INDEX IF NOT EXISTS idx_books_author ON books USING gin(to_tsvector('english', author));",
            "CREATE INDEX IF NOT EXISTS idx_books_description ON books USING gin(to_tsvector('english', description));",
            "CREATE INDEX IF NOT EXISTS idx_books_rating ON books(rating DESC);",
            "CREATE INDEX IF NOT EXISTS idx_books_year ON books(publication_year DESC);",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_logs_session_id ON recommendation_logs(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_book_chunks_book_id ON book_chunks(book_id);"
        ]
        
        logger.info("Creating indexes...")
        for index in indexes:
            if self.execute_sql(index):
                logger.info(f"Created index: {index.split('idx_')[1].split(' ')[0]}")
    
    def insert_sample_genres(self):
        """Insert sample genres into the database"""
        genres_sql = """
        INSERT INTO genres (name, description) VALUES
        ('Fiction', 'Narrative literature created from imagination'),
        ('Non-Fiction', 'Factual or informative literature'),
        ('Science Fiction', 'Fiction dealing with futuristic concepts'),
        ('Mystery', 'Fiction involving mysterious events'),
        ('Romance', 'Fiction focusing on love relationships'),
        ('Biography', 'Account of someone''s life written by someone else'),
        ('History', 'Study of past events'),
        ('Self-Help', 'Books designed to help readers improve themselves'),
        ('Technology', 'Books about technological subjects'),
        ('Business', 'Books about business and entrepreneurship'),
        ('Fantasy', 'Fiction with magical or supernatural elements'),
        ('Horror', 'Fiction intended to frighten or create suspense'),
        ('Thriller', 'Fast-paced fiction with constant danger'),
        ('Philosophy', 'Study of fundamental nature of reality'),
        ('Psychology', 'Study of mind and behavior')
        ON CONFLICT (name) DO NOTHING;
        """
        
        if self.execute_sql(genres_sql):
            logger.info("Successfully inserted sample genres")
    
    def verify_schema(self):
        """Verify that all tables were created successfully"""
        expected_tables = [
            'books', 'genres', 'book_genres', 'authors', 
            'book_authors', 'user_sessions', 'recommendation_logs', 'book_chunks'
        ]
        
        existing_tables = self.check_existing_tables()
        
        missing_tables = set(expected_tables) - set(existing_tables)
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            return False
        
        logger.info("All expected tables are present")
        
        # Check row counts
        for table in expected_tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = self.cursor.fetchone()[0]
            logger.info(f"Table '{table}': {count} rows")
        
        return True


# Helper functions for database operations
class BookDatabaseHelper:
    """Helper functions for common database operations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def add_book(self, title, author, **kwargs):
        """Add a new book to the database"""
        query = """
        INSERT INTO books (title, author, isbn, publication_year, publisher, 
                          page_count, language, description, summary, cover_image_url, 
                          pdf_path, rating)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        
        params = (
            title, author, kwargs.get('isbn'), kwargs.get('publication_year'),
            kwargs.get('publisher'), kwargs.get('page_count'), 
            kwargs.get('language', 'English'), kwargs.get('description'),
            kwargs.get('summary'), kwargs.get('cover_image_url'),
            kwargs.get('pdf_path'), kwargs.get('rating')
        )
        
        try:
            self.db.cursor.execute(query, params)
            book_id = self.db.cursor.fetchone()[0]
            self.db.connection.commit()
            logger.info(f"Added book '{title}' with ID: {book_id}")
            return book_id
        except Exception as e:
            self.db.connection.rollback()
            logger.error(f"Failed to add book: {e}")
            return None
    
    def search_books(self, search_term):
        """Search books by title or author"""
        query = """
        SELECT id, title, author, publication_year, rating
        FROM books
        WHERE to_tsvector('english', title || ' ' || author) @@ plainto_tsquery('english', %s)
        ORDER BY rating DESC NULLS LAST
        LIMIT 10;
        """
        
        try:
            self.db.cursor.execute(query, (search_term,))
            results = self.db.cursor.fetchall()
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_book_by_id(self, book_id):
        """Get book details by ID"""
        query = """
        SELECT * FROM books WHERE id = %s;
        """
        
        try:
            self.db.cursor.execute(query, (book_id,))
            result = self.db.cursor.fetchone()
            
            if result:
                columns = [desc[0] for desc in self.db.cursor.description]
                return dict(zip(columns, result))
            return None
        except Exception as e:
            logger.error(f"Failed to get book: {e}")
            return None
    
    def add_book_chunk(self, book_id, chunk_text, chunk_order, chunk_type='description'):
        """Add a text chunk for RAG processing"""
        query = """
        INSERT INTO book_chunks (book_id, chunk_text, chunk_order, chunk_type)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """
        
        try:
            self.db.cursor.execute(query, (book_id, chunk_text, chunk_order, chunk_type))
            chunk_id = self.db.cursor.fetchone()[0]
            self.db.connection.commit()
            return chunk_id
        except Exception as e:
            self.db.connection.rollback()
            logger.error(f"Failed to add chunk: {e}")
            return None


def main():
    """Main function to set up the database"""
    print("=" * 60)
    print("AI Book Recommendation System - Database Setup")
    print("=" * 60)
    
    # Create database manager
    try:
        db_manager = DatabaseManager()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please ensure .env file contains: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD")
        sys.exit(1)
    
    # Connect to database
    if not db_manager.connect():
        logger.error("Failed to connect to database. Please check:")
        logger.error("1. PostgreSQL container is running: docker ps | grep postgres")
        logger.error("2. Environment variables are correctly set in .env file")
        logger.error("3. Database is accessible on localhost:5432")
        sys.exit(1)
    
    try:
        # Check existing tables
        print("\n" + "=" * 60)
        print("Checking existing database state...")
        existing_tables = db_manager.check_existing_tables()
        
        # Ask user whether to drop existing tables
        if existing_tables:
            response = input("\nExisting tables found. Drop all tables and recreate? (yes/no): ").lower()
            if response == 'yes':
                db_manager.drop_all_tables()
            else:
                print("Keeping existing tables. Will create missing tables only.")
        
        # Create schema
        print("\n" + "=" * 60)
        print("Creating database schema...")
        if db_manager.create_schema():
            print("\n✓ Database schema created successfully!")
        else:
            print("\n✗ Failed to create database schema")
            sys.exit(1)
        
        # Verify schema
        print("\n" + "=" * 60)
        print("Verifying database schema...")
        if db_manager.verify_schema():
            print("\n✓ All tables verified successfully!")
        else:
            print("\n✗ Schema verification failed")
            sys.exit(1)
        
        # Test helper functions
        print("\n" + "=" * 60)
        print("Testing helper functions...")
        helper = BookDatabaseHelper(db_manager)
        
        # Add a test book
        test_book_id = helper.add_book(
            title="The Pragmatic Programmer",
            author="David Thomas, Andrew Hunt",
            isbn="9780135957059",
            publication_year=2019,
            publisher="Addison-Wesley",
            description="A guide to pragmatic programming for software developers",
            rating=4.5
        )
        
        if test_book_id:
            print(f"✓ Test book added successfully (ID: {test_book_id})")
            
            # Search for the book
            search_results = helper.search_books("pragmatic")
            if search_results:
                print(f"✓ Search test successful: Found {len(search_results)} results")
        
        print("\n" + "=" * 60)
        print("Database setup completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        db_manager.disconnect()


if __name__ == "__main__":
    main()
