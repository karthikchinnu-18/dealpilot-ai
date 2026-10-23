from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import init_db
from .routers import calls, negotiations, settings as settings_router, suppliers, telephony_webhooks

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield

app = FastAPI(
    title=settings.app_name,
    description="Autonomous AI Purchasing & Supplier Negotiation Platform. Conducts outbound phone calls, negotiates multilingual quotations, extracts structured offers, compares trade-offs, and enforces human approval.",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(negotiations.router)
app.include_router(suppliers.router)
app.include_router(calls.router)
app.include_router(telephony_webhooks.router)
app.include_router(settings_router.router)

@app.get("/")
def home():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "telephony_status": "configured" if settings.is_twilio_configured else "simulated_demo_mode",
        "notice": "Human approval is mandatory before any purchasing or binding financial commitment.",
        "documentation": "/docs",
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected",
        "telephony_provider": settings.telephony_provider,
        "twilio_ready": settings.is_twilio_configured,
    }
