import pytest
from backend.api.option_flow import classify_option_sentiment

def test_sentiment_buildup_long_call():
    # Long buildup on Call option -> Bullish
    sentiment, conf = classify_option_sentiment(
        option_type="call",
        oi=100000,
        oi_change=10000,
        volume=5000,
        ltp=150.0,
        gex=15000000.0,
        buildup="Long Build-Up",
        opponent_oi=50000,
        opponent_gex=5000000.0,
        strike_price=2300.0,
        spot_price=2290.0,
        max_chain_oi=500000,
        max_chain_vol=20000
    )
    assert sentiment == "Bullish" or sentiment == "Strong Bullish"
    assert conf >= 35

def test_sentiment_buildup_short_call():
    # Short buildup on Call option -> Bearish / Strong Bearish
    sentiment, conf = classify_option_sentiment(
        option_type="call",
        oi=400000,
        oi_change=50000,
        volume=10000,
        ltp=25.0,
        gex=10000000.0,
        buildup="Short Build-Up",
        opponent_oi=50000,
        opponent_gex=1000000.0,
        strike_price=2400.0,
        spot_price=2300.0,
        max_chain_oi=500000,
        max_chain_vol=20000
    )
    assert "Bearish" in sentiment
    assert conf >= 50

def test_sentiment_static_concentration_call_dominant():
    # Buildup is Neutral, but Call OI is significantly greater than Put OI
    sentiment, conf = classify_option_sentiment(
        option_type="call",
        oi=300000,
        oi_change=0,
        volume=100,
        ltp=50.0,
        gex=15000000.0,
        buildup="Neutral",
        opponent_oi=50000,
        opponent_gex=2500000.0,
        strike_price=2500.0,
        spot_price=2400.0,
        max_chain_oi=400000,
        max_chain_vol=10000
    )
    # Since Call OI is 6x Put OI and above spot -> Strong Bearish
    assert sentiment == "Strong Bearish"

def test_sentiment_static_concentration_put_dominant():
    # Buildup is Neutral, Put OI is 5x Call OI and below spot -> Strong Bullish
    sentiment, conf = classify_option_sentiment(
        option_type="put",
        oi=250000,
        oi_change=0,
        volume=200,
        ltp=15.0,
        gex=3750000.0,
        buildup="Neutral",
        opponent_oi=40000,
        opponent_gex=800000.0,
        strike_price=2200.0,
        spot_price=2300.0,
        max_chain_oi=300000,
        max_chain_vol=5000
    )
    assert sentiment == "Strong Bullish"
