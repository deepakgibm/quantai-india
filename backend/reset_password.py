"""Check and reset test user password with valid bcrypt hash."""
import psycopg2
import bcrypt

# Generate a proper bcrypt hash for the password
password = "admin1243"
salt = bcrypt.gensalt()
new_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
print(f'New hash: {new_hash}')

conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
cur = conn.cursor()

# Check current hash
cur.execute("SELECT id, email, hashed_password FROM users WHERE email = 'dthat53@gmail.com'")
row = cur.fetchone()
if row:
    print(f'Found user: id={row[0]}, email={row[1]}')
    current_hash = str(row[2]) if row[2] else 'None'
    print(f'Current hash length: {len(current_hash)}')
    print(f'Current hash starts with: {current_hash[:20]}')
    print(f'Is valid bcrypt hash: {current_hash.startswith("$2")}')
    
    # Update with new bcrypt hash
    cur.execute("UPDATE users SET hashed_password = %s WHERE email = 'dthat53@gmail.com'", (new_hash,))
    conn.commit()
    print(f'Password updated successfully! New hash: {new_hash[:30]}...')
else:
    print('User not found - creating user')
    # Create user
    cur.execute("""
        INSERT INTO users (email, username, full_name, hashed_password, is_active, created_at)
        VALUES ('dthat53@gmail.com', 'deepak', 'Deepak Kumar', %s, true, NOW())
    """, (new_hash,))
    conn.commit()
    print('User created successfully!')
    
conn.close()
