import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from database import Base
# Import models to ensure all ForeignKey tables (e.g. users) are registered in Base.metadata
import models
from models_alpha import InstrumentMaster, StockCandle
from decimal import Decimal

@pytest.fixture
def db_session():
    # Set up an in-memory SQLite database for verifying schema rules in isolation
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_instrument_master_schema_and_uniqueness(db_session):
    # 1. Create a valid instrument
    inst = InstrumentMaster(
        instrument_id=1,
        instrument_key="NSE_EQ|INE002A01018",
        symbol="RELIANCE",
        series="EQ",
        exchange="NSE",
        company_name="Reliance Industries Limited",
        sector="Oil & Gas",
        isin_code="INE002A01018",
        is_active=True
    )
    db_session.add(inst)
    db_session.commit()
    
    # Verify retrieval
    retrieved = db_session.query(InstrumentMaster).filter_by(symbol="RELIANCE").first()
    assert retrieved is not None
    assert retrieved.instrument_key == "NSE_EQ|INE002A01018"
    assert retrieved.symbol == "RELIANCE"
    assert retrieved.series == "EQ"
    assert retrieved.exchange == "NSE"

    # 2. Check duplicate instrument_key constraint
    dup_key_inst = InstrumentMaster(
        instrument_id=2,
        instrument_key="NSE_EQ|INE002A01018",  # duplicate key
        symbol="RELIANCE_DUP",
        series="EQ",
        exchange="NSE"
    )
    db_session.add(dup_key_inst)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 3. Check composite unique constraint (symbol, series, exchange)
    dup_composite_inst = InstrumentMaster(
        instrument_id=3,
        instrument_key="NSE_EQ|OTHER",
        symbol="RELIANCE",  # duplicate combination
        series="EQ",
        exchange="NSE"
    )
    db_session.add(dup_composite_inst)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_stock_candle_schema_and_precision(db_session):
    # Setup instrument master row first (for FK constraint checking if active)
    inst = InstrumentMaster(
        instrument_id=10,
        instrument_key="NSE_EQ|INE467B01029",
        symbol="TCS",
        series="EQ",
        exchange="NSE"
    )
    db_session.add(inst)
    db_session.commit()

    # 1. Create a valid candle
    ts = datetime(2026, 7, 24, 10, 0, 0)
    candle = StockCandle(
        instrument_id=10,
        timeframe=1440,
        candle_ts=ts,
        open=Decimal("3000.1234"),
        high=Decimal("3050.5678"),
        low=Decimal("2990.0001"),
        close=Decimal("3010.9999"),
        volume=100000
    )
    db_session.add(candle)
    db_session.commit()

    # Retrieve and verify precision
    retrieved = db_session.query(StockCandle).filter_by(instrument_id=10, timeframe=1440, candle_ts=ts).first()
    assert retrieved is not None
    # Verify open and close values are numeric and keep exact precision
    assert float(retrieved.open) == 3000.1234
    assert float(retrieved.close) == 3010.9999
    assert retrieved.volume == 100000

    # 2. Check Primary Key constraint (instrument_id, timeframe, candle_ts must be unique)
    dup_candle = StockCandle(
        instrument_id=10,
        timeframe=1440,
        candle_ts=ts,
        open=Decimal("3100.0000"),
        high=Decimal("3150.0000"),
        low=Decimal("3090.0000"),
        close=Decimal("3110.0000"),
        volume=50000
    )
    db_session.add(dup_candle)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
