import os
import re
import json

DIRS = [
    (r"c:\Users\Deepak Kumar\Downloads\quantai-india\backend\routers", ""),
    (r"c:\Users\Deepak Kumar\Downloads\quantai-india\backend\api\v1\endpoints", "/api/v1")
]
OUTPUT_FILE = r"c:\Users\Deepak Kumar\Downloads\quantai-india\docs\api_inventory.json"

# Correct prefix mapping based on main.py audits
prefixes_map = {
    "auth": "/api/auth",
    "heatmap": "/api/heatmap",
    "upstox": "/api/upstox",
    "trading": "/api/trading",
    "ai": "/api/ai",
    "orders": "/api/orders",
    "risk": "/api/risk",
    "settings": "/api/settings",
    "algorithms": "/api/algorithms",
    "agentic_bot": "/api/agentic-bot",
    "engine_performance": "/api/engines",
    "quant_bot": "/api/quant",
    "market": "/api/market",
    "backtest_strategies": "/api/v1/backtest",
    "ml_forecast": "/api/v1/ml",
    "walk_forward_backtest": "/api/v1/walk-forward",
    "experiment_lab": "/api/v1/experiment-lab",
    "etl_status": "/api/v1",
    "analytics": "/api/analytics",
    "hp_scanner_api": "/api/v3/scanner",
    "scanner": "/api/scanner"
}

inventory = []

route_pattern = re.compile(r'@router\.(get|post|put|delete|patch)\("([^"]+)"')
func_pattern = re.compile(r'async def ([a-zA-Z0-9_]+)\(')

for base_dir, base_prefix in DIRS:
    for filename in os.listdir(base_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            name = filename[:-3]
            path = os.path.join(base_dir, filename)
            
            # Determine prefix
            prefix = prefixes_map.get(name, base_prefix)
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    route_match = route_pattern.search(line)
                    if route_match:
                        method = route_match.group(1).upper()
                        route_path = route_match.group(2)
                        
                        full_path = prefix + route_path
                        if full_path.endswith("/") and len(full_path) > 1:
                            full_path = full_path[:-1]
                        
                        handler = "unknown"
                        for j in range(i + 1, min(i + 5, len(lines))):
                            func_match = func_pattern.search(lines[j])
                            if func_match:
                                handler = func_match.group(1)
                                break
                        
                        db_deps = []
                        if "db.execute" in content or "AsyncSession" in content or "Model" in content:
                            db_deps.append("PostgreSQL")
                        
                        cache_deps = []
                        if "cache" in content or "get_cache" in content or "dragonfly" in content:
                            cache_deps.append("Dragonfly/Redis")

                        inventory.append({
                            "api_name": f"{name}_{handler}",
                            "method": method,
                            "path": full_path,
                            "handler": f"{name}.{handler}",
                            "request_schema": {},
                            "response_schema": {},
                            "database_dependencies": db_deps,
                            "cache_dependencies": cache_deps,
                            "expected_response_time_ms": None,
                            "notes": f"File: {filename}"
                        })

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(inventory, f, indent=2)

print(f"Final discovery: {len(inventory)} APIs")
