# Security Review

This document contains an audit of the security posture, authentication protocols, secrets encryption mechanisms, and a register of identified vulnerabilities in the QuantAI India platform.

## Authentication & Authorization
- **Protocol**: Single Sign-On (SSO) backed by **Firebase Authentication**.
- **Client Side**: Handled by the Firebase JS Client SDK. Users log in via Google OAuth or Email/Password, producing a Firebase ID Token (JWT).
- **Backend Verification**: 
  - Every protected API route depends on `get_current_user` in [auth.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/utils/auth.py) or [api.ts](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/frontend/src/services/api.ts).
  - The JWT is verified using the Firebase Admin SDK, ensuring token authenticity, expiration verification, and mapping token identifiers directly to local `User` rows in PostgreSQL.

---

## Secrets & Token Encryption Context
To prevent plaintext exposure of highly sensitive broker API keys (e.g. Upstox Access Tokens), the database schema utilizes **Fernet Symmetric Cryptography**.
- **`EncryptedString` Decorator**: Defined in [database.py](file:///c:/Users/Deepak%20Kumar/Downloads/quantai-india/backend/database.py). 
- **Encryption Key**: Loaded via `TOKEN_ENCRYPTION_KEY` from the environment.
- **Behavior**:
  - When saving broker credentials, SQLAlchemy calls `encrypt_token()`, transforming the token byte stream using AES-128 in CBC mode with an HMAC-SHA256 signature.
  - When reading credentials, the value is decrypted back into plaintext transparently via `decrypt_token()`. If the environment key is missing or corrupted, a fallback warning is logged, and decryption fails gracefully.

---

## Security Vulnerability Register

### 1. SQL Injection Vulnerability in Feature Store (Severity: `CRITICAL`)
- **Location**: `backend/services/feature_store.py:93-99`
- **Description**: The DuckDB SQL query is built dynamically using Python f-strings. A malicious actor could supply a manipulated list of symbols that executes arbitrary SQL statements inside the local file database.
- **Risk**: Potential data extraction or corruption of Parquet datasets.
- **Mitigation**: Refactor the query to use parameterized bindings (`?` or named parameters) instead of string formatting.

### 2. Overly Permissive CORS Configuration (Severity: `HIGH`)
- **Location**: `backend/main.py:32`
- **Description**: The FastAPI app registers `allow_origins=["*"]` when local config is loose. This permits any external web page to execute Cross-Origin Requests against the backend.
- **Risk**: Cross-Origin resource leaks if API tokens are hijacked.
- **Mitigation**: Restrict allowed origins to specific domains (e.g., `https://quantai-app.com`) loaded from the `.env` settings.

### 3. Arbitrary Code Execution via Pickled ML Models (Severity: `HIGH`)
- **Location**: `backend/ml/ensemble.py:194`
- **Description**: Model ensemble files are loaded from the filesystem using `joblib.load()` (which relies on Python `pickle`). 
- **Risk**: If a malicious model file is uploaded to the workspace directories, loading it will trigger arbitrary Python execution on the host server.
- **Mitigation**: Transition from standard pickle/joblib files to tensor serialization libraries (like `safetensors` or ONNX) for deep learning models, or sign model checksums using SHA-256.

### 4. Hardcoded Secrets in Infrastructure Config (Severity: `MEDIUM`)
- **Location**: `docker-compose.yml`
- **Description**: Database passwords (`postgres:admin`) and Grafana administrator credentials are stored as hardcoded, plain text environment values.
- **Risk**: Credentials exposure if the compose file is committed to public git repositories.
- **Mitigation**: Use Docker Secrets or load credentials via external environment files (.env) excluded from version control.
