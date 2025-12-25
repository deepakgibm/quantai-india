"""
Test script for the 3-Agentic Stock Bot API - Writes output to file
"""
import asyncio
import httpx
import json

async def test_agentic_bot():
    """Test the agentic bot analyze endpoint."""
    base_url = "http://localhost:8000"
    output_file = "agentic_bot_test_result.json"
    
    payload = {
        "prompt": "Analyze top banking stocks for investment opportunities"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{base_url}/api/agentic-bot/analyze",
                json=payload
            )
            
            result = {
                "status_code": response.status_code,
                "prompt": payload["prompt"]
            }
            
            if response.status_code == 200:
                result["data"] = response.json()
                result["success"] = True
            else:
                result["error"] = response.text
                result["success"] = False
                
        except httpx.ConnectError as e:
            result = {"success": False, "error": f"Connection Error: {str(e)}"}
        except Exception as e:
            result = {"success": False, "error": f"{type(e).__name__}: {str(e)}"}
    
    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"Result written to {output_file}")
    print(f"Success: {result.get('success', False)}")
    print(f"Status: {result.get('status_code', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_agentic_bot())
