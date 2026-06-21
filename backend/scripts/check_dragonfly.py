import redis
try:
    r = redis.Redis(host='localhost', port=6379, socket_timeout=1.0)
    print("Ping:", r.ping())
except Exception as e:
    print("Connection failed:", e)
