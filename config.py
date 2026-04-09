# This module loads environment variables and exposes shared ATLAS configuration values.
import os

from dotenv import load_dotenv


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "openrouter/free")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "llama3.2:3b")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./atlas.db")
MAX_RETRIES = 3


if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY is missing.")
