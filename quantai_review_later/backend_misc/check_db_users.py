import sqlite3

conn = sqlite3.connect('quantai.db', timeout=1)
c = conn.cursor()

try:
    c.execute('SELECT id, email, username, hashed_password FROM users')
    users = c.fetchall()
    print(f"Found {len(users)} users:")
    for user in users:
        print(f"  ID: {user[0]}, Email: {user[1]}, Username: {user[2]}")
        print(f"  Password hash start: {user[3][:20]}...")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
