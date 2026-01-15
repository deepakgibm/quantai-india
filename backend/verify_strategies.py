import httpx
import asyncio

URL = "http://localhost:8000/api/scanner/strategies"

async def check_strategies():
    print(f"Checking {URL}...")
    # Authentication likely required? Endpoint depends on get_current_user
    # I need a token.
    # I will try without token first (to see 401).
    # Then I will login and retry.
    
    async with httpx.AsyncClient() as client:
        # 1. Login
        email = "superuser@example.com"
        pwd = "superuser123"
        print(f"Logging in as {email}...")
        
        auth_resp = await client.post("http://localhost:8000/api/auth/login", json={
            "email": email, "password": pwd
        })
        
        if auth_resp.status_code != 200:
            print(f"Login failed ({auth_resp.status_code} {auth_resp.text}), signing up...")
            signup = await client.post("http://localhost:8000/api/auth/signup", json={
                "email": email, 
                "username": "superuser", 
                "password": pwd, 
                "full_name": "Super User"
            })
            print(f"Signup Status: {signup.status_code} {signup.text}")
            
            auth_resp = await client.post("http://localhost:8000/api/auth/login", json={
                "email": email, "password": pwd
            })
            
        if auth_resp.status_code == 200:
            token = auth_resp.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            print("Logged in successfully.")
        else:
            print(f"FATAL: Could not login. {auth_resp.text}")
            return

        # 2. Get Strategies
        resp = await client.get(URL, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

if __name__ == "__main__":
    asyncio.run(check_strategies())
