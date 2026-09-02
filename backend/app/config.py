import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env file from the root directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
env_path = ROOT_DIR / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    # MongoDB settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "mk_path")

    # Clerk settings
    CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
    VITE_CLERK_PUBLISHABLE_KEY: str = os.getenv("VITE_CLERK_PUBLISHABLE_KEY", "")

    # AI API keys
    GEMINI_API_KEY_RAW: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-latest")

    # Neo4j Graph Layer settings (Phase 14)
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")


    @property
    def GEMINI_API_KEYS(self) -> List[str]:
        if not self.GEMINI_API_KEY_RAW:
            return []
        # Support both comma separated list or single key
        return [k.strip() for k in self.GEMINI_API_KEY_RAW.split(",") if k.strip()]

    # Demo Mode fallback when database or internet is down
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "False").lower() in ("true", "1", "yes")

    # Local development server settings
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

settings = Settings()
