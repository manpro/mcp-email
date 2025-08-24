#!/usr/bin/env python3
"""
Fix för string/int jämförelse i sort function
"""

# Read the current images2.py file from container
import subprocess

# Get file content
result = subprocess.run(['docker', 'exec', 'rss-backend', 'cat', '/app/app/images2.py'], 
                       capture_output=True, text=True)
content = result.stdout

# Fix the score_candidate function to use safe_confidence
new_content = content.replace(
    'def score_candidate(c: ImageCandidate) -> Tuple[float, int]:\n            return (c.confidence, c.area)',
    'def score_candidate(c: ImageCandidate) -> Tuple[float, int]:\n            return (safe_confidence(c), c.area)'
)

# Write fixed content to a temp file
with open('/home/micke/claude-env/rss-intel/backend/app/images2_sort_fixed.py', 'w') as f:
    f.write(new_content)

print("Fixed sort function to use safe_confidence")