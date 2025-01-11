from dotenv import load_dotenv
import os
import logging
import traceback

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.routers import itinerary

app = FastAPI(
    title="Travel Itinerary API",
    description="API for generating personalized travel itineraries",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handler for detailed error reporting
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "message": "An unexpected error occurred",
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "type": "UNEXPECTED_ERROR"
            }
        }
    )

# Import and include routers
from .routers import itinerary

# Add routers
app.include_router(itinerary.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Verify environment variables and initialize services on startup."""
    required_env_vars = [
        "GEMINI_API_KEY",
        "WEATHER_API_KEY",
        "TICKETMASTER_API_KEY"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("All required environment variables are set")
    logger.info("Application startup complete")

@app.get("/")
async def root():
    return {"message": "Welcome to the Itinerary API"} 