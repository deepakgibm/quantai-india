import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Connect to database
conn = sqlite3.connect('quantai.db')
cursor = conn.cursor()

# Hash the password
hashed_password = pwd_context.hash("demo123")

# Check if user exists
cursor.execute("SELECT id, email FROM users WHERE email = ?", ("demo@example.com",))
user = cursor.fetchone()

if user:
    print(f"Found user: {user[1]}")
    # Update password
    cursor.execute("UPDATE users SET hashed_password = ? WHERE email = ?", 
                   (hashed_password, "demo@example.com"))
    conn.commit()
    print("✅ Password reset to: demo123")
else:
    print("Creating new demo user...")
    cursor.execute("""
        INSERT INTO users (email, username, hashed_password, full_name, is_active, is_upstox_connected)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("demo@example.com", "demo", hashed_password, "Demo User", 1, 0))
    user_id = cursor.lastrowid
    
    # Create user settings
    cursor.execute("""
        INSERT INTO user_settings (user_id, max_capital, max_risk_per_trade, auto_trade, notifications)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, 1000000, 2.0, 0, 1))
    
    conn.commit()
    print("✅ Created demo user")
    print(f"   Email: demo@example.com")
    print(f"   Password: demo123")

conn.close()
