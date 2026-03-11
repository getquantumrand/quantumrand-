import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")
PORT = int(os.getenv("PORT", "8000"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///quantumrand.db")
API_VERSION = os.getenv("API_VERSION", "1.0.0")
APP_NAME = "QuantumRand"

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
if ENV == "production" and ALLOWED_ORIGINS == "*":
    ALLOWED_ORIGINS = "https://quantumrand.dev"

# Rate limit max bits per tier
MAX_BITS_FREE = int(os.getenv("MAX_BITS_FREE", "256"))
MAX_BITS_INDIE = int(os.getenv("MAX_BITS_INDIE", "1024"))
MAX_BITS_STARTUP = int(os.getenv("MAX_BITS_STARTUP", "2048"))
MAX_BITS_BUSINESS = int(os.getenv("MAX_BITS_BUSINESS", "4096"))

# Derive DB path from DATABASE_URL
if DATABASE_URL.startswith("sqlite:///"):
    DB_FILE = DATABASE_URL.replace("sqlite:///", "")
else:
    DB_FILE = "quantumrand.db"

# Origin PilotOS (on-premise quantum computing)
PILOTOS_HOST = os.getenv("PILOTOS_HOST", "localhost")
PILOTOS_PORT = int(os.getenv("PILOTOS_PORT", "7100"))
PILOTOS_API_KEY = os.getenv("PILOTOS_API_KEY", os.getenv("ORIGIN_PILOTOS_LICENSE", ""))
PILOTOS_ENABLED = bool(PILOTOS_API_KEY)

# Admin
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "quantumrand-admin")

# Legacy alias
ORIGIN_QC_TOKEN = PILOTOS_API_KEY
ORIGIN_QC_ENABLED = PILOTOS_ENABLED
