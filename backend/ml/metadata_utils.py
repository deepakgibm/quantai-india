import os
import json
import logging
from typing import Dict, Optional
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)

class SymbolMapper:
    """
    Manages symbol-to-index mapping for embeddings.
    Persists the mapping to ensure consistency between training and inference.
    """
    def __init__(self, mapper_path: str = None):
        self.mapper_path = mapper_path or os.path.join(settings.BASE_DIR, "data", "symbol_mapper.json")
        self.symbol_to_idx: Dict[str, int] = {}
        self.idx_to_symbol: Dict[int, str] = {}
        self.load()

    def load(self):
        if os.path.exists(self.mapper_path):
            with open(self.mapper_path, 'r') as f:
                self.symbol_to_idx = json.load(f)
                self.idx_to_symbol = {int(v): k for k, v in self.symbol_to_idx.items()}
            logger.info(f"Loaded mapping for {len(self.symbol_to_idx)} symbols.")

    def save(self):
        Path(os.path.dirname(self.mapper_path)).mkdir(parents=True, exist_ok=True)
        with open(self.mapper_path, 'w') as f:
            json.dump(self.symbol_to_idx, f)
        logger.info(f"Saved symbol mapping to {self.mapper_path}")

    def get_idx(self, symbol: str) -> int:
        if symbol not in self.symbol_to_idx:
            idx = len(self.symbol_to_idx)
            self.symbol_to_idx[symbol] = idx
            self.idx_to_symbol[idx] = symbol
            self.save()
        return self.symbol_to_idx[symbol]

    def get_symbol(self, idx: int) -> Optional[str]:
        return self.idx_to_symbol.get(idx)

# Timeframe Mapper
TIMEFRAME_TO_IDX = {
    "1m": 0, "5m": 1, "15m": 2, "30m": 3, "1h": 4, "4h": 5, "1d": 6
}
