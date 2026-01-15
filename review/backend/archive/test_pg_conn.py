import psycopg2
import sys

def test_conn():
    params = [
        "host=localhost dbname=quantai user=postgres password=admin",
        "host=localhost dbname=quantai user=quantai password=quantai123",
        "host=localhost dbname=quantai user=postgres password=quantai123",
        "host=localhost dbname=quantai user=quantai",
        "host=localhost dbname=postgres user=postgres password=quantai123",
    ]
    
    for p in params:
        try:
            print(f"Testing: {p}")
            conn = psycopg2.connect(p)
            print("  SUCCESS!")
            conn.close()
            return p
        except Exception as e:
            print(f"  FAILED: {e}")
    
    return None

if __name__ == "__main__":
    test_conn()
