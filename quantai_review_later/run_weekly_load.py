import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Remove backend dir from sys.path to prevent top-level imports
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) in sys.path:
    sys.path.remove(str(backend_dir))
# Also remove CWD if it is backend dir
if os.getcwd() == str(backend_dir) and os.getcwd() in sys.path:
    sys.path.remove(os.getcwd())

from backend.etl.weekly_loader import WeeklyLoader

if __name__ == "__main__":
    print("Starting Weekly Loader...")
    asyncio.run(WeeklyLoader().run())
