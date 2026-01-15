
import sys
import os
import traceback

# Add current directory to path
sys.path.append(os.getcwd())

print("--- DEBUG START ---")

try:
    print("1. Importing strategies.StrategyRegistry...")
    from strategies import StrategyRegistry
    print(f"   Success: {len(StrategyRegistry._strategies)} strategies registered.")
    
    print("2. Importing core.scanner.scanner_engine.ScannerEngine...")
    from core.scanner.scanner_engine import ScannerEngine
    print("   Success.")
    
    print("3. Importing services.derivatives_service.DerivativesService...")
    from services.derivatives_service import DerivativesService
    print("   Success.")
    
    print("4. Importing core.scanner.decision_engine.DecisionEngine...")
    from core.scanner.decision_engine import DecisionEngine
    print("   Success.")

    print("5. Instantiating DecisionEngine...")
    de = DecisionEngine()
    print("   Success.")

    print("6. Instantiating DerivativesService...")
    ds = DerivativesService()
    print("   Success.")

    print("7. Instantiating ScannerEngine...")
    # ScannerEngine(decision_engine, derivatives_service, strategy_registry=None)
    se = ScannerEngine(de, ds)
    print("   Success.")

    print("8. Importing get_realtime_scanner_engine...")
    from core.scanner.realtime_scanner_engine import get_realtime_scanner_engine
    print("   Success.")

    print("9. Calling get_realtime_scanner_engine()...")
    rse = get_realtime_scanner_engine()
    print("   Success.")

    print("--- DEBUG FINISHED SUCCESSFULLY ---")

except Exception as e:
    print(f"\n!!! CAUGHT EXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)
