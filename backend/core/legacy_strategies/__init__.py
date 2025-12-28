# Core Strategies Package
from .base_strategy import BaseStrategy, Signal
from .ma_crossover import MACrossoverStrategy
from .rsi_mean_reversion import RSIMeanReversionStrategy
from .macd_crossover import MACDCrossoverStrategy
from .supertrend import SupertrendStrategy
from .bollinger_squeeze import BollingerSqueezeStrategy
from .stochastic import StochasticStrategy
from .adx_trend import ADXTrendStrategy
from .volume_breakout import VolumeBreakoutStrategy
from .ichimoku import IchimokuStrategy

# Strategy registry for easy access
AVAILABLE_STRATEGIES = {
    'MACrossover': MACrossoverStrategy,
    'RSIMeanReversion': RSIMeanReversionStrategy,
    'MACDCrossover': MACDCrossoverStrategy,
    'Supertrend': SupertrendStrategy,
    'BollingerSqueeze': BollingerSqueezeStrategy,
    'Stochastic': StochasticStrategy,
    'ADXTrend': ADXTrendStrategy,
    'VolumeBreakout': VolumeBreakoutStrategy,
    'Ichimoku': IchimokuStrategy,
}

def get_strategy(name: str, params: dict = None):
    """Get strategy class by name"""
    strategy_class = AVAILABLE_STRATEGIES.get(name)
    if strategy_class:
        return strategy_class(params)
    raise ValueError(f"Unknown strategy: {name}")

def list_strategies():
    """List all available strategies with metadata"""
    result = []
    for name, cls in AVAILABLE_STRATEGIES.items():
        instance = cls()
        result.append({
            'name': instance.name,
            'description': instance.__class__.__doc__.split('\n')[1].strip() if instance.__class__.__doc__ else '',
            'version': instance.version,
            'default_params': getattr(cls, 'DEFAULT_PARAMS', {}),
        })
    return result
