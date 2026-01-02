from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body
from app.core.auth import verify_dashboard_token
from app.repository.audit_repo import AuditLogRepository
from app.repository.settings_repo import SettingsRepository
from app.repository.admin_token_repo import AdminTokenRepository
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Audit Logs ---

@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    _: str = Depends(verify_dashboard_token)
):
    """Get system audit logs."""
    audit_repo = AuditLogRepository()
    logs = await audit_repo.get_logs(limit=limit, offset=offset, user_id=user_id, action=action)
    return {"logs": logs}

# --- Settings ---

@router.get("/settings")
async def get_settings(
    _: str = Depends(verify_dashboard_token)
):
    """Get all system settings."""
    settings_repo = SettingsRepository()
    settings = await settings_repo.get_all_settings()
    # Convert list of dicts to a map for easier frontend consumption
    settings_map = {item["key"]: item["value"] for item in settings}
    return {"settings": settings_map}

@router.post("/settings")
async def update_settings(
    settings_data: Dict[str, Any] = Body(...),
    _: str = Depends(verify_dashboard_token)
):
    """Update system settings."""
    settings_repo = SettingsRepository()
    audit_repo = AuditLogRepository()
    
    updated = await settings_repo.update_settings_bulk(settings_data)
    
    # Log action
    await audit_repo.log_action(
        user_id="admin",
        action="update_settings",
        resource_type="settings",
        details={"updated_keys": list(settings_data.keys())}
    )
    
    return {"status": "success", "updated": len(updated)}

# --- Admin Tokens ---

@router.get("/tokens")
async def get_tokens(
    _: str = Depends(verify_dashboard_token)
):
    """Get all active admin tokens."""
    token_repo = AdminTokenRepository()
    tokens = await token_repo.get_active_tokens()
    # Mask actual tokens for security, only show preview or just metadata
    for t in tokens:
        if t.get("token"):
            t["token_preview"] = t["token"][:8] + "..."
            del t["token"] # Don't send full token back
    return {"tokens": tokens}

@router.post("/tokens")
async def create_token(
    name: str = Body(..., embed=True),
    _: str = Depends(verify_dashboard_token)
):
    """Create a new admin token."""
    token_repo = AdminTokenRepository()
    audit_repo = AuditLogRepository()
    
    token = await token_repo.create_token(name=name, created_by="admin")
    
    await audit_repo.log_action(
        user_id="admin",
        action="create_token",
        resource_type="admin_token",
        resource_id=token["id"],
        details={"name": name}
    )
    
    return {"token": token}

@router.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: str,
    _: str = Depends(verify_dashboard_token)
):
    """Revoke an admin token."""
    token_repo = AdminTokenRepository()
    audit_repo = AuditLogRepository()
    
    success = await token_repo.revoke_token(token_id)
    if not success:
        raise HTTPException(status_code=404, detail="Token not found or failed to revoke")
    
    await audit_repo.log_action(
        user_id="admin",
        action="revoke_token",
        resource_type="admin_token",
        resource_id=token_id
    )
    
    return {"status": "success"}
