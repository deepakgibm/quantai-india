import sqlite3
import bcrypt

# Hash the password with bcrypt
password = "demo123"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# Connect and update
conn = sqlite3.connect('quantai.db')
c = conn.cursor()

# Delete existing demo user
c.execute('DELETE FROM user_settings WHERE user_id IN (SELECT id FROM users WHERE email="demo@example.com")')
c.execute('DELETE FROM users WHERE email="demo@example.com"')

# Create new user
c.execute('''INSERT INTO users (email, username, hashed_password, full_name, is_active, is_upstox_connected, created_at) 
             VALUES (?, ?, ?, ?, ?, ?, datetime('now'))''', 
          ('demo@example.com', 'demo', hashed, 'Demo User', 1, 0))
user_id = c.lastrowid

# Create settings
c.execute('''INSERT INTO user_settings (user_id, max_capital, max_risk_per_trade, auto_trade, notifications) 
             VALUES (?, ?, ?, ?, ?)''',
          (user_id, 1000000, 2.0, 0, 1))

conn.commit()
conn.close()

print("✅ Demo user created successfully!")
print("   Email: demo@example.com")
print("   Password: demo123")
print("\nPlease restart the backend server now:")
print("   1. Press Ctrl+C in the uvicorn terminal")
print("   2. Run: python -m uvicorn main:app --reload --port 8000")
