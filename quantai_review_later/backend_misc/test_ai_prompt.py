"""Quick test for AI prompt endpoint"""
import asyncio
import httpx
import json

async def test_ai_prompt():
    base_url = "http://localhost:8000"
    
    # First, login to get a token
    print("1. Logging in...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        login_response = await client.post(
            f"{base_url}/api/auth/login",
            json={"email": "demo@example.com", "password": "demo123"}
        )
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code}")
            print(login_response.text)
            return
        
        token_data = login_response.json()
        token = token_data.get("access_token")
        print(f"Login successful, token: {token[:20]}...")
        
        # Test AI prompt endpoint
        print("\n2. Testing /api/ai/prompt...")
        try:
            prompt_response = await client.post(
                f"{base_url}/api/ai/prompt",
                json={"prompt": "Find top 3 stocks to buy today"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=120.0
            )
            
            print(f"Status: {prompt_response.status_code}")
            if prompt_response.status_code == 200:
                data = prompt_response.json()
                print("Success!")
                print(json.dumps(data, indent=2, default=str)[:3000])
            else:
                print(f"Error: {prompt_response.text}")
        except Exception as e:
            print(f"Request failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_prompt())
