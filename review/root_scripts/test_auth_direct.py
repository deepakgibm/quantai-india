
import bcrypt

def test_direct():
    plain = "admin123"
    hashed = "$2b$12$R.S/I06n5fG9H/MIF7DFd.UxLVC5yF9Z9relfIeU/D"
    print(f"Testing direct checkpw: plain={plain}, hashed={hashed}")
    try:
        # Bcrypt expects bytes
        res = bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
        print(f"Result: {res}")
    except Exception as e:
        print(f"Direct checkpw failed: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_direct()
