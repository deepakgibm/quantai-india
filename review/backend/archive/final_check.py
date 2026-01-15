import os
import sys

# Ensure backend root is in path
backend_root = os.getcwd()
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

print(f"Current Directory: {os.getcwd()}")
print(f"Python Executable: {sys.executable}")
print(f"SYS PATH: {sys.path[:3]}")

try:
    import strategies
    print(f"SUCCESS: strategies module loaded from {strategies.__file__}")
    from strategies import StrategyRegistry
    print(f"StrategyRegistry: {StrategyRegistry}")
    print(f"Registered Strategies: {list(StrategyRegistry._strategies.keys()) if StrategyRegistry else []}")
    print(f"Total Count: {len(StrategyRegistry._strategies) if StrategyRegistry else 0}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
