"""Test AI with output to file"""
import asyncio
import httpx

async def test():
    base_url = "http://localhost:8000"
    output_file = "ai_test_result.txt"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Login
        login = await client.post(f"{base_url}/api/auth/login", json={"email": "demo@example.com", "password": "demo123"})
        token = login.json().get("access_token")
        
        # Test AI endpoint
        resp = await client.post(
            f"{base_url}/api/ai/prompt",
            json={"prompt": "Find top 3 stocks to buy today"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Status: {resp.status_code}\n\n")
            f.write(f"Response:\n{resp.text}\n")
        
        print(f"Status {resp.status_code} - Written to {output_file}")

asyncio.run(test())
