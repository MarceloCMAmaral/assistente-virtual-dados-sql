"""
Centralized configuration for the Assistente Virtual de Dados.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # LLM Provider: "openai" or "gemini"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./anexo_desafio_1.db")
    
    # LLM Models
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Agent Configuration
    MAX_RETRY_ATTEMPTS: int = 3
    DEFAULT_QUERY_LIMIT: int = 10
    
    # Visualization
    MAX_BARS_CHART: int = 15  # Max items for bar chart before falling back to table
    MIN_ROWS_HISTOGRAM: int = 10  # Minimum rows to show histogram
    
    @classmethod
    def get_database_uri(cls) -> str:
        """Get the SQLite database URI."""
        db_path = Path(cls.DATABASE_PATH).resolve()
        return f"sqlite:///{db_path}"
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if cls.LLM_PROVIDER not in ["openai", "gemini"]:
            errors.append(f"Invalid LLM_PROVIDER: {cls.LLM_PROVIDER}. Must be 'openai' or 'gemini'.")
        
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when using OpenAI provider.")
        
        if cls.LLM_PROVIDER == "gemini" and not cls.GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY is required when using Gemini provider.")
        
        db_path = Path(cls.DATABASE_PATH)
        if not db_path.exists():
            errors.append(f"Database file not found: {cls.DATABASE_PATH}")
        
        return errors
