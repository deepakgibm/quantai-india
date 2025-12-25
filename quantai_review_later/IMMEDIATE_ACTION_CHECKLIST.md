# ✅ Immediate Action Checklist
## QuantAI India - Next 14 Days

**Start Date**: November 22, 2025  
**Target Completion**: December 5, 2025  
**Focus**: Quick Wins + Critical Foundation

---

## 🎯 Overview

This checklist focuses on high-impact, low-effort improvements that can be completed in 2 weeks. Each task includes implementation steps and code snippets.

**Total Estimated Time**: 10-12 working days  
**Difficulty**: Medium  
**Impact**: High

---

## Day 1-2: Database Upgrade

### ✅ Task 1: Migrate from SQLite to PostgreSQL

**Why**: SQLite doesn't handle concurrent writes well, PostgreSQL is production-ready

**Steps**:

1. **Install PostgreSQL**
```bash
# Windows (using Chocolatey)
choco install postgresql

# Or download from postgresql.org
```

2. **Update requirements.txt**
```python
# Change:
aiosqlite==0.19.0

# To:
asyncpg==0.29.0
psycopg2-binary==2.9.9
```

3. **Update database.py**
```python
# backend/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Change DATABASE_URL in config.py
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/quantai"

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

4. **Migration Script**
```python
# backend/migrate_to_postgres.py
import asyncio
import sqlite3
from sqlalchemy.ext.asyncio import create_async_engine
from models import User, Order, Algorithm, UserSettings

async def migrate():
    # Read from SQLite
    sqlite_conn = sqlite3.connect('quantai.db')
    
    # Write to PostgreSQL
    pg_engine = create_async_engine("postgresql+asyncpg://user:password@localhost:5432/quantai")
    
    # Migrate each table
    # ... migration logic
    
    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
```

**Validation**:
```bash
cd backend
python migrate_to_postgres.py
python test_integration_simple.py  # All tests should pass
```

---

## Day 3-4: Caching & Performance

### ✅ Task 2: Add Redis Caching

**Why**: Reduce API calls, faster responses, better user experience

**Steps**:

1. **Install Redis**
```bash
# Windows
choco install redis-64

# Start Redis
redis-server
```

2. **Update requirements.txt**
```python
redis==5.0.1
aioredis==2.0.1
```

3. **Create cache service**
```python
# backend/services/cache_service.py
import aioredis
from typing import Optional, Any
import json

class CacheService:
    def __init__(self):
        self.redis = None
    
    async def connect(self):
        self.redis = await aioredis.from_url("redis://localhost:6379")
    
    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value: Any, expire: int = 300):
        """Set value with expiration in seconds"""
        await self.redis.set(key, json.dumps(value), ex=expire)
    
    async def delete(self, key: str):
        await self.redis.delete(key)
    
    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

cache = CacheService()
```

4. **Update main.py**
```python
# backend/main.py
from services.cache_service import cache

@app.on_event("startup")
async def startup_event():
    await init_db()
    await cache.connect()
    print("Database and cache initialized")

@app.on_event("shutdown")
async def shutdown_event():
    await cache.redis.close()
```

5. **Use caching in routers**
```python
# backend/routers/trading.py
from services.cache_service import cache

@router.get("/market-indices")
async def get_market_indices(current_user: User = Depends(get_current_user)):
    # Check cache first
    cached = await cache.get("market_indices")
    if cached:
        return cached
    
    # Fetch fresh data
    indices = [
        {"name": "NIFTY 50", "value": 22430.5, "change": 125.4, "percent": 0.56},
        {"name": "BANK NIFTY", "value": 47540.2, "change": -89.3, "percent": -0.19},
        {"name": "INDIA VIX", "value": 12.45, "change": -0.55, "percent": -4.23}
    ]
    
    # Cache for 60 seconds
    await cache.set("market_indices", indices, expire=60)
    
    return indices
```

**Validation**:
```bash
# First call - should be slower
curl http://localhost:8000/api/trading/market-indices

# Second call - should be instant (from cache)
curl http://localhost:8000/api/trading/market-indices
```

---

## Day 5: Logging & Monitoring

### ✅ Task 3: Implement Structured Logging

**Why**: Debug issues, track trades, audit trail, compliance

**Steps**:

1. **Update requirements.txt**
```python
structlog==24.1.0
python-json-logger==2.0.7
```

2. **Create logging config**
```python
# backend/utils/logging_config.py
import structlog
import logging
from datetime import datetime

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

logger = structlog.get_logger()
```

3. **Use in code**
```python
# backend/routers/orders.py
from utils.logging_config import logger

@router.post("/")
async def place_order(
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(
        "order_placement_started",
        user_id=current_user.id,
        symbol=order.symbol,
        order_type=order.order_type,
        quantity=order.quantity
    )
    
    try:
        # ... order placement logic
        
        logger.info(
            "order_placed_successfully",
            user_id=current_user.id,
            order_id=db_order.id,
            symbol=order.symbol
        )
        
        return db_order
        
    except Exception as e:
        logger.error(
            "order_placement_failed",
            user_id=current_user.id,
            symbol=order.symbol,
            error=str(e)
        )
        raise
```

4. **Update main.py**
```python
from utils.logging_config import configure_logging, logger

configure_logging()

@app.on_event("startup")
async def startup_event():
    await init_db()
    await cache.connect()
    logger.info("application_started", version="1.0.0")
```

---

## Day 6: Security & Rate Limiting

### ✅ Task 4: Add Rate Limiting

**Why**: Prevent API abuse, respect broker limits, better resource management

**Steps**:

1. **Update requirements.txt**
```python
slowapi==0.1.9
```

2. **Configure rate limiter**
```python
# backend/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

3. **Apply to routes**
```python
# backend/routers/orders.py
from main import limiter

@router.post("/")
@limiter.limit("10/minute")  # Max 10 orders per minute
async def place_order(
    request: Request,
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # ... order logic

@router.get("/")
@limiter.limit("100/minute")  # Max 100 reads per minute
async def get_orders(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # ... get logic
```

4. **Add API key validation**
```python
# backend/utils/auth.py
async def verify_api_key(api_key: str = Header(None)):
    """For programmatic API access"""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Validate API key from database
    # ... validation logic
    
    return api_key
```

---

## Day 7-8: Testing Infrastructure

### ✅ Task 5: Comprehensive Unit Tests

**Why**: Prevent regressions, safe refactoring, confidence in changes

**Steps**:

1. **Update requirements.txt**
```python
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2  # For testing async FastAPI
```

2. **Create test structure**
```
backend/tests/
├── __init__.py
├── conftest.py
├── test_auth.py
├── test_orders.py
├── test_algorithms.py
├── test_trading.py
└── test_risk.py
```

3. **Setup conftest.py**
```python
# backend/tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from main import app
from database import Base, get_db
from models import User
from utils.auth import get_password_hash

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/quantai_test"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def client(test_db):
    async def override_get_db():
        async_session = sessionmaker(
            test_db, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

4. **Write tests**
```python
# backend/tests/test_auth.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_signup(client: AsyncClient):
    response = await client.post("/api/auth/signup", json={
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    # First signup
    await client.post("/api/auth/signup", json={
        "email": "test2@example.com",
        "username": "testuser2",
        "full_name": "Test User 2",
        "password": "testpass123"
    })
    
    # Then login
    response = await client.post("/api/auth/login", json={
        "email": "test2@example.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
```

5. **Run tests**
```bash
# Run all tests
pytest backend/tests/

# Run with coverage
pytest --cov=backend backend/tests/

# Run specific test
pytest backend/tests/test_auth.py::test_signup
```

**Target**: 50%+ coverage initially, 80%+ within a month

---

## Day 9-10: Code Quality

### ✅ Task 6: Code Formatting & Linting

**Steps**:

1. **Install tools**
```bash
pip install black isort flake8 mypy
```

2. **Create configs**
```toml
# backend/pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
```

3. **Format code**
```bash
# Format with Black
black backend/

# Sort imports
isort backend/

# Check for issues
flake8 backend/ --max-line-length=100
mypy backend/
```

4. **Pre-commit hooks**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
```

---

## Day 11-12: Documentation

### ✅ Task 7: API Documentation

**Steps**:

1. **Enhanced OpenAPI docs**
```python
# backend/main.py
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="QuantAI India Trading Bot API",
        version="1.0.0",
        description="""
        ## Features
        - User authentication with JWT
        - Trading operations
        - Algorithm management
        - AI-powered trading assistant
        - Upstox integration
        
        ## Authentication
        All endpoints except /api/auth/* require Bearer token
        """,
        routes=app.routes,
    )
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

2. **Add example responses**
```python
# backend/routers/orders.py
@router.post("/", response_model=OrderResponse)
async def place_order(
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Place a new order
    
    - **symbol**: Stock symbol (e.g., "RELIANCE", "TCS")
    - **order_type**: "BUY" or "SELL"
    - **quantity**: Number of shares
    - **price**: Limit price (optional, for limit orders)
    
    Returns the created order with status "PENDING"
    """
    # ... logic
```

3. **README updates**
```markdown
# QuantAI India Trading Bot

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend
npm install
npm run dev
```

## API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
```

---

## Day 13-14: Performance & Monitoring

### ✅ Task 8: Basic Monitoring

**Steps**:

1. **Add Prometheus metrics**
```python
# requirements.txt
prometheus-fastapi-instrumentator==6.1.0
```

2. **Setup monitoring**
```python
# backend/main.py
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

3. **Health check endpoint**
```python
@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check
    Returns system status, database connectivity, cache status
    """
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "unknown",
        "cache": "unknown",
        "apis": {
            "upstox": "unknown",
            "gemini": "unknown"
        }
    }
    
    # Check database
    try:
        await db.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        checks["status"] = "degraded"
    
    # Check Redis
    try:
        await cache.redis.ping()
        checks["cache"] = "healthy"
    except:
        checks["cache"] = "unhealthy"
        checks["status"] = "degraded"
    
    return checks
```

---

## ✅ Validation Checklist

### End of Week 1
- [ ] PostgreSQL migrated and tested
- [ ] Redis caching working
- [ ] Logging producing structured JSON logs
- [ ] Rate limiting active on all endpoints
- [ ] 10+ unit tests passing

### End of Week 2
- [ ] 50%+ test coverage
- [ ] Code formatted with Black
- [ ] API documentation updated
- [ ] Health check endpoint working
- [ ] All integration tests passing
- [ ] No critical security issues

---

## 📊 Success Metrics

| Metric | Before | Target | Actual |
|--------|--------|--------|--------|
| Database | SQLite | PostgreSQL | ___ |
| API Response Time | Varies | <100ms | ___ |
| Test Coverage | 0% | 50% | ___ |
| Code Issues (flake8) | Unknown | <10 | ___ |
| Uptime | Unknown | 99%+ | ___ |

---

## 🚀 Next Steps (Week 3+)

After completing this checklist:

1. **Week 3-4**: Start real-time market data integration
2. **Week 5-6**: Begin backtesting engine development
3. **Week 7-8**: Implement risk management system
4. **Week 9+**: Strategy development

---

## 📞 Support

If you get stuck:
1. Check error logs: `tail -f backend/logs/app.log`
2. Review test failures: `pytest -v`
3. Consult documentation in `QUANTAI_ENHANCEMENT_ROADMAP.md`

---

**Remember**: These are quick wins to strengthen the foundation. Don't skip them to jump to "exciting" features. This foundation will save you weeks of debugging later!

**Good luck! 🚀**
