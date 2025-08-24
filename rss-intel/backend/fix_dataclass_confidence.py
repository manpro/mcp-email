#!/usr/bin/env python3
"""
Robust fix för string/int confidence problem genom __post_init__
"""
import subprocess

# Get current file content from container
result = subprocess.run(['docker', 'exec', 'rss-backend', 'cat', '/app/app/images2.py'], 
                       capture_output=True, text=True)
content = result.stdout

# Find the ImageCandidate dataclass and add __post_init__ method
lines = content.split('\n')
new_lines = []
in_imagecandidate_class = False
added_post_init = False

for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Check if we're at the ImageCandidate dataclass
    if '@dataclass' in line and i < len(lines)-1 and 'ImageCandidate' in lines[i+1]:
        in_imagecandidate_class = True
    
    # Add __post_init__ after the confidence field definition
    if in_imagecandidate_class and 'confidence: float = 0.5' in line and not added_post_init:
        new_lines.extend([
            '',
            '    def __post_init__(self):',
            '        """Ensure confidence is always a float"""',
            '        if isinstance(self.confidence, str):',
            '            try:',
            '                self.confidence = float(self.confidence)',
            '            except (ValueError, TypeError):',
            '                self.confidence = 0.5',
            '        elif not isinstance(self.confidence, (int, float)):',
            '            self.confidence = 0.5'
        ])
        added_post_init = True
    
    # Exit class detection when we hit the area property
    if in_imagecandidate_class and '@property' in line and 'area' in lines[i+1]:
        in_imagecandidate_class = False

# Write fixed content
with open('/home/micke/claude-env/rss-intel/backend/app/images2_dataclass_fixed.py', 'w') as f:
    f.write('\n'.join(new_lines))

print("Added __post_init__ method to ImageCandidate for automatic confidence conversion")