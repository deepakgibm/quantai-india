"""
Timeframe Conversion Utilities

Converts between text-based timeframes (e.g., '5m', '1d') and 
numeric timeframes in minutes (5, 1440) for the new schema.
"""



# Mapping from text timeframe to minutes
TIMEFRAME_TO_MINUTES = {
    # Standard formats
    '1m': 1,
    '3m': 3,
    '5m': 5,
    '15m': 15,
    '30m': 30,
    '1h': 60,
    '4h': 240,
    '1d': 1440,
    
    # Alternative formats (for backward compatibility)
    '1minute': 1,
    '5minute': 5,
    '15minute': 15,
    '30minute': 30,
    '1hour': 60,
    '1day': 1440,
    
    # Upstox formats
    'minute': 1,
    'day': 1440,
    'week': 10080,  # 7 * 1440
    'month': 43200,  # 30 * 1440
}

# Mapping from minutes to text (canonical form)
MINUTES_TO_TIMEFRAME = {
    1: '1m',
    3: '3m',
    5: '5m',
    15: '15m',
    30: '30m',
    60: '1h',
    240: '4h',
    1440: '1d',
    10080: '1w',
    43200: '1M',
}


def text_to_minutes(timeframe_text: str) -> int:
    """
    Convert text timeframe to minutes.
    
    Args:
        timeframe_text: Text representation (e.g., '5m', '1d', '1hour')
    
    Returns:
        Timeframe in minutes
    
    Raises:
        ValueError: If timeframe is not recognized
    
    Examples:
        >>> text_to_minutes('5m')
        5
        >>> text_to_minutes('1d')
        1440
        >>> text_to_minutes('1hour')
        60
    """
    tf_lower = timeframe_text.lower().strip()
    
    if tf_lower in TIMEFRAME_TO_MINUTES:
        return TIMEFRAME_TO_MINUTES[tf_lower]
    
    # Try to parse numeric prefix (e.g., '15m' -> 15)
    # Handle cases like '15min', '15minute', '15minutes'
    import re
    match = re.match(r'^(\d+)\s*(m|min|minute|minutes|h|hour|hours|d|day|days)$', tf_lower)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        
        if unit in ('m', 'min', 'minute', 'minutes'):
            return value
        elif unit in ('h', 'hour', 'hours'):
            return value * 60
        elif unit in ('d', 'day', 'days'):
            return value * 1440
    
    raise ValueError(f"Unknown timeframe format: {timeframe_text}")


def minutes_to_text(minutes: int) -> str:
    """
    Convert minutes to text timeframe.
    
    Args:
        minutes: Timeframe in minutes (e.g., 5, 60, 1440)
    
    Returns:
        Text representation (e.g., '5m', '1h', '1d')
    
    Raises:
        ValueError: If minutes value is not a standard timeframe
    
    Examples:
        >>> minutes_to_text(5)
        '5m'
        >>> minutes_to_text(1440)
        '1d'
    """
    if minutes in MINUTES_TO_TIMEFRAME:
        return MINUTES_TO_TIMEFRAME[minutes]
    
    # Handle non-standard values by computing appropriate unit
    if minutes < 60:
        return f'{minutes}m'
    elif minutes < 1440:
        if minutes % 60 == 0:
            return f'{minutes // 60}h'
        return f'{minutes}m'
    else:
        if minutes % 1440 == 0:
            return f'{minutes // 1440}d'
        return f'{minutes}m'


def is_intraday(timeframe_minutes: int) -> bool:
    """
    Check if timeframe is intraday (less than 1 day).
    
    Args:
        timeframe_minutes: Timeframe in minutes
    
    Returns:
        True if intraday, False otherwise
    """
    return timeframe_minutes < 1440


def is_valid_timeframe(timeframe_text: str) -> bool:
    """
    Check if a text timeframe is valid/recognized.
    
    Args:
        timeframe_text: Text representation
    
    Returns:
        True if valid, False otherwise
    """
    try:
        text_to_minutes(timeframe_text)
        return True
    except ValueError:
        return False


def normalize_timeframe(timeframe_text: str) -> str:
    """
    Normalize a timeframe to its canonical text form.
    
    Args:
        timeframe_text: Any valid text representation
    
    Returns:
        Canonical form (e.g., '5m', '1h', '1d')
    
    Examples:
        >>> normalize_timeframe('5minute')
        '5m'
        >>> normalize_timeframe('1day')
        '1d'
        >>> normalize_timeframe('1hour')
        '1h'
    """
    minutes = text_to_minutes(timeframe_text)
    return minutes_to_text(minutes)


# Standard timeframes used in the application
STANDARD_TIMEFRAMES = [1, 5, 15, 30, 60, 1440]  # 1m, 5m, 15m, 30m, 1h, 1d
STANDARD_TIMEFRAMES_TEXT = ['1m', '5m', '15m', '30m', '1h', '1d']
