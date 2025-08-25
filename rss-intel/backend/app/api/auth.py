"""Authentication API for RSS Intelligence"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Header, Cookie
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_db
from ..auth import UserManager, get_current_user, require_auth

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
    db: Session = Depends(get_db)
):
    """Login user and create session"""
    try:
        user_manager = UserManager(db)
        user = user_manager.authenticate_user(request.username, request.password)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Set session cookie
        response.set_cookie(
            key="session_token",
            value=user["session_token"],
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        # Remove sensitive data from response
        user_info = {
            "username": user["username"],
            "email": user["email"],
            "preferences": user["preferences"]
        }
        
        logger.info(f"User {request.username} logged in successfully")
        
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
    current_user: Dict[str, Any] = Depends(require_auth)
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
    current_user: Dict[str, Any] = Depends(require_auth)
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
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Update user preferences"""
    try:
        user_manager = UserManager(db)
        
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
        current_user = get_current_user(request, authorization, session_token, user_id)
        
        return {
            "authenticated": current_user != "owner",  # 'owner' is default fallback
            "user_id": current_user,
            "auth_methods": [
                "Authorization header (Bearer token)",
                "Session cookie",
                "X-User-ID header"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return {
            "authenticated": False,
            "user_id": None,
            "error": str(e)
        }