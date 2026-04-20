"""
Trade Screener — Database Models

Production-grade SQLAlchemy models for the institutional stock analysis system.
7 tables covering financials, holdings, insider activity, scoring, and conviction lists.
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean, DateTime,
    Text, JSON, Index, UniqueConstraint, Date, SmallInteger, Numeric
)
from datetime import datetime
from database import Base


# =============================================================================
# FUNDAMENTAL DATA TABLES
# =============================================================================

class ScreenerFinancials(Base):
    """
    Quarterly and annual financial data for fundamental analysis.
    Sources: yfinance, NSE filings, Screener-style parsing.
    """
    __tablename__ = "screener_financials"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    period_type = Column(String(10), nullable=False, default="quarterly")  # quarterly, annual
    period_end = Column(Date, nullable=False)  # End date of the period
    fiscal_year = Column(Integer, nullable=True)
    quarter = Column(SmallInteger, nullable=True)  # 1-4 for quarterly

    # Revenue & Profitability
    revenue = Column(Numeric(18, 2), nullable=True)  # Total Revenue (Cr)
    net_profit = Column(Numeric(18, 2), nullable=True)
    ebitda = Column(Numeric(18, 2), nullable=True)
    operating_profit = Column(Numeric(18, 2), nullable=True)
    ebitda_margin = Column(Float, nullable=True)  # %
    net_margin = Column(Float, nullable=True)  # %
    operating_margin = Column(Float, nullable=True)  # %

    # Growth Metrics
    revenue_growth_yoy = Column(Float, nullable=True)  # % YoY
    profit_growth_yoy = Column(Float, nullable=True)  # % YoY
    revenue_growth_qoq = Column(Float, nullable=True)  # % QoQ
    profit_growth_qoq = Column(Float, nullable=True)  # % QoQ

    # Return Ratios
    roe = Column(Float, nullable=True)  # Return on Equity %
    roce = Column(Float, nullable=True)  # Return on Capital Employed %
    roa = Column(Float, nullable=True)  # Return on Assets %

    # Debt Metrics
    total_debt = Column(Numeric(18, 2), nullable=True)
    total_equity = Column(Numeric(18, 2), nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    interest_coverage = Column(Float, nullable=True)

    # Cash Flow
    operating_cash_flow = Column(Numeric(18, 2), nullable=True)
    free_cash_flow = Column(Numeric(18, 2), nullable=True)
    capex = Column(Numeric(18, 2), nullable=True)

    # Valuation
    eps = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)
    market_cap = Column(Numeric(18, 2), nullable=True)  # Cr

    # CAGR (calculated over multiple periods)
    sales_cagr_3y = Column(Float, nullable=True)
    sales_cagr_5y = Column(Float, nullable=True)
    profit_cagr_3y = Column(Float, nullable=True)
    profit_cagr_5y = Column(Float, nullable=True)

    # Metadata
    data_source = Column(String(30), default="yfinance")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('symbol', 'period_type', 'period_end', name='uq_screener_fin'),
        Index('idx_screener_fin_symbol_period', 'symbol', 'period_end'),
        Index('idx_screener_fin_type', 'period_type'),
        {'extend_existing': True}
    )


# =============================================================================
# HOLDINGS & INSTITUTIONAL DATA
# =============================================================================

class ScreenerHoldingsHistory(Base):
    """
    Quarterly shareholding pattern history.
    Tracks promoter, FII, DII, MF holdings over time.
    Source: NSE shareholding pattern filings.
    """
    __tablename__ = "screener_holdings_history"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    quarter_end = Column(Date, nullable=False)  # Quarter ending date
    fiscal_year = Column(Integer, nullable=True)
    quarter = Column(SmallInteger, nullable=True)  # 1-4

    # Promoter Holdings
    promoter_pct = Column(Float, nullable=True)
    promoter_change = Column(Float, nullable=True)  # QoQ change in %
    promoter_pledge_pct = Column(Float, nullable=True)  # % of promoter holding pledged

    # Foreign Institutional Investors
    fii_pct = Column(Float, nullable=True)
    fii_change = Column(Float, nullable=True)  # QoQ change

    # Domestic Institutional Investors
    dii_pct = Column(Float, nullable=True)
    dii_change = Column(Float, nullable=True)  # QoQ change

    # Mutual Funds (subset of DII)
    mf_pct = Column(Float, nullable=True)
    mf_change = Column(Float, nullable=True)  # QoQ change

    # Insurance (subset of DII)
    insurance_pct = Column(Float, nullable=True)

    # Retail / Public
    public_pct = Column(Float, nullable=True)

    # Metadata
    data_source = Column(String(30), default="nse")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('symbol', 'quarter_end', name='uq_screener_holdings'),
        Index('idx_screener_holdings_symbol_qtr', 'symbol', 'quarter_end'),
        {'extend_existing': True}
    )


class ScreenerInsiderActivity(Base):
    """
    Insider buying/selling activity tracking.
    Source: NSE SAST disclosures, bulk deal data.
    """
    __tablename__ = "screener_insider_activity"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)

    person_name = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True)  # Promoter, Director, KMP, etc.
    transaction_type = Column(String(10), nullable=False)  # BUY or SELL
    quantity = Column(BigInteger, nullable=True)
    price = Column(Float, nullable=True)
    value = Column(Numeric(18, 2), nullable=True)  # Total value in Rs

    # Metadata
    data_source = Column(String(30), default="nse")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_screener_insider_symbol_date', 'symbol', 'trade_date'),
        Index('idx_screener_insider_txn', 'transaction_type'),
        {'extend_existing': True}
    )


class ScreenerBulkDeals(Base):
    """
    Bulk and block deal tracking.
    Large institutional transactions that signal smart money movement.
    Source: NSE/BSE bulk deal disclosures.
    """
    __tablename__ = "screener_bulk_deals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)
    deal_type = Column(String(10), default="BULK")  # BULK or BLOCK

    client_name = Column(String(300), nullable=True)
    transaction_type = Column(String(10), nullable=False)  # BUY or SELL
    quantity = Column(BigInteger, nullable=True)
    price = Column(Float, nullable=True)
    turnover = Column(Numeric(18, 2), nullable=True)  # Total turnover in Cr

    # Metadata
    data_source = Column(String(30), default="nse")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_screener_bulk_symbol_date', 'symbol', 'trade_date'),
        Index('idx_screener_bulk_type', 'deal_type'),
        {'extend_existing': True}
    )


# =============================================================================
# SCORING & CONVICTION TABLES
# =============================================================================

class ScreenerStockScore(Base):
    """
    Per-stock multi-dimensional scoring results.
    Updated daily by the scoring engine.
    
    Each dimension scores 0-100, weighted to produce overall_score.
    """
    __tablename__ = "screener_stock_score"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    score_date = Column(Date, nullable=False, index=True)

    # Current Market Price snapshot
    cmp = Column(Float, nullable=True)
    market_cap_cr = Column(Float, nullable=True)
    sector = Column(String(100), nullable=True)

    # === Dimension Scores (0-100 each) ===

    # 1. Promoter Quality (weight: 15%)
    promoter_score = Column(Float, nullable=True)
    promoter_holding = Column(Float, nullable=True)  # % captured at scoring time
    promoter_pledge = Column(Float, nullable=True)

    # 2. Institutional Accumulation (weight: 20%)
    institutional_score = Column(Float, nullable=True)
    fii_holding = Column(Float, nullable=True)
    dii_holding = Column(Float, nullable=True)
    fii_change_qoq = Column(Float, nullable=True)
    dii_change_qoq = Column(Float, nullable=True)

    # 3. Earnings Quality (weight: 20%)
    earnings_score = Column(Float, nullable=True)
    revenue_growth = Column(Float, nullable=True)
    profit_growth = Column(Float, nullable=True)
    roe_latest = Column(Float, nullable=True)
    roce_latest = Column(Float, nullable=True)

    # 4. Debt Quality (weight: 10%)
    debt_score = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    interest_coverage_val = Column(Float, nullable=True)

    # 5. Order Book / Growth Pipeline (weight: 10%)
    order_book_score = Column(Float, nullable=True)

    # 6. Sector Leadership (weight: 10%)
    sector_score = Column(Float, nullable=True)
    sector_rank = Column(Integer, nullable=True)  # Rank within sector

    # 7. Technical Strength (weight: 10%)
    technical_score = Column(Float, nullable=True)
    pct_from_52w_high = Column(Float, nullable=True)
    relative_strength = Column(Float, nullable=True)  # vs NIFTY

    # 8. Market Direction (weight: 5%)
    market_score = Column(Float, nullable=True)

    # === Composite Scores ===
    overall_score = Column(Float, nullable=False, index=True)  # Weighted 0-100
    rank = Column(Integer, nullable=True, index=True)  # 1 = best
    conviction_level = Column(String(20), nullable=True)  # EXTREME, VERY_HIGH, HIGH, MODERATE, AVOID

    # Score breakdown as JSON for transparency
    score_breakdown = Column(JSON, nullable=True)

    # Metadata
    scoring_version = Column(String(10), default="1.0")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('symbol', 'score_date', name='uq_screener_score'),
        Index('idx_screener_score_overall', 'overall_score'),
        Index('idx_screener_score_conviction', 'conviction_level'),
        Index('idx_screener_score_sector', 'sector'),
        {'extend_existing': True}
    )


class ScreenerConvictionList(Base):
    """
    Final ranked BUY list with full institutional-grade analysis.
    Generated from ScreenerStockScore + additional qualitative analysis.
    """
    __tablename__ = "screener_conviction_list"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    score_date = Column(Date, nullable=False, index=True)
    rank = Column(Integer, nullable=False)

    # Classification
    conviction_level = Column(String(20), nullable=False)  # EXTREME, VERY_HIGH, HIGH
    list_type = Column(String(20), default="BUY")  # BUY or AVOID

    # Stock Context
    company_name = Column(String(200), nullable=True)
    sector = Column(String(100), nullable=True)
    cmp = Column(Float, nullable=True)
    market_cap_cr = Column(Float, nullable=True)

    # Holdings Snapshot
    promoter_holding = Column(Float, nullable=True)
    fii_holding = Column(Float, nullable=True)
    dii_holding = Column(Float, nullable=True)

    # Growth Metrics
    sales_growth = Column(Float, nullable=True)  # Latest YoY %
    profit_growth = Column(Float, nullable=True)  # Latest YoY %

    # Quality Metrics
    roe = Column(Float, nullable=True)
    roce = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)

    # Overall Score
    overall_score = Column(Float, nullable=False)

    # Investment Thesis (Generated by conviction service)
    why_buy = Column(Text, nullable=True)
    risk_factors = Column(Text, nullable=True)

    # Trade Parameters
    buy_zone_low = Column(Float, nullable=True)
    buy_zone_high = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    target_1y = Column(Float, nullable=True)
    target_3y = Column(Float, nullable=True)

    # Order Book / Pipeline Quality
    order_book_strength = Column(String(20), nullable=True)  # STRONG, MODERATE, WEAK

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('symbol', 'score_date', 'list_type', name='uq_screener_conviction'),
        Index('idx_conviction_rank', 'rank'),
        Index('idx_conviction_type', 'list_type'),
        {'extend_existing': True}
    )


class ScreenerSectorAnalysis(Base):
    """
    Sector-level analysis for rotation insights.
    Updated daily alongside stock scoring.
    """
    __tablename__ = "screener_sector_analysis"

    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    score_date = Column(Date, nullable=False, index=True)

    # Sector Performance
    sector_score = Column(Float, nullable=True)  # 0-100
    avg_stock_score = Column(Float, nullable=True)
    stock_count = Column(Integer, nullable=True)

    # Rotation Signal
    rotation_signal = Column(String(20), nullable=True)  # ACCUMULATE, HOLD, REDUCE, AVOID
    momentum_3m = Column(Float, nullable=True)  # 3-month sector return %
    momentum_6m = Column(Float, nullable=True)  # 6-month sector return %
    momentum_1y = Column(Float, nullable=True)  # 1-year sector return %

    # Sector Leaders (top 3 stocks by score)
    leaders = Column(JSON, nullable=True)  # [{"symbol": "X", "score": 85}, ...]

    # FII/DII Flow into sector
    avg_fii_holding = Column(Float, nullable=True)
    avg_fii_change = Column(Float, nullable=True)  # QoQ
    avg_dii_holding = Column(Float, nullable=True)

    # Outlook
    outlook_6m = Column(String(20), nullable=True)  # BULLISH, NEUTRAL, BEARISH
    outlook_2y = Column(String(20), nullable=True)
    outlook_5y = Column(String(20), nullable=True)
    outlook_rationale = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('sector', 'score_date', name='uq_screener_sector'),
        Index('idx_screener_sector_score', 'sector_score'),
        {'extend_existing': True}
    )
