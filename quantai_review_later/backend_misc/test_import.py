import sys
import os
sys.path.append(os.getcwd())
print(f"Sys path: {sys.path}")
try:
    print("Imported models_alpha")
except Exception as e:
    print(f"Error: {e}")
