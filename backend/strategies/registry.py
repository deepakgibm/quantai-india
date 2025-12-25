from .ml_trend import MLTrendStrategy

STRATEGIES = {
    "trend_continuation": MLTrendStrategy,
}

def get_strategy(name: str):
    return STRATEGIES.get(name)
