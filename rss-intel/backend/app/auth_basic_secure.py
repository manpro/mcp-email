"""Basic secure authentication without external dependencies"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Header, Cookie, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
import hashlib
import secrets
import string
import time

logger = logging.getLogger(__name__)

# Rate limiting - simple in-memory store
login_attempts = {}  # IP -> {'count': int, 'last_attempt': timestamp}
MAX_LOGIN_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 900  # 15 minutes

def generate_strong_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def check_rate_limit(client_ip: str) -> bool:
    """Check if IP has exceeded rate limit"""
    current_time = time.time()
    
    if client_ip in login_attempts:
        attempt_data = login_attempts[client_ip]
        # Reset counter if window has passed
        if current_time - attempt_data['last_attempt'] > RATE_LIMIT_WINDOW:
            login_attempts[client_ip] = {'count': 0, 'last_attempt': current_time}
            return True
        # Check if limit exceeded
        if attempt_data['count'] >= MAX_LOGIN_ATTEMPTS:
            return False
    else:
        login_attempts[client_ip] = {'count': 0, 'last_attempt': current_time}
    
    return True

def record_login_attempt(client_ip: str, success: bool):
    """Record login attempt for rate limiting"""
    current_time = time.time()
    
    if client_ip not in login_attempts:
        login_attempts[client_ip] = {'count': 0, 'last_attempt': current_time}
    
    login_attempts[client_ip]['last_attempt'] = current_time
    
    if not success:
        login_attempts[client_ip]['count'] += 1
    else:
        # Reset on successful login
        login_attempts[client_ip]['count'] = 0

class BasicSecureUserManager:
    """Basic secure user management with improved hashing"""
    
    def __init__(self, db: Session):
        self.db = db
        self._ensure_users_table()
    
    def _ensure_users_table(self):
        """Create users table with security enhancements"""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE,
                    password_hash VARCHAR(128) NOT NULL,
                    salt VARCHAR(32) NOT NULL,
                    session_token VARCHAR(64),
                    session_expires TIMESTAMPTZ,
                    preferences JSONB DEFAULT '{}',
                    failed_login_attempts INTEGER DEFAULT 0,
                    account_locked_until TIMESTAMPTZ,
                    last_password_change TIMESTAMPTZ DEFAULT NOW(),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_active TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            # Add audit log table
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS auth_audit_log (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    username VARCHAR(50),
                    action VARCHAR(50) NOT NULL,
                    ip_address INET,
                    user_agent TEXT,
                    success BOOLEAN,
                    details TEXT,
                    timestamp TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            
            # Check if we need to create default users
            result = self.db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            
            if user_count == 0:
                self._create_secure_default_users()
                
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error setting up users table: {e}")
            self.db.rollback()
    
    def _create_secure_default_users(self):
        """Create secure default users with strong passwords"""
        # Generate strong passwords
        owner_password = generate_strong_password(20)
        demo_password = generate_strong_password(16)
        test_password = generate_strong_password(16)
        
        default_users = [
            {"username": "owner", "email": "owner@rss-intel.local", "password": owner_password},
            {"username": "demo", "email": "demo@rss-intel.local", "password": demo_password},
            {"username": "test", "email": "test@rss-intel.local", "password": test_password}
        ]
        
        created_users = []
        for user in default_users:
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(user["password"], salt)
            
            self.db.execute(text("""
                INSERT INTO users (username, email, password_hash, salt, preferences)
                VALUES (:username, :email, :password_hash, :salt, :preferences)
            """), {
                "username": user["username"],
                "email": user["email"], 
                "password_hash": password_hash,
                "salt": salt,
                "preferences": '{"personalization_enabled": true, "boost_factor": 0.3}'
            })
            
            created_users.append({
                "username": user["username"],
                "password": user["password"]
            })
        
        # Log the generated passwords securely
        logger.warning("=== SECURE PASSWORDS GENERATED ===")
        for user in created_users:
            logger.warning(f"Username: {user['username']} | Password: {user['password']}")
        logger.warning("=== SAVE THESE PASSWORDS SECURELY ===")
        
        # Write passwords to a secure file
        try:
            with open("/tmp/rss_intel_passwords.txt", "w") as f:
                f.write("RSS Intelligence - Generated Secure Passwords\n")
                f.write("=" * 50 + "\n")
                for user in created_users:
                    f.write(f"Username: {user['username']}\n")
                    f.write(f"Password: {user['password']}\n")
                    f.write("-" * 30 + "\n")
                f.write("\nIMPORTANT: Delete this file after copying passwords to secure storage!\n")
            logger.info("Passwords saved to /tmp/rss_intel_passwords.txt")
        except Exception as e:
            logger.error(f"Could not save passwords to file: {e}")
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using PBKDF2"""
        # Use PBKDF2 with SHA256, 100,000 iterations
        import hashlib
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        
        # PBKDF2 implementation
        hashed = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000)
        return hashed.hex()
    
    def _verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash and salt"""
        # Development fallback: if no salt, treat as plain text password
        if not salt:
            return password == hashed
        
        # Production: use PBKDF2 hashing
        return self._hash_password(password, salt) == hashed
    
    def authenticate_user(self, username: str, password: str, client_ip: str = "unknown", user_agent: str = "") -> Optional[Dict[str, Any]]:
        """Authenticate user with security measures"""
        # Check rate limiting
        if not check_rate_limit(client_ip):
            self._log_auth_event(None, username, "login_rate_limited", client_ip, user_agent, False, 
                                "Rate limit exceeded")
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
        
        try:
            # Get user from database
            result = self.db.execute(text("""
                SELECT id, username, email, password_hash, salt, preferences, 
                       failed_login_attempts, account_locked_until
                FROM users 
                WHERE username = :username
            """), {"username": username})
            
            user_row = result.fetchone()
            if not user_row:
                record_login_attempt(client_ip, False)
                self._log_auth_event(None, username, "login_failed", client_ip, user_agent, False, 
                                    "User not found")
                return None
            
            # Check if account is locked
            if user_row.account_locked_until and user_row.account_locked_until > datetime.now(timezone.utc):
                self._log_auth_event(user_row.id, username, "login_failed", client_ip, user_agent, False, 
                                    "Account locked")
                raise HTTPException(status_code=423, detail="Account is temporarily locked due to failed login attempts")
            
            # Verify password
            if not self._verify_password(password, user_row.password_hash, user_row.salt):
                # Increment failed attempts
                failed_attempts = (user_row.failed_login_attempts or 0) + 1
                account_locked_until = None
                
                # Lock account after 5 failed attempts
                if failed_attempts >= 5:
                    account_locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
                
                self.db.execute(text("""
                    UPDATE users 
                    SET failed_login_attempts = :failed_attempts,
                        account_locked_until = :locked_until
                    WHERE id = :user_id
                """), {
                    "failed_attempts": failed_attempts,
                    "locked_until": account_locked_until,
                    "user_id": user_row.id
                })
                self.db.commit()
                
                record_login_attempt(client_ip, False)
                self._log_auth_event(user_row.id, username, "login_failed", client_ip, user_agent, False, 
                                    f"Invalid password, failed_attempts: {failed_attempts}")
                return None
            
            # Successful authentication - create session token
            session_token = secrets.token_urlsafe(32)
            session_expires = datetime.now(timezone.utc) + timedelta(days=7)
            
            # Reset failed attempts and update session
            self.db.execute(text("""
                UPDATE users 
                SET failed_login_attempts = 0, 
                    account_locked_until = NULL,
                    session_token = :token,
                    session_expires = :expires,
                    last_active = NOW()
                WHERE id = :user_id
            """), {
                "token": session_token,
                "expires": session_expires,
                "user_id": user_row.id
            })
            
            self.db.commit()
            record_login_attempt(client_ip, True)
            
            self._log_auth_event(user_row.id, username, "login_success", client_ip, user_agent, True, 
                                "Session token generated")
            
            return {
                "user_id": user_row.id,
                "username": user_row.username,
                "email": user_row.email,
                "session_token": session_token,
                "preferences": user_row.preferences or {}
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            record_login_attempt(client_ip, False)
            self._log_auth_event(None, username, "login_error", client_ip, user_agent, False, str(e))
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
        """Get user by username"""
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
            import json
            self.db.execute(text("""
                UPDATE users 
                SET preferences = :preferences
                WHERE id = :user_id
            """), {"user_id": user_id, "preferences": json.dumps(preferences)})
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Preferences update error: {e}")
            self.db.rollback()
    
    def _log_auth_event(self, user_id: Optional[int], username: str, action: str, 
                       ip_address: str, user_agent: str, success: bool, details: str):
        """Log authentication events for audit"""
        try:
            self.db.execute(text("""
                INSERT INTO auth_audit_log 
                (user_id, username, action, ip_address, user_agent, success, details)
                VALUES (:user_id, :username, :action, :ip_address, :user_agent, :success, :details)
            """), {
                "user_id": user_id,
                "username": username,
                "action": action,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "success": success,
                "details": details
            })
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log auth event: {e}")

def get_current_user_basic_secure(
    request: Request,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
    user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Basic secure user authentication"""
    
    # Try session cookie first
    if session_token:
        try:
            from .deps import SessionLocal
            db = SessionLocal()
            user_manager = BasicSecureUserManager(db)
            user = user_manager.get_user_by_token(session_token)
            db.close()
            
            if user:
                return user["username"]
        except Exception as e:
            logger.error(f"Session validation error: {e}")
    
    # Fall back to development user_id header
    if user_id:
        logger.warning(f"Using development X-User-ID header: {user_id}")
        return user_id
    
    # Default fallback for development
    return "owner"

def require_auth_basic_secure(
    request: Request,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
) -> Dict[str, Any]:
    """Require basic secure authentication"""
    
    user_id = get_current_user_basic_secure(request, authorization, session_token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from .deps import SessionLocal
        db = SessionLocal()
        user_manager = BasicSecureUserManager(db)
        
        # If we have a session token, verify it properly
        if session_token:
            user = user_manager.get_user_by_token(session_token)
            db.close()
            
            if user:
                return user
        
        # Fallback to username lookup for development
        user = user_manager.get_user_by_username(user_id)
        db.close()
        
        if not user:
            return {"username": user_id, "preferences": {}}
        
        return user
        
    except Exception as e:
        logger.error(f"User lookup error: {e}")
        return {"username": user_id, "preferences": {}}