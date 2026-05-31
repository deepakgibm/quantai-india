import redis

def check_db(db_num):
    print(f"Checking DB {db_num}...")
    try:
        r = redis.Redis(host='localhost', port=6379, db=db_num, decode_responses=True)
        r.ping()
        keys = r.keys("*sector_heatmap*")
        print(f"  Keys found: {keys}")
        if keys:
            val = r.get(keys[0])
            print(f"  Value present (length): {len(val) if val else 0}")
    except Exception as e:
        print(f"  Error: {e}")

def main():
    check_db(0)
    check_db(1)

if __name__ == "__main__":
    main()
