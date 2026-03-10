import os

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

# Origin Quantum Cloud (pyqpanda)
ORIGIN_QC_TOKEN = os.getenv("ORIGIN_QC_TOKEN", "")
ORIGIN_QC_ENABLED = bool(ORIGIN_QC_TOKEN)
