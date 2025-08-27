#!/usr/bin/env python3
"""Debug authentication issues"""

import requests
import json

# Test data
login_data = {
    "username": "owner",
    "password": "admin123"
}

# Test against different endpoints
endpoints = [
    "http://localhost:8000/api/auth/login",
    "https://localhost:3002/api/auth/login", 
    "https://rss.manprogroup.com/api/auth/login"
]

for endpoint in endpoints:
    print(f"\n=== Testing {endpoint} ===")
    try:
        if endpoint.startswith("https://localhost"):
            # Local HTTPS with self-signed cert
            response = requests.post(endpoint, json=login_data, verify=False, timeout=10)
        elif endpoint.startswith("https://rss.manprogroup"):
            # External with real SSL
            response = requests.post(endpoint, json=login_data, timeout=10)
        else:
            # HTTP
            response = requests.post(endpoint, json=login_data, timeout=10)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        # Also test status endpoint
        status_endpoint = endpoint.replace("/login", "/status")
        status_resp = requests.get(status_endpoint, verify=False if "localhost" in endpoint else True, timeout=5)
        print(f"Status endpoint: {status_resp.status_code} - {status_resp.text[:100]}...")
        
    except Exception as e:
        print(f"Error: {e}")

print("\n=== Testing database directly ===")
import os
import sys
sys.path.insert(0, '/home/micke/claude-env/rss-intel/backend')

try:
    from sqlalchemy import create_engine, text
    
    DATABASE_URL = "postgresql://rss:changeme@localhost:5432/rssintel"
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT username, password_hash, salt FROM users"))
        print("Database users:")
        for row in result:
            print(f"  {row.username}: hash='{row.password_hash}' salt='{row.salt}'")
except Exception as e:
    print(f"Database test failed: {e}")