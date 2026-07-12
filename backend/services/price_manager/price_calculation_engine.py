class PriceCalculationEngine:
    """
    Centralized calculator for absolute changes, percentage changes, gaps,
    and base indicator pricing values.
    """

    def calculate_change(self, ltp: float, prev_close: float) -> float:
        return ltp - prev_close

    def calculate_change_percent(self, ltp: float, prev_close: float) -> float:
        if prev_close <= 0.0:
            return 0.0
        return ((ltp - prev_close) / prev_close) * 100.0

    def calculate_gap(self, open_price: float, prev_close: float) -> float:
        if prev_close <= 0.0:
            return 0.0
        return ((open_price - prev_close) / prev_close) * 100.0

    def get_typical_price(self, high: float, low: float, close: float) -> float:
        return (high + low + close) / 3.0

_price_calculation_engine = None

def get_price_calculation_engine() -> PriceCalculationEngine:
    global _price_calculation_engine
    if _price_calculation_engine is None:
        _price_calculation_engine = PriceCalculationEngine()
    return _price_calculation_engine
