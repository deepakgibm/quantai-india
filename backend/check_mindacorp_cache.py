
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
v = r.get('qai:snap:MINDACORP')
if v:
    d = json.loads(v)
    print(f"Cache LTP: {d.get('ltp')}")
    print(f"Prev Close: {d.get('prev_close')}")
    print(f"Change: {d.get('change_pct')}%")
else:
    print("MINDACORP not in cache")
