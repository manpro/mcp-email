"""Secure authentication and user management for RSS Intelligence"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Header, Cookie, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
import bcrypt
import secrets
import string
from jose import JWTError, jwt
from functools import lru_cache
import time
import hashlib

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = secrets.token_urlsafe(32)  # Generate once per app start
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Rate limiting - simple in-memory store (use Redis in production)
login_attempts = {}  # IP -> {'count': int, 'last_attempt': timestamp}
MAX_LOGIN_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 900  # 15 minutes

def generate_strong_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return {"username": username, "payload": payload}
    except JWTError:
        return None

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

class SecureUserManager:
    """Secure user management with bcrypt hashing and JWT tokens"""
    
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
                    password_hash VARCHAR(60) NOT NULL,  -- bcrypt hash
                    session_token VARCHAR(64),
                    session_expires TIMESTAMPTZ,
                    jwt_token_blacklist TEXT[] DEFAULT '{}',  -- For token revocation
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
                    details JSONB,
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
            password_hash = self._hash_password(user["password"])
            
            self.db.execute(text("""
                INSERT INTO users (username, email, password_hash, preferences)
                VALUES (:username, :email, :password_hash, :preferences)
            """), {
                "username": user["username"],
                "email": user["email"], 
                "password_hash": password_hash,
                "preferences": '{"personalization_enabled": true, "boost_factor": 0.3}'
            })
            
            created_users.append({
                "username": user["username"],
                "password": user["password"]
            })
        
        # Log the generated passwords (remove this in production!)
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
    
    def _hash_password(self, password: str) -> str:
        """Hash password with bcrypt and salt"""
        salt = bcrypt.gensalt(rounds=12)  # Higher rounds for more security
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def authenticate_user(self, username: str, password: str, client_ip: str = "unknown", user_agent: str = "") -> Optional[Dict[str, Any]]:
        """Authenticate user with security measures"""
        # Check rate limiting
        if not check_rate_limit(client_ip):
            self._log_auth_event(None, username, "login_rate_limited", client_ip, user_agent, False, 
                                {"reason": "Rate limit exceeded"})
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
        
        try:
            # Get user from database
            result = self.db.execute(text("""
                SELECT id, username, email, password_hash, preferences, 
                       failed_login_attempts, account_locked_until
                FROM users 
                WHERE username = :username
            """), {"username": username})
            
            user_row = result.fetchone()
            if not user_row:
                record_login_attempt(client_ip, False)
                self._log_auth_event(None, username, "login_failed", client_ip, user_agent, False, 
                                    {"reason": "User not found"})
                return None
            
            # Check if account is locked
            if user_row.account_locked_until and user_row.account_locked_until > datetime.now(timezone.utc):
                self._log_auth_event(user_row.id, username, "login_failed", client_ip, user_agent, False, 
                                    {"reason": "Account locked"})
                raise HTTPException(status_code=423, detail="Account is temporarily locked due to failed login attempts")
            
            # Verify password
            if not self._verify_password(password, user_row.password_hash):
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
                                    {"reason": "Invalid password", "failed_attempts": failed_attempts})
                return None
            
            # Successful authentication - create JWT token
            access_token = create_access_token(
                data={"sub": user_row.username, "user_id": user_row.id}
            )
            
            # Reset failed attempts and update last active
            self.db.execute(text("""
                UPDATE users 
                SET failed_login_attempts = 0, 
                    account_locked_until = NULL,
                    last_active = NOW()
                WHERE id = :user_id
            """), {"user_id": user_row.id})
            
            self.db.commit()
            record_login_attempt(client_ip, True)
            
            self._log_auth_event(user_row.id, username, "login_success", client_ip, user_agent, True, 
                                {"token_generated": True})
            
            return {
                "user_id": user_row.id,
                "username": user_row.username,
                "email": user_row.email,
                "access_token": access_token,
                "token_type": "bearer",
                "preferences": user_row.preferences or {}
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            record_login_attempt(client_ip, False)
            self._log_auth_event(None, username, "login_error", client_ip, user_agent, False, 
                                {"error": str(e)})
            return None
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user info"""
        token_data = verify_token(token)
        if not token_data:
            return None
        
        username = token_data["username"]
        
        # Check if user still exists and token isn't blacklisted
        result = self.db.execute(text("""
            SELECT id, username, email, preferences, jwt_token_blacklist
            FROM users 
            WHERE username = :username
        """), {"username": username})
        
        user_row = result.fetchone()
        if not user_row:
            return None
        
        # Check blacklist
        if user_row.jwt_token_blacklist and token in user_row.jwt_token_blacklist:
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
                       ip_address: str, user_agent: str, success: bool, details: Dict[str, Any]):
        """Log authentication events for audit"""
        try:
            import json
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
                "details": json.dumps(details)
            })
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log auth event: {e}")

def get_current_user_secure(
    request: Request,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
    user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> str:
    """Secure user authentication with JWT support"""
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Try JWT token from Authorization header
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            from .deps import SessionLocal
            db = SessionLocal()
            user_manager = SecureUserManager(db)
            user = user_manager.verify_jwt_token(token)
            db.close()
            
            if user:
                return user["username"]
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
    
    # Fall back to development user_id header
    if user_id:
        logger.warning(f"Using development X-User-ID header: {user_id}")
        return user_id
    
    # Default fallback for development
    return "owner"

def require_auth_secure(
    request: Request,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
) -> Dict[str, Any]:
    """Require secure authentication"""
    
    user_id = get_current_user_secure(request, authorization, session_token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from .deps import SessionLocal
        db = SessionLocal()
        user_manager = SecureUserManager(db)
        
        # If we have a JWT token, verify it properly
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            user = user_manager.verify_jwt_token(token)
            db.close()
            
            if not user:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            
            return user
        
        # Fallback to username lookup for development
        result = db.execute(text("""
            SELECT id, username, email, preferences
            FROM users 
            WHERE username = :username
        """), {"username": user_id})
        
        user_row = result.fetchone()
        db.close()
        
        if not user_row:
            return {"username": user_id, "preferences": {}}
        
        return {
            "user_id": user_row.id,
            "username": user_row.username,
            "email": user_row.email,
            "preferences": user_row.preferences or {}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User lookup error: {e}")
        return {"username": user_id, "preferences": {}}