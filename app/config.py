import os
import secrets
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("APP_ENV", os.getenv("ENV", "development"))
PORT = int(os.getenv("PORT", "8000"))
API_VERSION = os.getenv("API_VERSION", "1.0.0")
APP_NAME = "QuantumRand"

# CORS — locked down in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
if ENV == "production" and ALLOWED_ORIGINS == "*":
    ALLOWED_ORIGINS = "https://quantumrand.dev"

# Rate limit max bits per tier
MAX_BITS_FREE = int(os.getenv("MAX_BITS_FREE", "256"))
MAX_BITS_INDIE = int(os.getenv("MAX_BITS_INDIE", "1024"))
MAX_BITS_STARTUP = int(os.getenv("MAX_BITS_STARTUP", "2048"))
MAX_BITS_BUSINESS = int(os.getenv("MAX_BITS_BUSINESS", "4096"))

# Origin PilotOS (on-premise quantum computing)
PILOTOS_HOST = os.getenv("PILOTOS_HOST", "localhost")
PILOTOS_PORT = int(os.getenv("PILOTOS_PORT", "7100"))
PILOTOS_API_KEY = os.getenv("PILOTOS_API_KEY", os.getenv("ORIGIN_PILOTOS_LICENSE", ""))
PILOTOS_ENABLED = bool(PILOTOS_API_KEY)

# IBM Quantum (real quantum hardware)
IBM_QUANTUM_TOKEN = os.getenv("IBM_QUANTUM_TOKEN", "")
IBM_QUANTUM_ENABLED = bool(IBM_QUANTUM_TOKEN)

# Sentry error tracking
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Admin — None if not configured (disables admin endpoints)
_admin_secret = os.getenv("ADMIN_SECRET", "")
ADMIN_SECRET = _admin_secret if _admin_secret else None

# Demo rate limiting
DEMO_RATE_LIMIT = int(os.getenv("DEMO_RATE_LIMIT", "10"))  # requests per minute per IP

# Request timeout for quantum circuit execution (seconds)
CIRCUIT_TIMEOUT = int(os.getenv("CIRCUIT_TIMEOUT", "30"))
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))

# Stripe billing
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY)

# Stripe Price IDs (set after creating products in Stripe dashboard)
STRIPE_PRICE_INDIE = os.getenv("STRIPE_PRICE_INDIE", "")
STRIPE_PRICE_STARTUP = os.getenv("STRIPE_PRICE_STARTUP", "")
STRIPE_PRICE_BUSINESS = os.getenv("STRIPE_PRICE_BUSINESS", "")
