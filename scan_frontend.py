
import os
import re
import json

FRONTEND_DIR = r"c:\Users\Deepak Kumar\Downloads\quantai-india"
EXTENSIONS = {'.ts', '.tsx', '.js', '.jsx'}

# Regex to match imports:
# import XYZ from 'path'
# import { X, Y as Z } from 'path'
# import * as A from 'path'
IMPORT_REGEX = re.compile(r'import\s+(?:(\*\s+as\s+\w+)|({[\s\w,]+})|([\w]+))\s+from\s+[\'"]([^\'"]+)[\'"]')
# Regex to match variable usage (simple word match)
WORD_REGEX = re.compile(r'\b(\w+)\b')

def scan_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple strategy:
    # 1. Parse all imported names
    # 2. Check if they appear > 1 time in the file (once is the import itself)
    # This is rough but catches strict unused cases.
    
    unused = []
    
    # Normalize content: remove comments? (Skip for simplicity, risk of false negative is acceptable, risk of false positive is main concern)
    # If we find "X" in a comment, we might think it's used. That's safer than deleting used code.
    
    for match in IMPORT_REGEX.finditer(content):
        full_match = match.group(0)
        star_import = match.group(1) # * as A
        destructured = match.group(2) # { X, Y }
        default_import = match.group(3) # React
        
        imported_names = []
        if star_import:
            imported_names.append(star_import.split('as')[1].strip())
        elif default_import:
            imported_names.append(default_import.strip())
        elif destructured:
            # Handle { X, Y as Z }
            items = destructured.replace('{', '').replace('}', '').split(',')
            for item in items:
                item = item.strip()
                if not item: continue
                if ' as ' in item:
                    imported_names.append(item.split(' as ')[1].strip())
                else:
                    imported_names.append(item)
                    
        for name in imported_names:
            # Count occurrences in the whole file
            # If occurrences == 1 (the import definition), it's potentially unused
            # Be careful with `React` which might be implicit in older JSX but this is Vite/React18+ likely
            if name == 'React': continue # Skip React import check
            
            # Use regex to count word boundaries
            escaped_name = re.escape(name)
            pattern = re.compile(fr'\b{escaped_name}\b')
            count = len(pattern.findall(content))
            
            if count <= 1:
                unused.append({
                    "file": filepath,
                    "import": name,
                    "line": content[:match.start()].count('\n') + 1
                })
                
    return unused

results = []
for root, _, files in os.walk(FRONTEND_DIR):
    if 'node_modules' in root or '.git' in root or 'dist' in root or '.venv' in root or 'backend' in root:
        continue
    for file in files:
        if os.path.splitext(file)[1] in EXTENSIONS:
            path = os.path.join(root, file)
            results.extend(scan_file(path))

print(json.dumps(results, indent=2))
