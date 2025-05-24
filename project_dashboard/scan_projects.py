#!/usr/bin/env python3

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

def read_readme(project_path: str) -> Optional[str]:
    """Extract description from README file."""
    readme_files = ['README.md', 'README.txt', 'README.rst', 'README']
    for readme in readme_files:
        readme_path = os.path.join(project_path, readme)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Get first few lines or first paragraph
                    lines = content.split('\n')
                    description = []
                    for line in lines[:10]:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            description.append(line)
                        if len(description) >= 3:
                            break
                    return ' '.join(description)[:200] if description else None
            except:
                pass
    return None

def detect_project_type(project_path: str, indicators: List[str]) -> str:
    """Detect project type based on files present."""
    if any(f in indicators for f in ['package.json', 'yarn.lock', 'node_modules']):
        return 'Node.js/JavaScript'
    elif any(f in indicators for f in ['requirements.txt', 'setup.py', 'pyproject.toml', 'main.py', 'app.py']):
        return 'Python'
    elif 'Dockerfile' in indicators:
        return 'Docker'
    elif any(f in indicators for f in ['pom.xml', '*.java']):
        return 'Java'
    elif any(f in indicators for f in ['go.mod', '*.go']):
        return 'Go'
    elif any(f in indicators for f in ['Cargo.toml', '*.rs']):
        return 'Rust'
    elif 'index.html' in indicators:
        return 'Web/HTML'
    elif 'Makefile' in indicators:
        return 'C/C++/Make'
    elif '.git' in indicators:
        return 'Git Repository'
    else:
        return 'Unknown'

def scan_directory(base_path: str) -> List[Dict]:
    """Scan a directory for software projects."""
    projects = []
    
    try:
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if not os.path.isdir(item_path) or item.startswith('.'):
                continue
                
            # Check for project indicators
            indicators = []
            project_files = [
                'main.py', 'app.py', 'Dockerfile', 'requirements.txt', 'README.md',
                'pyproject.toml', 'package.json', 'index.html', 'Makefile',
                'pom.xml', 'go.mod', 'Cargo.toml', 'composer.json', 'setup.py'
            ]
            
            # Check for files
            for file in project_files:
                if os.path.exists(os.path.join(item_path, file)):
                    indicators.append(file)
            
            # Check for .git
            if os.path.exists(os.path.join(item_path, '.git')):
                indicators.append('.git')
                
            # Check for code files
            code_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.sh', '.php']
            code_count = 0
            try:
                for root, dirs, files in os.walk(item_path):
                    if len(root.split(os.sep)) - len(item_path.split(os.sep)) > 2:
                        continue  # Don't go too deep
                    for file in files:
                        if any(file.endswith(ext) for ext in code_extensions):
                            code_count += 1
                            if code_count >= 3:  # If we find several code files
                                if 'code_files' not in indicators:
                                    indicators.append('code_files')
                                break
                    if code_count >= 3:
                        break
            except:
                pass
            
            # If we found indicators, this is likely a project
            if indicators:
                description = read_readme(item_path)
                if not description:
                    description = f"Software project ({', '.join(indicators[:3])})"
                
                projects.append({
                    'name': item,
                    'path': item_path,
                    'type': detect_project_type(item_path, indicators),
                    'description': description,
                    'indicators': indicators
                })
                
    except PermissionError:
        pass
    except Exception as e:
        print(f"Error scanning {base_path}: {e}")
    
    return projects

def main():
    print("Scanning for software projects...")
    all_projects = []
    
    # Scan common directories
    search_paths = [
        '/home/micke',
        '/opt',
        '/srv',
        '/mnt',
        '/var/www',
        '/usr/local/src'
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            print(f"Scanning {path}...")
            projects = scan_directory(path)
            all_projects.extend(projects)
    
    # Also scan subdirectories in home
    home_subdirs = [
        '/home/micke/projects',
        '/home/micke/crewai',
        '/home/micke/elpriser-sverige'
    ]
    
    for path in home_subdirs:
        if os.path.exists(path):
            print(f"Scanning {path}...")
            projects = scan_directory(path)
            all_projects.extend(projects)
    
    # Remove duplicates and sort
    seen_paths = set()
    unique_projects = []
    for project in all_projects:
        if project['path'] not in seen_paths:
            seen_paths.add(project['path'])
            unique_projects.append(project)
    
    unique_projects.sort(key=lambda x: x['name'].lower())
    
    # Save to JSON
    output_file = '/home/micke/project_dashboard/projects.json'
    with open(output_file, 'w') as f:
        json.dump(unique_projects, f, indent=2)
    
    print(f"Found {len(unique_projects)} projects")
    print(f"Results saved to {output_file}")
    
    # Print summary
    for project in unique_projects:
        print(f"- {project['name']} ({project['type']}) - {project['path']}")

if __name__ == "__main__":
    main()