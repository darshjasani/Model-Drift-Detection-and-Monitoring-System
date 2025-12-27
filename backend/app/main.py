"""FastAPI Main Application"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db, check_db_connection
from app.api import prediction, monitoring, websocket
from app.ml.model import get_model

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info("=" * 60)
    
    # Initialize database
    logger.info("Initializing database...")
    try:
        init_db()
        if check_db_connection():
            logger.info("✓ Database connection successful")
        else:
            logger.warning("✗ Database connection failed")
    except Exception as e:
        logger.error(f"✗ Database initialization error: {e}")
    
    # Load ML model
    logger.info("Loading ML model...")
    try:
        model = get_model()
        logger.info(f"✓ Model loaded: {model.version}")
        logger.info(f"  Training date: {model.training_date}")
        logger.info(f"  Features: {len(model.feature_names)}")
    except Exception as e:
        logger.error(f"✗ Model loading error: {e}")
        logger.warning("  Prediction endpoints will not work until model is trained")
    
    logger.info("=" * 60)
    logger.info("Application started successfully!")
    logger.info(f"API available at: http://0.0.0.0:8000")
    logger.info(f"Docs available at: http://0.0.0.0:8000/docs")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # Convert to ms
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint for Docker healthcheck
    
    Returns basic health status of the application
    """
    db_status = check_db_connection()
    
    # Check model status
    model_status = False
    try:
        model = get_model()
        model_status = model.health_check()
    except:
        pass
    
    overall_status = "healthy" if (db_status and model_status) else "degraded"
    
    return {
        "status": overall_status,
        "database": "healthy" if db_status else "unhealthy",
        "model": "healthy" if model_status else "unhealthy",
        "timestamp": time.time()
    }


@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.API_TITLE}",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(prediction.router)
app.include_router(monitoring.router)
app.include_router(websocket.router)


# Development hot reload info
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting development server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

