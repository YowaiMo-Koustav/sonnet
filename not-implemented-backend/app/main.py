from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from datetime import datetime
import uuid
import logging
from app.core.config import get_settings
from app.services.background_jobs import get_scheduler
from app.core.middleware import (
    CompressionMiddleware,
    ETagMiddleware,
    RateLimitMiddleware,
    ErrorHandlingMiddleware
)
from app.api.locations import router as locations_router
from app.api.schemes import router as schemes_router
from app.api.pdf import router as pdf_router
from app.api.users import router as users_router
from app.api.applications import router as applications_router
from app.api.gemini import router as gemini_router

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events.
    
    Starts the background job scheduler on startup and
    shuts it down on application shutdown.
    """
    # Startup: Start the background job scheduler
    scheduler = get_scheduler()
    scheduler.start()
    
    yield
    
    # Shutdown: Stop the background job scheduler
    scheduler.shutdown()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A scholarship and job discovery system for students in rural districts",
    lifespan=lifespan
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Vite dev server (configured port)
        "http://localhost:5173",  # Vite default port
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handlers for consistent error responses
def create_error_response(status_code: int, error_code: str, message: str, details: dict, request_id: str) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPException."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
    }
    error_code = error_codes.get(exc.status_code, "HTTP_ERROR")
    
    logger.warning(
        f"HTTP Exception: {request.method} {request.url.path} "
        f"status={exc.status_code} detail={exc.detail} request_id={request_id}"
    )
    
    return create_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=exc.detail,
        details={},
        request_id=request_id
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTPException."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
    }
    error_code = error_codes.get(exc.status_code, "HTTP_ERROR")
    
    logger.warning(
        f"HTTP Exception: {request.method} {request.url.path} "
        f"status={exc.status_code} detail={exc.detail} request_id={request_id}"
    )
    
    return create_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=exc.detail,
        details={},
        request_id=request_id
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # Extract field-level validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation Error: {request.method} {request.url.path} "
        f"errors={len(errors)} request_id={request_id}"
    )
    
    return create_error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": errors},
        request_id=request_id
    )


# Add middleware for API response optimizations (Requirement 7.1)
# Order matters: Error handling (outermost) -> Rate limiting -> ETag -> Compression (innermost)
app.add_middleware(CompressionMiddleware, min_size=500)
app.add_middleware(ETagMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(ErrorHandlingMiddleware)

# Register routers
app.include_router(locations_router)
app.include_router(schemes_router)
app.include_router(pdf_router)
app.include_router(users_router)
app.include_router(applications_router)
app.include_router(gemini_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Sonnet - Smart Scheme & Job Informer",
        "version": settings.app_version
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
