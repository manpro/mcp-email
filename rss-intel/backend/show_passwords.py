#!/usr/bin/env python3
"""Show current user passwords and reset if needed"""

import os
import sys
import secrets
import string
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def generate_password(length=12):
    """Generate a simple password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def main():
    # Get database connection
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://rss:changeme@postgres:5432/rssintel')
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check what passwords are currently set
        print("=== Current User Status ===")
        result = db.execute(text("SELECT username, password_hash, salt FROM users ORDER BY username"))
        users_data = []
        for row in result:
            users_data.append({
                'username': row.username,
                'has_hash': bool(row.password_hash),
                'has_salt': bool(row.salt)
            })
            print(f"User: {row.username} - Hash: {'✓' if row.password_hash else '✗'} Salt: {'✓' if row.salt else '✗'}")
        
        print("\n=== Setting Simple Passwords ===")
        
        # Set simple passwords for testing
        simple_passwords = {
            'owner': 'admin123',
            'demo': 'demo123', 
            'test': 'test123'
        }
        
        for username, password in simple_passwords.items():
            # Update with plain text password (temporary for testing)
            db.execute(text("""
                UPDATE users 
                SET password_hash = :password, salt = NULL 
                WHERE username = :username
            """), {"password": password, "username": username})
            print(f"Set password for {username}: {password}")
        
        db.commit()
        print("\n=== Login Credentials ===")
        for username, password in simple_passwords.items():
            print(f"{username}: {password}")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()