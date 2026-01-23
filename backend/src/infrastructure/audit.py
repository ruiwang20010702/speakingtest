"""
Audit Logging Infrastructure

Security:
- Hash chain: Each record contains SHA-256 hash of previous record
- Record hash: Each record has a SHA-256 hash of its contents
- Tamper detection: Any modification breaks the hash chain
- Verification: Use verify_audit_chain() to check integrity
"""
import hashlib
import json
from typing import Optional, Any, Dict
from datetime import datetime
from fastapi import Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.adapters.repositories.models import AuditLogModel
from src.infrastructure.timezone import now as china_now


def _compute_record_hash(
    operator_id: int,
    action: str,
    target_type: Optional[str],
    target_id: Optional[int],
    client_ip: Optional[str],
    user_agent: Optional[str],
    details: Optional[Dict[str, Any]],
    created_at: datetime,
    prev_hash: Optional[str]
) -> str:
    """
    Compute SHA-256 hash of audit record content.
    
    Hash includes all record fields to detect any tampering.
    """
    # Create a deterministic string representation
    hash_content = {
        "operator_id": operator_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "client_ip": client_ip,
        "user_agent": user_agent,
        "details": details,
        "created_at": created_at.isoformat() if created_at else None,
        "prev_hash": prev_hash
    }
    
    # Sort keys for deterministic serialization
    content_str = json.dumps(hash_content, sort_keys=True, ensure_ascii=False, default=str)
    
    return hashlib.sha256(content_str.encode('utf-8')).hexdigest()


async def _get_last_record_hash(db: AsyncSession) -> Optional[str]:
    """Get the record_hash of the most recent audit log entry."""
    stmt = select(AuditLogModel.record_hash).order_by(desc(AuditLogModel.id)).limit(1)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    return row


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
    Record an audit log entry with hash chain for tamper detection.
    
    Args:
        db: Database session
        operator_id: ID of the user performing the action
        action: Action name (e.g., "LOGIN", "CREATE_STUDENT")
        target_type: Type of the target object (e.g., "student", "test")
        target_id: ID of the target object
        details: Additional details in JSON format
        request: FastAPI Request object (to extract IP and User-Agent)
    
    Security:
        - Each record contains hash of previous record (prev_hash)
        - Each record has its own hash (record_hash)
        - Breaking the chain indicates tampering
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
        
        # Get hash of previous record for chain
        prev_hash = await _get_last_record_hash(db)
        
        # Create timestamp
        created_at = china_now()
        
        # Compute record hash
        record_hash = _compute_record_hash(
            operator_id=operator_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            client_ip=client_ip,
            user_agent=user_agent,
            details=details,
            created_at=created_at,
            prev_hash=prev_hash
        )

        log_entry = AuditLogModel(
            operator_id=operator_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            client_ip=client_ip,
            user_agent=user_agent,
            details=details,
            created_at=created_at,
            prev_hash=prev_hash,
            record_hash=record_hash
        )
        
        db.add(log_entry)
        # We don't commit here to allow the caller to manage the transaction
        # The hash chain is still valid because we use the same session.
        
    except Exception as e:
        # Audit logging should not break the main application flow
        logger.error(f"Failed to create audit log: {e}")


async def verify_audit_chain(db: AsyncSession, start_id: Optional[int] = None, limit: int = 1000) -> Dict[str, Any]:
    """
    Verify the integrity of audit log hash chain.
    
    Args:
        db: Database session
        start_id: Start verification from this ID (optional)
        limit: Maximum records to verify
    
    Returns:
        Dict with verification results:
        - valid: bool - True if chain is intact
        - records_checked: int - Number of records verified
        - first_broken_id: Optional[int] - ID of first record with broken chain
        - error: Optional[str] - Error description if chain is broken
    """
    try:
        # Build query
        stmt = select(AuditLogModel).order_by(AuditLogModel.id.asc()).limit(limit)
        if start_id:
            stmt = stmt.where(AuditLogModel.id >= start_id)
        
        result = await db.execute(stmt)
        records = result.scalars().all()
        
        if not records:
            return {
                "valid": True,
                "records_checked": 0,
                "first_broken_id": None,
                "error": None
            }
        
        prev_hash = None
        for i, record in enumerate(records):
            # Skip hash verification for records without hash (legacy records)
            if record.record_hash is None:
                prev_hash = None
                continue
            
            # Verify prev_hash matches
            if i > 0 and record.prev_hash != prev_hash:
                return {
                    "valid": False,
                    "records_checked": i + 1,
                    "first_broken_id": record.id,
                    "error": f"Chain broken at ID {record.id}: prev_hash mismatch"
                }
            
            # Verify record_hash
            expected_hash = _compute_record_hash(
                operator_id=record.operator_id,
                action=record.action,
                target_type=record.target_type,
                target_id=record.target_id,
                client_ip=record.client_ip,
                user_agent=record.user_agent,
                details=record.details,
                created_at=record.created_at,
                prev_hash=record.prev_hash
            )
            
            if record.record_hash != expected_hash:
                return {
                    "valid": False,
                    "records_checked": i + 1,
                    "first_broken_id": record.id,
                    "error": f"Record tampered at ID {record.id}: hash mismatch"
                }
            
            prev_hash = record.record_hash
        
        return {
            "valid": True,
            "records_checked": len(records),
            "first_broken_id": None,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Failed to verify audit chain: {e}")
        return {
            "valid": False,
            "records_checked": 0,
            "first_broken_id": None,
            "error": str(e)
        }
