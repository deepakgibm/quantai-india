from dotenv import load_dotenv
from pathlib import Path

def verify_algorithms():
    env_path = Path("backend/.env")
    load_dotenv(env_path)
    
    # We'll use the local backend URL
    url = "http://localhost:8000/api/v1/forecast/algorithms"
    
    # We need a token. Since I don't have a valid user token in the script, 
    # I'll check if the backend is reachable and handle the response.
    # In a real scenario, I might need to mock auth or use a test user.
    # However, since I'm on the machine, I can also check via Python code
    # by importing the registry directly.
    
    import sys
    sys.path.insert(0, str(Path("backend").absolute()))
    
    try:
        from ml.algorithm_registry import get_algorithm_registry
        registry = get_algorithm_registry()
        
        # Test the synchronous part of list_all (without DB first)
        import asyncio
        
        async def run_test():
            algos = await registry.list_all()
            print(f"Found {len(algos)} algorithms in registry:")
            for a in algos:
                print(f" - {a.id}: {a.name} (Recommended: {a.recommended})")
            
            if len(algos) == 4:
                print("[SUCCESS] All 4 algorithms are registered.")
            else:
                print(f"[WARNING] Expected 4 algorithms, found {len(algos)}.")

        asyncio.run(run_test())
        
    except Exception as e:
        print(f"Error verifying algorithms: {e}")

if __name__ == "__main__":
    verify_algorithms()
