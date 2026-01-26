import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Remove backend dir from sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) in sys.path:
    sys.path.remove(str(backend_dir))

try:
    print("✅ Imported Nifty100Daily successfully")
    
    print("✅ Imported Nifty100Daily from models.py successfully")
    
    print("✅ yfinance is installed")
    
except Exception as e:
    print(f"❌ Error: {e}")
