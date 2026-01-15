# Configuration - Add your API keys here
import os
from pathlib import Path

# Load from environment or .env file
class Config:
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # LLM Mode: "mock" or "openai"
    LLM_MODE: str = os.getenv("LLM_MODE", "mock")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./meeting_safe.db")
    
    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))


config = Config()
