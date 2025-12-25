
import requests
import json
import sys

def test_agentic_bot():
    base_url = "http://localhost:8000"
    
    # 1. Health Check
    try:
        print("Checking health...")
        resp = requests.get(f"{base_url}/health")
        print(f"Health: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    url = f"{base_url}/api/agentic-bot/analyze"
    prompt = "find top 5 stock to buy for the period of 1 week"
    
    print(f"\nTesting Agentic Bot with prompt: '{prompt}'")
    
    try:
        response = requests.post(url, json={"prompt": prompt}, timeout=60) # Add timeout
        
        if response.status_code == 200:
            data = response.json()
            print("\n[OK] API Call Successful")
            print(f"Status: {data.get('status')}")
            
            results = data.get('data', [])
            print(f"\nReceived {len(results)} recommendations:")
            
            for i, stock in enumerate(results):
                print(f"\n{i+1}. {stock['symbol']} ({stock['final_decision']})")
                print(f"   Buy Score: {stock['buy_score']}")
                print(f"   Reason: {stock['reason_for_buy']}")
                print(f"   Risk Score: {stock['risk_score']}")
                print(f"   ML Confidence: {stock['ml_reasoning']}")
                print(f"   News Sentiment: {stock['news_sentiment']}")
                
            if len(results) > 0:
                print("\n[PASS] Test Passed: Received recommendations.")
            else:
                print("\n[FAIL] Test Failed: No recommendations returned.")
                
        else:
            print(f"\n[FAIL] API Call Failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")

if __name__ == "__main__":
    test_agentic_bot()
