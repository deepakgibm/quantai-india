import sys
import os
sys.path.append(os.getcwd())
try:
    from etl import weekly_loader
    print("Imported weekly_loader")
except Exception as e:
    print(f"Error: {e}")
