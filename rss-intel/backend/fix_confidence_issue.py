#!/usr/bin/env python3
"""
Fix för string/int jämförelse i image extraction
"""

# Read the current images2.py file
with open('/home/micke/claude-env/rss-intel/backend/app/images2.py', 'r') as f:
    content = f.read()

# Add a safe confidence helper function before the ImageCandidate class
helper_function = '''
def safe_confidence(candidate) -> float:
    """Safely extract confidence as float, handle string values"""
    try:
        conf = getattr(candidate, 'confidence', 0.5)
        if isinstance(conf, str):
            return float(conf)
        return float(conf)
    except (ValueError, TypeError):
        return 0.5

'''

# Find the line where ImageCandidate is defined and insert helper before it
lines = content.split('\n')
new_lines = []
for i, line in enumerate(lines):
    if line.strip().startswith('@dataclass') and i < len(lines)-1 and 'ImageCandidate' in lines[i+1]:
        new_lines.append(helper_function)
    new_lines.append(line)

# Replace the problematic max() calls with safe versions
new_content = '\n'.join(new_lines)

# Replace max(c.confidence for c in all_candidates) with safe versions
new_content = new_content.replace(
    'max(c.confidence for c in all_candidates)',
    'max(safe_confidence(c) for c in all_candidates)'
)

# Write the fixed content
with open('/home/micke/claude-env/rss-intel/backend/app/images2_fixed.py', 'w') as f:
    f.write(new_content)

print("Created fixed version as images2_fixed.py")