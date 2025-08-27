"""Simple authentication for RSS Intelligence"""
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, Header, Cookie
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class SimpleUserManager:
    """Simple user manager for basic authentication"""
    
    def __init__(self, db: Session):
        self.db = db
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Create users table if it doesn't exist"""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100),
                    password_hash VARCHAR(60) NOT NULL,
                    session_token VARCHAR(64),
                    session_expires TIMESTAMPTZ,
                    preferences JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_active TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            self.db.commit()
            
            # Ensure test user exists
            self._create_test_user()
        except Exception as e:
            logger.error(f"Failed to create users table: {e}")
            self.db.rollback()
    
    def _create_test_user(self):
        """Create test user if it doesn't exist"""
        try:
            # Check if test user exists
            result = self.db.execute(text("""
                SELECT id FROM users WHERE username = :username
            """), {"username": "test"})
            
            if not result.fetchone():
                # Create test user with plaintext password (for development)
                self.db.execute(text("""
                    INSERT INTO users (username, email, password_hash, preferences)
                    VALUES (:username, :email, :password_hash, :preferences)
                """), {
                    "username": "test",
                    "email": "test@rss-intel.local",
                    "password_hash": "test123",  # Plain text for development
                    "preferences": '{"personalization_enabled": true, "boost_factor": 0.3}'
                })
                self.db.commit()
                logger.info("Created test user")
        except Exception as e:
            logger.error(f"Failed to create test user: {e}")
            self.db.rollback()
    
    def authenticate_user(self, username: str, password: str, client_ip: str = "", user_agent: str = "") -> Optional[Dict[str, Any]]:
        """Authenticate user and create session"""
        try:
            # Get user and compare plaintext password
            result = self.db.execute(text("""
                SELECT id, username, email, password_hash, preferences
                FROM users 
                WHERE username = :username
            """), {"username": username})
            
            user_row = result.fetchone()
            if not user_row:
                logger.warning(f"User {username} not found")
                return None
            
            # Simple plaintext password comparison
            if password != user_row.password_hash:
                logger.warning(f"Password mismatch for {username}: expected '{user_row.password_hash}', got '{password}'")
                return None
            
            # Create session token
            session_token = secrets.token_urlsafe(32)
            session_expires = datetime.now(timezone.utc) + timedelta(days=7)
            
            # Update user session
            self.db.execute(text("""
                UPDATE users 
                SET session_token = :token, 
                    session_expires = :expires, 
                    last_active = NOW()
                WHERE id = :user_id
            """), {
                "token": session_token,
                "expires": session_expires,
                "user_id": user_row.id
            })
            self.db.commit()
            
            return {
                "username": user_row.username,
                "email": user_row.email,
                "session_token": session_token,
                "preferences": user_row.preferences or {}
            }
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self.db.rollback()
            return None
    
    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user by session token"""
        try:
            result = self.db.execute(text("""
                SELECT username, email, preferences
                FROM users 
                WHERE session_token = :token 
                AND session_expires > NOW()
            """), {"token": token})
            
            user_row = result.fetchone()
            if user_row:
                # Update last active
                self.db.execute(text("""
                    UPDATE users 
                    SET last_active = NOW() 
                    WHERE session_token = :token
                """), {"token": token})
                self.db.commit()
                
                return {
                    "username": user_row.username,
                    "email": user_row.email,
                    "preferences": user_row.preferences or {}
                }
            
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None

def get_current_user_simple(
    request: Request,
    authorization: str = None,
    session_token: str = None,
    user_id: str = None
) -> str:
    """Get current user from session token or fallback"""
    
    # Try session token first
    if session_token:
        try:
            from .deps import SessionLocal
            db = SessionLocal()
            
            # Check if session token exists and is valid
            result = db.execute(text("""
                SELECT username FROM users 
                WHERE session_token = :token 
                AND session_expires > NOW()
            """), {"token": session_token})
            
            user_row = result.fetchone()
            db.close()
            
            if user_row:
                return user_row.username
        except Exception as e:
            logger.error(f"Session validation error: {e}")
    
    # Fallback to user_id header (development mode only)
    if user_id and user_id != "owner":
        return user_id
    
    # No valid authentication found
    return None

def require_auth_simple(
    request: Request,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
) -> Dict[str, Any]:
    """Require authentication - returns user info or raises HTTPException"""
    
    user_id = get_current_user_simple(request, authorization, session_token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get full user info if we have a session token
    if session_token:
        try:
            from .deps import SessionLocal
            db = SessionLocal()
            user_manager = SimpleUserManager(db)
            user = user_manager.get_user_by_token(session_token)
            db.close()
            
            if user:
                return user
        except Exception as e:
            logger.error(f"User info retrieval error: {e}")
    
    # Fallback user info
    return {
        "username": user_id,
        "email": f"{user_id}@rss-intel.local",
        "preferences": {"personalization_enabled": True, "boost_factor": 0.3}
    }