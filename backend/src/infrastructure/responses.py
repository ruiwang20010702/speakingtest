"""
Standard Response Models
Based on /api-design-principles workflow.
"""
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ============================================
# Pagination
# ============================================

class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response.
    
    Usage:
        return PaginatedResponse(
            items=users,
            total=100,
            page=1,
            page_size=20
        )
    """
    items: List[T]
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int):
        """Factory method to create paginated response."""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


# ============================================
# Error Handling
# ============================================

class ErrorDetail(BaseModel):
    """Single error detail."""
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    """
    Standard error response.
    
    Example:
        {
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": [{"field": "email", "message": "Invalid email format"}],
            "timestamp": "2026-01-05T15:00:00Z",
            "path": "/api/v1/users"
        }
    """
    error: str = Field(description="Error code (e.g., 'NotFound', 'ValidationError')")
    message: str = Field(description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(default=None, description="Detailed error info")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    path: Optional[str] = None


# ============================================
# Success Responses
# ============================================

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None


class CreatedResponse(BaseModel):
    """Response for created resources."""
    id: int
    message: str = "Resource created successfully"


# ============================================
# Helper Functions
# ============================================

def create_error_response(
    error: str,
    message: str,
    path: Optional[str] = None,
    details: Optional[List[dict]] = None,
) -> ErrorResponse:
    """Create a standardized error response."""
    error_details = None
    if details:
        error_details = [ErrorDetail(**d) for d in details]
    
    return ErrorResponse(
        error=error,
        message=message,
        path=path,
        details=error_details,
    )
