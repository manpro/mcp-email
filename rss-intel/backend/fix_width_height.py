#!/usr/bin/env python3
"""
Fix för width/height som också kan vara strings
"""
import subprocess

# Get current file content from container
result = subprocess.run(['docker', 'exec', 'rss-backend', 'cat', '/app/app/images2.py'], 
                       capture_output=True, text=True)
content = result.stdout

# Find the __post_init__ method and enhance it to handle width/height
lines = content.split('\n')
new_lines = []
in_post_init = False

for i, line in enumerate(lines):
    if 'def __post_init__(self):' in line:
        in_post_init = True
        new_lines.append(line)
        new_lines.append('        """Ensure confidence, width, and height are correct types"""')
        # Skip the old docstring
        if i + 1 < len(lines) and '"""' in lines[i + 1]:
            continue
    elif in_post_init and line.strip().startswith('elif not isinstance(self.confidence'):
        # Add width and height conversion before the confidence elif
        new_lines.extend([
            '        ',
            '        # Convert width and height to int if they are strings',
            '        if isinstance(self.width, str):',
            '            try:',
            '                self.width = int(self.width) if self.width else None',
            '            except (ValueError, TypeError):',
            '                self.width = None',
            '        ',
            '        if isinstance(self.height, str):',
            '            try:',
            '                self.height = int(self.height) if self.height else None', 
            '            except (ValueError, TypeError):',
            '                self.height = None',
            line
        ])
        in_post_init = False
    else:
        new_lines.append(line)

# Write fixed content
with open('/home/micke/claude-env/rss-intel/backend/app/images2_width_height_fixed.py', 'w') as f:
    f.write('\n'.join(new_lines))

print("Enhanced __post_init__ to handle width/height conversion")