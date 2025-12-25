import sys
import os
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
    from backend.models_ml import Nifty100Daily
    print("✅ Imported Nifty100Daily successfully")
    
    from backend.models import Nifty100Daily as Nifty100DailyFromModels
    print("✅ Imported Nifty100Daily from models.py successfully")
    
    import yfinance
    print("✅ yfinance is installed")
    
except Exception as e:
    print(f"❌ Error: {e}")
