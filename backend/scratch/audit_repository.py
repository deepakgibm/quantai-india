import os
import ast
import re
from collections import defaultdict

def scan_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        if 'venv' in root or '.git' in root or '__pycache__' in root or 'scratch' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files

def parse_imports(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()
    
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports

def detect_cycles(graph):
    visited = {}
    path = []
    cycles = []
    
    def dfs(node):
        if node in visited:
            if visited[node] == 1: # in current path
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
            return
        
        visited[node] = 1
        path.append(node)
        
        for neighbor in graph[node]:
            dfs(neighbor)
            
        path.pop()
        visited[node] = 2 # fully processed

    for node in list(graph.keys()):
        dfs(node)
        
    return cycles

def main():
    backend_dir = os.path.abspath('backend')
    files = scan_files(backend_dir)
    print(f"Scanned {len(files)} Python files in backend.")
    
    # 1. Dependency Graph & Circular Imports
    graph = defaultdict(set)
    file_to_module = {}
    for f in files:
        rel_path = os.path.relpath(f, backend_dir)
        module_name = rel_path.replace('.py', '').replace(os.sep, '.')
        if module_name.endswith('.__init__'):
            module_name = module_name[:-9]
        file_to_module[module_name] = rel_path
    
    for f in files:
        rel_path = os.path.relpath(f, backend_dir)
        module_name = rel_path.replace('.py', '').replace(os.sep, '.')
        if module_name.endswith('.__init__'):
            module_name = module_name[:-9]
            
        imports = parse_imports(f)
        for imp in imports:
            # Match imports to local modules
            for local_mod in file_to_module:
                if imp == local_mod or imp.startswith(local_mod + '.'):
                    graph[module_name].add(local_mod)
                    
    cycles = detect_cycles(graph)
    if cycles:
        print(f"\n[Warning] Found {len(cycles)} circular dependencies:")
        for cycle in cycles[:5]:
            print(" -> ".join(cycle))
    else:
        print("\n[Success] No circular dependencies detected in local imports.")
        
    # 2. Dead Code / Unimported Files Candidate
    all_local_targets = set(file_to_module.keys())
    imported_targets = set()
    for mod, neighbors in graph.items():
        for n in neighbors:
            imported_targets.add(n)
            
    # Exclude main entry points, routers, migrations
    exclude_prefixes = ['main', 'api.', 'tests.', 'alembic', 'scripts.', 'scratch.']
    dead_candidates = []
    for mod in all_local_targets:
        if mod not in imported_targets:
            # Check exclusions
            is_excluded = False
            for prefix in exclude_prefixes:
                if mod == prefix or mod.startswith(prefix):
                    is_excluded = True
                    break
            if not is_excluded:
                dead_candidates.append(file_to_module[mod])
                
    print(f"\nFound {len(dead_candidates)} potential dead code file candidates:")
    for cand in sorted(dead_candidates):
         print(f" - {cand}")

    # 3. Duplicate Indicator Searches
    print("\nScanning for duplicate indicator definitions:")
    indicator_keywords = ['def calculate_atr', 'def calculate_rsi', 'def calculate_sma', 'def calculate_ema', 'def compute_atr']
    indicators_found = defaultdict(list)
    for f in files:
        with open(f, 'r', encoding='utf-8', errors='ignore') as file_obj:
            content = file_obj.read()
        for kw in indicator_keywords:
            if kw in content:
                rel_path = os.path.relpath(f, backend_dir)
                indicators_found[kw].append(rel_path)
                
    for kw, paths in indicators_found.items():
        print(f" Keyword '{kw}' found in:")
        for p in paths:
            print(f"  - {p}")

if __name__ == '__main__':
    main()
