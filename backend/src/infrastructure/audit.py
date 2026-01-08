"""
Audit Logging Infrastructure
"""
from typing import Optional, Any, Dict
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.adapters.repositories.models import AuditLogModel


async def log_audit(
    db: AsyncSession,
    operator_id: int,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> None:
    """
    Record an audit log entry.
    
    Args:
        db: Database session
        operator_id: ID of the user performing the action
        action: Action name (e.g., "LOGIN", "CREATE_STUDENT")
        target_type: Type of the target object (e.g., "student", "test")
        target_id: ID of the target object
        details: Additional details in JSON format
        request: FastAPI Request object (to extract IP and User-Agent)
    """
    try:
        client_ip = None
        user_agent = None
        
        if request:
            if request.client:
                client_ip = request.client.host
            user_agent = request.headers.get("user-agent")
            
            # Try to get real IP if behind proxy
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()

        log_entry = AuditLogModel(
            operator_id=operator_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            client_ip=client_ip,
            user_agent=user_agent,
            details=details
        )
        
        db.add(log_entry)
        # We don't commit here to allow the caller to manage the transaction
        # or to commit along with the main business logic.
        # However, for audit logs, sometimes we want them to persist even if the main action fails?
        # Usually audit logs are part of the same transaction if the action succeeds.
        # If we want to log failures, we should handle that separately.
        # For now, we assume this is called within the successful transaction flow.
        
    except Exception as e:
        # Audit logging should not break the main application flow
        logger.error(f"Failed to create audit log: {e}")
