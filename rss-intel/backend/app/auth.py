"""Simple authentication and user management for RSS Intelligence"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Header, Cookie, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
import hashlib
import secrets

logger = logging.getLogger(__name__)

class UserManager:
    """Simple user management for personalization"""
    
    def __init__(self, db: Session):
        self.db = db
        self._ensure_users_table()
    
    def _ensure_users_table(self):
        """Create users table if it doesn't exist"""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE,
                    password_hash VARCHAR(128),
                    session_token VARCHAR(64),
                    session_expires TIMESTAMPTZ,
                    preferences JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_active TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            # Create default admin user if none exists
            result = self.db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            
            if user_count == 0:
                self._create_default_users()
                
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error setting up users table: {e}")
            self.db.rollback()
    
    def _create_default_users(self):
        """Create default users for testing"""
        default_users = [
            {"username": "owner", "email": "owner@rss-intel.local"},
            {"username": "demo", "email": "demo@rss-intel.local"},
            {"username": "test", "email": "test@rss-intel.local"}
        ]
        
        for user in default_users:
            password_hash = self._hash_password("default123")  # Default password
            
            self.db.execute(text("""
                INSERT INTO users (username, email, password_hash, preferences)
                VALUES (:username, :email, :password_hash, :preferences)
            """), {
                "username": user["username"],
                "email": user["email"], 
                "password_hash": password_hash,
                "preferences": '{"personalization_enabled": true, "boost_factor": 0.3}'
            })
        
        logger.info(f"Created {len(default_users)} default users")
    
    def _hash_password(self, password: str) -> str:
        """Simple password hashing"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and create session"""
        try:
            password_hash = self._hash_password(password)
            
            result = self.db.execute(text("""
                SELECT id, username, email, preferences 
                FROM users 
                WHERE username = :username AND password_hash = :password_hash
            """), {"username": username, "password_hash": password_hash})
            
            user_row = result.fetchone()
            if not user_row:
                return None
            
            # Create session token
            session_token = secrets.token_urlsafe(32)
            session_expires = datetime.now(timezone.utc) + timedelta(days=7)
            
            self.db.execute(text("""
                UPDATE users 
                SET session_token = :token, session_expires = :expires, last_active = NOW()
                WHERE id = :user_id
            """), {
                "token": session_token,
                "expires": session_expires,
                "user_id": user_row.id
            })
            
            self.db.commit()
            
            return {
                "user_id": user_row.id,
                "username": user_row.username,
                "email": user_row.email,
                "session_token": session_token,
                "preferences": user_row.preferences or {}
            }
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user by session token"""
        try:
            result = self.db.execute(text("""
                SELECT id, username, email, preferences
                FROM users 
                WHERE session_token = :token 
                AND session_expires > NOW()
            """), {"token": token})
            
            user_row = result.fetchone()
            if not user_row:
                return None
            
            # Update last active
            self.db.execute(text("""
                UPDATE users SET last_active = NOW() WHERE id = :user_id
            """), {"user_id": user_row.id})
            
            self.db.commit()
            
            return {
                "user_id": user_row.id,
                "username": user_row.username,
                "email": user_row.email,
                "preferences": user_row.preferences or {}
            }
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username (for API compatibility)"""
        try:
            result = self.db.execute(text("""
                SELECT id, username, email, preferences
                FROM users 
                WHERE username = :username
            """), {"username": username})
            
            user_row = result.fetchone()
            if not user_row:
                return None
            
            return {
                "user_id": user_row.id,
                "username": user_row.username,
                "email": user_row.email,
                "preferences": user_row.preferences or {}
            }
            
        except Exception as e:
            logger.error(f"User lookup error: {e}")
            return None
    
    def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]):
        """Update user preferences"""
        try:
            self.db.execute(text("""
                UPDATE users 
                SET preferences = :preferences
                WHERE id = :user_id
            """), {"user_id": user_id, "preferences": preferences})
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Preferences update error: {e}")
            self.db.rollback()

def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
    user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """
    Get current user from various sources:
    1. Authorization header (Bearer token)
    2. Session cookie
    3. X-User-ID header (for development/API)
    4. Default to 'owner' for backward compatibility
    """
    
    # For development - allow direct user_id specification
    if user_id:
        return user_id
    
    # Try authorization header
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        # In a real app, validate JWT token here
        # For now, treat it as session token
        try:
            from .deps import SessionLocal
            db = SessionLocal()
            user_manager = UserManager(db)
            user = user_manager.get_user_by_token(token)
            db.close()
            
            if user:
                return user["username"]
        except Exception as e:
            logger.error(f"Token validation error: {e}")
    
    # Try session cookie
    if session_token:
        try:
            from .deps import SessionLocal
            db = SessionLocal()
            user_manager = UserManager(db)
            user = user_manager.get_user_by_token(session_token)
            db.close()
            
            if user:
                return user["username"]
        except Exception as e:
            logger.error(f"Session validation error: {e}")
    
    # Default to 'owner' for backward compatibility
    return "owner"

def require_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
) -> Dict[str, Any]:
    """Require authentication - returns user info or raises HTTPException"""
    
    user_id = get_current_user(request, authorization, session_token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from .deps import SessionLocal
        db = SessionLocal()
        user_manager = UserManager(db)
        user = user_manager.get_user_by_username(user_id)
        db.close()
        
        if not user:
            # Create user on-the-fly for backward compatibility
            return {"username": user_id, "preferences": {}}
        
        return user
        
    except Exception as e:
        logger.error(f"User lookup error: {e}")
        return {"username": user_id, "preferences": {}}