"""
Core Exceptions for QuantAI India
Defines centralized custom exceptions used across backend services.
"""

class DataUnavailableError(Exception):
    """
    Exception raised when required market data (OHLCV, etc.) is unavailable
    or fails validation checks. Ensures the system fails fast rather than
    resorting to dummy or simulated data in production.
    """
    def __init__(self, message: str, symbol: str = None, required_candles: int = None, available_candles: int = None):
        self.message = message
        self.symbol = symbol
        self.required_candles = required_candles
        self.available_candles = available_candles
        super().__init__(self.message)
