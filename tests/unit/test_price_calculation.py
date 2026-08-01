import pytest
from services.price_manager.price_calculation_engine import PriceCalculationEngine

@pytest.fixture
def calc_engine():
    return PriceCalculationEngine()

def test_calculate_change(calc_engine):
    assert calc_engine.calculate_change(150.0, 100.0) == 50.0
    assert calc_engine.calculate_change(90.0, 100.0) == -10.0
    assert calc_engine.calculate_change(100.0, 100.0) == 0.0

def test_calculate_change_percent(calc_engine):
    assert calc_engine.calculate_change_percent(150.0, 100.0) == 50.0
    assert calc_engine.calculate_change_percent(90.0, 100.0) == -10.0
    
    # Zero/negative division safety
    assert calc_engine.calculate_change_percent(150.0, 0.0) == 0.0
    assert calc_engine.calculate_change_percent(150.0, -10.0) == 0.0

def test_calculate_gap(calc_engine):
    assert calc_engine.calculate_gap(105.0, 100.0) == 5.0
    assert calc_engine.calculate_gap(95.0, 100.0) == -5.0
    
    # Zero/negative division safety
    assert calc_engine.calculate_gap(105.0, 0.0) == 0.0

def test_get_typical_price(calc_engine):
    assert calc_engine.get_typical_price(105.0, 95.0, 100.0) == 100.0
    assert calc_engine.get_typical_price(10.0, 5.0, 6.0) == 7.0
