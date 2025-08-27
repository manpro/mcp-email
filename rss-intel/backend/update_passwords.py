#!/usr/bin/env python3
"""
Script to update user passwords to secure versions with proper salt and hashing
"""

import sys
import hashlib
import secrets
import string
from sqlalchemy import create_engine, text
from app.config import settings

def generate_strong_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def hash_password_pbkdf2(password: str, salt: str) -> str:
    """Hash password with salt using PBKDF2"""
    password_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    hashed = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000)
    return hashed.hex()

def main():
    print("🔒 RSS Intelligence - Password Security Update")
    print("=" * 50)
    
    # Connect to database
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Check if we have the new salt column
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS salt VARCHAR(32)"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS account_locked_until TIMESTAMPTZ"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_password_change TIMESTAMPTZ DEFAULT NOW()"))
            conn.commit()
            print("✅ Database schema updated")
        except Exception as e:
            print(f"⚠️ Schema update warning: {e}")
        
        # Get existing users
        result = conn.execute(text("SELECT id, username, password_hash FROM users WHERE salt IS NULL"))
        users_to_update = result.fetchall()
        
        if not users_to_update:
            print("✅ All users already have secure passwords")
            return
        
        print(f"🔄 Found {len(users_to_update)} users to update")
        
        # Generate new secure passwords
        updated_users = []
        
        for user in users_to_update:
            # Generate strong password
            if user.username == "owner":
                new_password = generate_strong_password(20)
            else:
                new_password = generate_strong_password(16)
            
            # Generate salt and hash
            salt = secrets.token_hex(16)
            password_hash = hash_password_pbkdf2(new_password, salt)
            
            # Update database
            conn.execute(text("""
                UPDATE users 
                SET password_hash = :password_hash, 
                    salt = :salt,
                    last_password_change = NOW(),
                    failed_login_attempts = 0,
                    account_locked_until = NULL
                WHERE id = :user_id
            """), {
                "password_hash": password_hash,
                "salt": salt,
                "user_id": user.id
            })
            
            updated_users.append({
                "username": user.username,
                "password": new_password
            })
            
            print(f"✅ Updated {user.username}")
        
        conn.commit()
        
        print("\n" + "=" * 50)
        print("🔑 NEW SECURE PASSWORDS")
        print("=" * 50)
        
        for user in updated_users:
            print(f"Username: {user['username']}")
            print(f"Password: {user['password']}")
            print("-" * 30)
        
        # Save to file
        try:
            with open("/tmp/rss_intel_secure_passwords.txt", "w") as f:
                f.write("RSS Intelligence - Secure Passwords\n")
                f.write("=" * 50 + "\n")
                f.write("IMPORTANT: Save these passwords securely and delete this file!\n\n")
                
                for user in updated_users:
                    f.write(f"Username: {user['username']}\n")
                    f.write(f"Password: {user['password']}\n")
                    f.write("-" * 30 + "\n")
                
                f.write("\n⚠️  SECURITY NOTES:\n")
                f.write("- These passwords use PBKDF2 hashing with 100,000 iterations\n")
                f.write("- Rate limiting: 5 failed attempts locks account for 1 hour\n")
                f.write("- All authentication events are logged for audit\n")
                f.write("- Session tokens expire after 7 days\n")
                f.write("\n🗑️  DELETE THIS FILE AFTER COPYING PASSWORDS!\n")
            
            print(f"\n💾 Passwords saved to: /tmp/rss_intel_secure_passwords.txt")
            
        except Exception as e:
            print(f"⚠️ Could not save passwords to file: {e}")
        
        print("\n🔒 Password update completed successfully!")
        print("⚠️  IMPORTANT: Update your login credentials immediately!")

if __name__ == "__main__":
    main()