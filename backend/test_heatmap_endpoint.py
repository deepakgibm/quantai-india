import asyncio
import time
from fastapi.testclient import TestClient
from main import app
from utils.auth import get_current_user
from models import User

# Define dummy user
dummy_user = User(id=1, email="test@quantai.com", is_active=True)

# Override auth dependency
app.dependency_overrides[get_current_user] = lambda: dummy_user

client = TestClient(app)

def test_endpoint():
    start_time = time.time()
    response = client.get("/api/heatmap?mode=performance&timeframe=1D")
    duration = time.time() - start_time
    
    print(f"Heatmap API status: {response.status_code}")
    print(f"Heatmap API duration: {duration:.4f} seconds")
    if response.status_code == 200:
        data = response.json()
        print(f"Response status: {data.get('status')}")
        print(f"Number of sectors: {len(data.get('sectors', []))}")
        if data.get('sectors'):
            print("Sample sector:", data['sectors'][0]['name'], "with", len(data['sectors'][0]['stocks']), "stocks")
    else:
        print("Error content:", response.content)

if __name__ == "__main__":
    test_endpoint()
