
import bcrypt
from passlib.context import CryptContext

# Monkeypatch for passlib + bcrypt 4.0 compatibility
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("about", (object,), {"__version__": bcrypt.__version__})

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    print(f"Verifying: plain={plain_password}, hashed={hashed_password}")
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Crashed in pwd_context.verify: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    hashed = "$2b$12$0XyI06n5fG9H/MIF7MCCyFiXVClsv6lMmavwAI"
    plain = "admin123"
    result = verify_password(plain, hashed)
    print(f"Final result: {result}")
