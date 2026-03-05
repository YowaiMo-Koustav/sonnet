"""Middleware for API response optimizations and error handling."""
import hashlib
import time
import logging
import traceback
import uuid
from typing import Callable
from datetime import datetime
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from pydantic import ValidationError
import gzip
import json

# Configure logger
logger = logging.getLogger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to compress responses using gzip.
    
    Compresses responses when:
    - Client accepts gzip encoding (Accept-Encoding header)
    - Response is larger than min_size bytes
    - Content-Type is compressible (JSON, text, etc.)
    """
    
    def __init__(self, app, min_size: int = 500):
        super().__init__(app)
        self.min_size = min_size
        self.compressible_types = {
            "application/json",
            "application/javascript",
            "text/html",
            "text/css",
            "text/plain",
            "text/xml",
            "application/xml",
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and compress response if applicable."""
        response = await call_next(request)
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response
        
        # Check if content type is compressible
        content_type = response.headers.get("content-type", "")
        is_compressible = any(ct in content_type for ct in self.compressible_types)
        
        if not is_compressible:
            return response
        
        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Only compress if body is large enough
        if len(body) < self.min_size:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        
        # Compress the body
        compressed_body = gzip.compress(body, compresslevel=6)
        
        # Create new response with compressed body
        headers = dict(response.headers)
        headers["Content-Encoding"] = "gzip"
        headers["Content-Length"] = str(len(compressed_body))
        headers["Vary"] = "Accept-Encoding"
        
        return Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )


class ETagMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add ETag support for caching.
    
    Generates ETags based on response content hash and handles
    conditional requests using If-None-Match header.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add ETag support."""
        # Only apply to GET and HEAD requests
        if request.method not in ["GET", "HEAD"]:
            return await call_next(request)
        
        # Get response
        response = await call_next(request)
        
        # Only add ETag for successful responses
        if response.status_code != 200:
            return response
        
        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Generate ETag from content hash
        etag = f'"{hashlib.md5(body).hexdigest()}"'
        
        # Check if client sent If-None-Match header
        if_none_match = request.headers.get("if-none-match")
        
        if if_none_match and if_none_match == etag:
            # Content hasn't changed, return 304 Not Modified
            return Response(
                status_code=304,
                headers={
                    "ETag": etag,
                    "Cache-Control": "private, max-age=300",  # 5 minutes
                },
            )
        
        # Add ETag to response
        headers = dict(response.headers)
        headers["ETag"] = etag
        headers["Cache-Control"] = "private, max-age=300"  # 5 minutes
        
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API rate limiting.
    
    Implements a simple in-memory rate limiter based on IP address.
    Limits requests per IP to prevent abuse.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # {ip: [(timestamp, count), ...]}
        self.cleanup_interval = 60  # Clean up old entries every 60 seconds
        self.last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove entries older than 1 minute."""
        current_time = time.time()
        cutoff_time = current_time - 60
        
        for ip in list(self.request_counts.keys()):
            self.request_counts[ip] = [
                (ts, count) for ts, count in self.request_counts[ip]
                if ts > cutoff_time
            ]
            if not self.request_counts[ip]:
                del self.request_counts[ip]
        
        self.last_cleanup = current_time
    
    def _get_request_count(self, ip: str) -> int:
        """Get the number of requests from an IP in the last minute."""
        current_time = time.time()
        cutoff_time = current_time - 60
        
        if ip not in self.request_counts:
            return 0
        
        # Count requests in the last minute
        count = sum(
            c for ts, c in self.request_counts[ip]
            if ts > cutoff_time
        )
        return count
    
    def _record_request(self, ip: str):
        """Record a request from an IP."""
        current_time = time.time()
        
        if ip not in self.request_counts:
            self.request_counts[ip] = []
        
        self.request_counts[ip].append((current_time, 1))
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and enforce rate limits."""
        # Periodic cleanup
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        request_count = self._get_request_count(client_ip)
        
        if request_count >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit is {self.requests_per_minute} requests per minute.",
                    "retry_after": 60,
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                },
            )
        
        # Record the request
        self._record_request(client_ip)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.requests_per_minute - request_count - 1
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response



class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    
    Handles different error categories:
    - User Input Errors (400): Invalid search queries, malformed data
    - Data Validation Errors (422): Missing required fields, invalid references
    - Processing Errors (500): PDF parsing failures, extraction timeouts
    - System Errors (503): Database connection failures, external service unavailability
    
    Returns consistent error response format and logs all errors with context.
    """
    
    # Retry configuration for transient failures
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5  # seconds
    TRANSIENT_ERROR_CODES = {503, 504}  # Service Unavailable, Gateway Timeout
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle any errors that occur."""
        # Generate unique request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Record request start time
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log successful requests (only for non-200 status codes)
            if response.status_code >= 400:
                duration = time.time() - start_time
                logger.warning(
                    f"Request failed: {request.method} {request.url.path} "
                    f"status={response.status_code} duration={duration:.3f}s "
                    f"request_id={request_id}"
                )
            
            return response
            
        except HTTPException as exc:
            # FastAPI HTTPException - user input errors
            return self._handle_http_exception(exc, request, request_id, start_time)
            
        except StarletteHTTPException as exc:
            # Starlette HTTPException
            return self._handle_http_exception(exc, request, request_id, start_time)
            
        except ValidationError as exc:
            # Pydantic validation errors - data validation errors
            return self._handle_validation_error(exc, request, request_id, start_time)
            
        except IntegrityError as exc:
            # Database integrity constraint violations
            return self._handle_integrity_error(exc, request, request_id, start_time)
            
        except OperationalError as exc:
            # Database operational errors (connection issues, etc.)
            return self._handle_operational_error(exc, request, request_id, start_time)
            
        except SQLAlchemyError as exc:
            # Other database errors
            return self._handle_database_error(exc, request, request_id, start_time)
            
        except ValueError as exc:
            # Value errors - typically user input issues
            return self._handle_value_error(exc, request, request_id, start_time)
            
        except Exception as exc:
            # Catch-all for unexpected errors
            return self._handle_unexpected_error(exc, request, request_id, start_time)
    
    def _create_error_response(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: dict,
        request_id: str
    ) -> JSONResponse:
        """
        Create a standardized error response.
        
        Error Response Format:
        {
            "error_code": string,
            "message": string,
            "details": dict,
            "timestamp": ISO datetime,
            "request_id": string
        }
        """
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
    
    def _handle_http_exception(
        self,
        exc: Exception,
        request: Request,
        request_id: str,
        start_time: float
    ) -> JSONResponse:
        """Handle HTTP exceptions (user input errors)."""
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc))
        
        duration = time.time() - start_time
        
        # Log the error
        logger.warning(
            f"HTTP Exception: {request.method} {request.url.path} "
            f"status={status_code} detail={detail} "
            f"duration={duration:.3f}s request_id={request_id}"
        )
        
        # Determine error code based on status
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
        error_code = error_codes.get(status_code, "HTTP_ERROR")
        
        return self._create_error_response(
            status_code=status_code,
            error_code=error_code,
            message=detail,
            details={},
            request_id=request_id
        )
    
    def _handle_validation_error(
        self,
        exc: ValidationError,
        request: Request,
        request_id: str,
        start_time: float
    ) -> JSONResponse:
        """Handle Pydantic validation errors (data validation errors)."""
        duration = time.time() - start_time
        
        # Extract field-level validation errors
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })
        
        # Log the error
        logger.warning(
            f"Validation Error: {request.method} {request.url.path} "
            f"errors={len(errors)} duration={duration:.3f}s request_id={request_id}"
        )
        
        return self._create_error_response(
            status_code=422,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
            request_id=request_id
        )
    
    def _handle_integrity_error(
        self,
        exc: IntegrityError,
        request: Request,
        request_id: str,
        start_time: float
    ) -> JSONResponse:
        """Handle database integrity constraint violations."""
        duration = time.time() - start_time
        
        # Extract constraint information
        error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
        
        # Log the error
        logger.error(
            f"Integrity Error: {request.method} {request.url.path} "
            f"error={error_msg} duration={duration:.3f}s request_id={request_id}",
            exc_info=True
        )
        
        # Provide user-friendly message
        message = "Data integrity constraint violation"
        if "unique" in error_msg.lower():
            message = "A record with this information already exists"
        elif "foreign key" in error_msg.lower():
            message = "Referenced record does not exist"
        elif "not null" in error_msg.lower():
            message = "Required field is missing"
        
        return self._create_error_response(
            status_code=422,
            error_code="INTEGRITY_ERROR",
            message=message,
            details={"database_error": error_msg},
            request_id=request_id
        )
    
    def _handle_operational_error(
        self,
        exc: OperationalError,
        request: Request,
        request_id: str,
        start_time: float
    ) -> JSONResponse:
        """Handle database operational errors (connection issues, etc.)."""
        duration = time.time() - start_time
        
        error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
        
        # Log the error
        logger.error(
            f"Operational Error: {request.method} {request.url.path} "
            f"error={error_msg} duration={duration:.3f}s request_id={request_id}",
            exc_info=True
        )
        
        # Return 503 Service Unavailable for database connection issues
        return self._create_error_response(
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            message="Service temporarily unavailable. Please try again later.",
            details={"retry_after": 60},
            request_id=request_id
        )
    
    def _handle_database_error(
        self,
        exc: SQLAlchemyError,
        request: Request,
        request_id: str,
        start_time: float
    ) -> JSONResponse:
        """Handle other database errors."""
        duration = time.time() - start_time
        
        error_msg = str(exc)
        
        # Log the error
        logger.error(
            f"Database Error: {request.method} {request.url.path} "
            f"error={error_msg} duration={duration:.3f}s request_id={request_id}",
            exc_info=True
        )
        
        return self._create_error_response(
            status_code=500,
            error_code="DATABASE_ERROR",
            message="An error occurred while processing your request",
            details={},
            request_id=request_id
        )
    
    def _handle_value_error(
        self,
        exc: ValueError,
        request: Request,
        request_id: str,
        start_time: float
    ) -> JSONResponse:
        """Handle value errors (typically user input issues)."""
        duration = time.time() - start_time
        
        error_msg = str(exc)
        
        # Log the error
        logger.warning(
            f"Value Error: {request.method} {request.url.path} "
            f"error={error_msg} duration={duration:.3f}s request_id={request_id}"
        )
        
        return self._create_error_response(
            status_code=400,
            error_code="INVALID_VALUE",
            message=error_msg,
            details={},
            request_id=request_id
        )
    
    def _handle_unexpected_error(
        self,
        exc: Exception,
        request: Request,
        request_id: str,
        start_time: float
    ) -> JSONResponse:
        """Handle unexpected errors."""
        duration = time.time() - start_time
        
        error_msg = str(exc)
        error_type = type(exc).__name__
        
        # Log the full traceback for debugging
        logger.error(
            f"Unexpected Error: {request.method} {request.url.path} "
            f"type={error_type} error={error_msg} "
            f"duration={duration:.3f}s request_id={request_id}",
            exc_info=True
        )
        
        # Don't expose internal error details to users
        return self._create_error_response(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later.",
            details={"error_type": error_type},
            request_id=request_id
        )
