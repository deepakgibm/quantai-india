
import asyncio
from backend.utils.auth import verify_password_async

async def test_auth():
    hashed = "$2b$12$0XyI06n5fG9H/MIF7MCCyFiXVClsv6lMmavwAI"
    plain = "admin123"
    print(f"Testing verify_password_async for {plain}...")
    try:
        result = await verify_password_async(plain, hashed)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Verification crashed: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_auth())
