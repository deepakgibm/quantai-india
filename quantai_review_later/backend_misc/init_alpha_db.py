"""
Database initialization script for AlphaPrime models.

Since the project uses SQLite with async create_all() instead of Alembic,
this script ensures all AlphaPrime tables are created when the database initializes.

Usage:
    python init_alpha_db.py
"""

import asyncio
from database import engine, Base
from models_alpha import (
    AlphaPrimeConfig
)


async def init_alpha_tables():
    """
    Create all AlphaPrime tables in the database.
    This is idempotent - safe to run multiple times.
    """
    print("Initializing AlphaPrime database tables...")
    
    async with engine.begin() as conn:
        # Create all tables defined in Base metadata
        await conn.run_sync(Base.metadata.create_all)
    
    print("✓ AlphaPrime tables created successfully!")
    print("\nCreated tables:")
    print("  - stock_data (OHLCV time-series)")
    print("  - alpha_signals (Factor values)")
    print("  - trade_decisions (ML-driven trades)")
    print("  - etl_logs (Pipeline audit trail)")
    print("  - alpha_prime_config (Module configuration)")


async def create_default_config():
    """
    Insert default AlphaPrime configuration if it doesn't exist.
    """
    from database import AsyncSessionLocal
    from sqlalchemy import select
    
    print("\nCreating default AlphaPrime configuration...")
    
    async with AsyncSessionLocal() as session:
        # Check if default config exists
        result = await session.execute(
            select(AlphaPrimeConfig).where(AlphaPrimeConfig.config_name == "default")
        )
        existing_config = result.scalar_one_or_none()
        
        if existing_config:
            print("✓ Default configuration already exists")
            return
        
        # Create default config
        default_config = AlphaPrimeConfig(
            config_name="default",
            lookback_period=30,
            rebalance_frequency="daily",
            momentum_weight=0.33,
            volatility_weight=0.33,
            volume_weight=0.34,
            max_position_size=0.05,
            stop_loss_pct=0.02,
            take_profit_pct=0.06,
            min_confidence=0.70,
            max_positions=10,
            ml_enabled=True,
            auto_trade_enabled=False,
            paper_trade_mode=True,
            version="v1.0"
        )
        
        session.add(default_config)
        await session.commit()
        print("✓ Default configuration created")


async def main():
    """Main entry point"""
    try:
        await init_alpha_tables()
        await create_default_config()
        print("\n✅ AlphaPrime database initialization complete!")
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
