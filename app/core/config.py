import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

class Settings:
    PROJECT_NAME: str = "AI Book Recommendation RAG"
    PROJECT_VERSION: str = "1.0.0"
    
    # Database Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "n8n")
    
    # Construct Database URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    # AI Service URLs
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    N8N_URL: str = os.getenv("N8N_URL", "http://localhost:5678")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")

settings = Settings()
