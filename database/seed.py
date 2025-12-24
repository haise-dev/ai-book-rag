import pandas as pd
import os
from database.setup import DatabaseManager, BookDatabaseHelper

def seed_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'books.csv')
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    print("Loading data from CSV...")
    df = pd.read_csv(csv_path)
    
    db = DatabaseManager()
    if not db.connect(): return
    
    helper = BookDatabaseHelper(db)
    
    for _, row in df.iterrows():
        # 1. Insert Book
        book_id = helper.add_book(
            title=row['title'],
            author=row['author'],
            isbn=str(row['isbn']),
            publication_year=int(row['publication_year']),
            publisher=row['publisher'],
            page_count=int(row['page_count']),
            language=row['language'],
            description=row['description'],
            rating=float(row['rating']),
            cover_image_url=row['cover_image_url']
        )
        
        if book_id:
            # 2. Handle Genres (Tách chuỗi "Fiction,Classic")
            genres = [g.strip() for g in str(row['genres']).split(',')]
            for genre_name in genres:
                # Logic insert genre và book_genre cần được thêm vào helper
                # (Bạn có thể tự viết thêm hàm add_genre_to_book trong helper)
                pass 
                
    print("Seeding complete!")
    db.disconnect()

if __name__ == "__main__":
    seed_data()
