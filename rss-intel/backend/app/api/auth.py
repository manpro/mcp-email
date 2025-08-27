"""Authentication API for RSS Intelligence"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Header, Cookie
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_db
from ..auth_simple import SimpleUserManager, get_current_user_simple, require_auth_simple

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: str
    user: Dict[str, Any]
    message: str

class UserPreferences(BaseModel):
    personalization_enabled: bool = True
    boost_factor: float = 0.3
    preferred_sources: list = []
    excluded_topics: list = []

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Secure login with JWT tokens and rate limiting"""
    try:
        # Get client info for security logging
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent", "")
        
        user_manager = SimpleUserManager(db)
        user = user_manager.authenticate_user(
            request.username, 
            request.password, 
            client_ip=client_ip, 
            user_agent=user_agent
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Check if request is HTTPS (forwarded by nginx)
        is_https = (
            http_request.headers.get("x-forwarded-proto") == "https" or
            http_request.url.scheme == "https"
        )
        
        # Set session token as HTTP-only cookie
        response.set_cookie(
            key="session_token",
            value=user["session_token"],
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=is_https,  # Secure only over HTTPS
            samesite="lax",  # Allow cross-port access on same domain
            domain=None  # Let browser determine domain (works for localhost:port)
        )
        
        # Remove sensitive data from response
        user_info = {
            "username": user["username"],
            "email": user["email"],
            "preferences": user["preferences"]
        }
        
        logger.info(f"User {request.username} logged in successfully from {client_ip}")
        
        return LoginResponse(
            status="success",
            user=user_info,
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/logout")
async def logout(response: Response):
    """Logout user and clear session"""
    response.delete_cookie("session_token")
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/me")
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(require_auth_simple)
):
    """Get current user information"""
    return {
        "username": current_user["username"],
        "preferences": current_user.get("preferences", {}),
        "authenticated": True
    }

@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth_simple)
):
    """List available users (for development)"""
    try:
        from sqlalchemy import text
        
        result = db.execute(text("""
            SELECT username, email, created_at, last_active,
                   CASE WHEN session_expires > NOW() THEN true ELSE false END as active_session
            FROM users 
            ORDER BY last_active DESC
        """))
        
        users = []
        for row in result:
            users.append({
                "username": row.username,
                "email": row.email,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "last_active": row.last_active.isoformat() if row.last_active else None,
                "active_session": row.active_session
            })
        
        return {
            "users": users,
            "total": len(users)
        }
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/preferences")
async def update_preferences(
    preferences: UserPreferences,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth_simple)
):
    """Update user preferences"""
    try:
        user_manager = SimpleUserManager(db)
        
        # Update preferences
        user_manager.update_user_preferences(
            current_user["user_id"],
            preferences.dict()
        )
        
        return {
            "status": "success",
            "message": "Preferences updated",
            "preferences": preferences.dict()
        }
        
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def auth_status(
    request: Request,
    authorization: str = Header(None),
    session_token: str = Cookie(None),
    user_id: str = Header(None, alias="X-User-ID")
):
    """Get authentication status without requiring auth"""
    try:
        current_user = get_current_user_simple(request, authorization, session_token, user_id)
        
        return {
            "authenticated": current_user is not None,
            "user_id": current_user,
            "auth_methods": [
                "Authorization header (Bearer token)",
                "HTTP-only cookie (session_token)",
                "X-User-ID header (development only)"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return {
            "authenticated": False,
            "user_id": None,
            "error": str(e)
        }