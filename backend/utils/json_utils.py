
import math
import logging
from typing import Any
from datetime import datetime, date
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

def sanitize_for_json(data: Any) -> Any:
    """
    Recursively sanitizes data to ensure it is JSON serializable.
    Handles:
    - NaN / Inf values -> None
    - numpy types -> python native types
    - pandas Timestamp -> str (ISO 8601)
    - datetime/date -> str (ISO 8601)
    - Decimal -> float
    """
    # Base cases
    if data is None:
        return None
    
    if isinstance(data, (bool, str)):
        return data
        
    if isinstance(data, (int, float)):
        if math.isnan(data) or math.isinf(data):
            return None
        return data

    # Recursive cases
    if isinstance(data, dict):
        return {k: sanitize_for_json(v) for k, v in data.items()}
    
    if isinstance(data, list):
        return [sanitize_for_json(v) for v in data]
    
    if isinstance(data, tuple):
        return [sanitize_for_json(v) for v in data]
        
    # Numpy types
    if isinstance(data, (np.integer, np.int64, np.int32)):
        return int(data)
        
    if isinstance(data, (np.floating, np.float64, np.float32)):
        if np.isnan(data) or np.isinf(data):
            return None
        return float(data)
        
    if isinstance(data, np.bool_):
        return bool(data)
        
    if isinstance(data, np.ndarray):
        return sanitize_for_json(data.tolist())

    # Pandas/Date types
    if isinstance(data, (pd.Timestamp, datetime, date)):
        return data.isoformat()
        
    # Decimal
    if hasattr(data, "to_decimal"):  # For some specialized types
        return float(data)
        
    try:
        from decimal import Decimal
        if isinstance(data, Decimal):
            return float(data)
    except ImportError:
        pass
        
    # Fallback for unknown objects with to_dict or similar
    if hasattr(data, "dict"):
        return sanitize_for_json(data.dict())
        
    if hasattr(data, "to_dict"):
        return sanitize_for_json(data.to_dict())

    # Final fallback: string representation if everything else fails
    try:
        return str(data)
    except Exception:
        return None
