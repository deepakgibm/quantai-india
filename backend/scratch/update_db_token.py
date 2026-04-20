import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path
from cryptography.fernet import Fernet

load_dotenv(Path('backend/.env'))

def update_token():
    db_url = os.getenv('DATABASE_URL').replace('+asyncpg', '')
    key = os.getenv('TOKEN_ENCRYPTION_KEY')
    if not key:
        print("TOKEN_ENCRYPTION_KEY not found")
        return
        
    f = Fernet(key)
    token = os.getenv('UPSTOX_ACCESS_TOKEN')
    if not token:
        print("UPSTOX_ACCESS_TOKEN not found")
        return
        
    encrypted = f.encrypt(token.encode()).decode()
    
    engine = create_engine(db_url)
    with engine.connect() as conn:
        try:
            # First check if it exists
            res = conn.execute(text("SELECT id FROM auth_tokens WHERE token_type = 'ANALYTICS'"))
            row = res.fetchone()
            
            if row:
                conn.execute(
                    text("UPDATE auth_tokens SET encrypted_token = :val, health_status = 'HEALTHY' WHERE token_type = 'ANALYTICS'"),
                    {'val': encrypted}
                )
                print("Token updated in DB")
            else:
                # Need to find the system user ID
                res = conn.execute(text("SELECT id FROM users WHERE username = 'system_bot'"))
                sys_user = res.fetchone()
                if not sys_user:
                    print("system_bot user not found, cannot insert token")
                    return
                    
                conn.execute(
                    text("INSERT INTO auth_tokens (user_id, token_type, encrypted_token, health_status) VALUES (:uid, 'ANALYTICS', :val, 'HEALTHY')"),
                    {'uid': sys_user[0], 'val': encrypted}
                )
                print("Token inserted in DB")
            
            conn.commit()
        except Exception as e:
            print(f"Error updating token: {e}")

if __name__ == "__main__":
    update_token()
