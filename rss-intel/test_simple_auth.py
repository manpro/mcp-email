#!/usr/bin/env python3
"""Simple authentication test without dependencies"""

import os
import sys
import requests

# Test the simplest possible login
login_data = {
    "username": "owner", 
    "password": "admin123"
}

print("=== Testing simple authentication ===")

# Test direct to backend
backend_url = "http://localhost:8000/api/auth/login"
print(f"Testing backend directly: {backend_url}")

try:
    response = requests.post(backend_url, json=login_data, timeout=5)
    print(f"Backend response: {response.status_code}")
    print(f"Response text: {response.text}")
    
    if response.status_code == 200:
        print("✅ Backend authentication WORKS!")
    else:
        print("❌ Backend authentication FAILED")
        
        # Test with different combinations
        test_cases = [
            {"username": "owner", "password": "admin123"},
            {"username": "demo", "password": "demo123"},
            {"username": "test", "password": "test123"},
            {"username": "owner", "password": "default123"},
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"Testing case {i+1}: {test_case}")
            test_response = requests.post(backend_url, json=test_case, timeout=5)
            print(f"  Status: {test_response.status_code}, Response: {test_response.text}")
            
except Exception as e:
    print(f"Backend test failed: {e}")

print("\n=== Testing via nginx proxy ===")
# Test through nginx
nginx_url = "https://localhost:3002/api/auth/login"
print(f"Testing nginx: {nginx_url}")

try:
    response = requests.post(nginx_url, json=login_data, verify=False, timeout=5)
    print(f"Nginx response: {response.status_code}")
    print(f"Response text: {response.text}")
    
    if response.status_code == 200:
        print("✅ Nginx authentication WORKS!")
    else:
        print("❌ Nginx authentication FAILED")
        
except Exception as e:
    print(f"Nginx test failed: {e}")

print("\n=== Testing database directly ===")
# Test database content
try:
    import subprocess
    result = subprocess.run([
        "docker-compose", "exec", "-T", "backend", "python", "-c",
        """
from sqlalchemy import create_engine, text
import os
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("SELECT username, password_hash, salt FROM users"))
    for row in result:
        print(f"User: {row.username}, Hash: '{row.password_hash}', Salt: '{row.salt}'")
        """
    ], capture_output=True, text=True)
    
    print("Database content:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
        
except Exception as e:
    print(f"Database test failed: {e}")