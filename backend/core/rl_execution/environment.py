"""
Trading Environment for RL Agent
Gym-compatible environment for order execution optimization
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExecutionAction(Enum):
    """Possible execution actions"""
    MARKET_ORDER = 0  # Execute immediately at market
    LIMIT_AGGRESSIVE = 1  # Limit at bid+spread for buy, ask-spread for sell
    LIMIT_PASSIVE = 2  # Limit at bid for buy, ask for sell
    WAIT = 3  # Do nothing this step
    TWAP_START = 4  # Start TWAP execution
    VWAP_START = 5  # Start VWAP execution


@dataclass
class MarketState:
    """Current market state observation"""
    timestamp: datetime
    
    # Price data
    bid: float
    ask: float
    mid: float
    spread: float
    spread_bps: float
    
    # Volume data
    bid_size: int
    ask_size: int
    volume_imbalance: float  # (bid_size - ask_size) / (bid_size + ask_size)
    
    # Recent activity
    last_trade_price: float
    last_trade_size: int
    vwap_5min: float
    volatility_5min: float
    
    # Order book depth
    book_depth_bid: float  # Total bid volume in top 5 levels
    book_depth_ask: float  # Total ask volume in top 5 levels
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for RL agent"""
        return np.array([
            self.mid,
            self.spread_bps,
            self.volume_imbalance,
            self.vwap_5min,
            self.volatility_5min,
            self.book_depth_bid / (self.book_depth_bid + self.book_depth_ask + 1e-6),
        ], dtype=np.float32)


@dataclass
class ExecutionState:
    """Current execution state"""
    # Target
    target_quantity: int
    executed_quantity: int
    remaining_quantity: int
    
    # Performance
    avg_fill_price: float
    slippage_bps: float  # vs arrival price
    execution_progress: float  # 0 to 1
    
    # Time
    elapsed_seconds: float
    remaining_seconds: float
    time_progress: float  # 0 to 1
    
    # Urgency
    urgency_factor: float  # Higher = need to complete faster
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array"""
        return np.array([
            self.execution_progress,
            self.time_progress,
            self.slippage_bps / 100,  # Normalize
            self.urgency_factor,
            self.remaining_quantity / (self.target_quantity + 1e-6),
        ], dtype=np.float32)


class TradingEnvironment:
    """
    Gym-style environment for RL order execution
    
    State: Market microstructure + execution progress
    Action: Discrete execution decisions
    Reward: Negative slippage + completion bonus
    
    This environment simulates order execution optimization
    for minimizing implementation shortfall.
    """
    
    # Observation space dimensions
    MARKET_STATE_DIM = 6
    EXECUTION_STATE_DIM = 5
    OBSERVATION_DIM = MARKET_STATE_DIM + EXECUTION_STATE_DIM
    
    # Action space
    N_ACTIONS = 6
    
    def __init__(
        self,
        target_quantity: int = 1000,
        time_horizon_seconds: float = 300.0,  # 5 minutes
        step_interval_seconds: float = 1.0,
        urgency: float = 0.5
    ):
        self.target_quantity = target_quantity
        self.time_horizon = time_horizon_seconds
        self.step_interval = step_interval_seconds
        self.urgency = urgency
        
        # State
        self._market_data: List[Dict] = []
        self._current_step = 0
        self._executed_qty = 0
        self._total_cost = 0.0
        self._arrival_price = 0.0
        self._done = False
        
        # Metrics
        self._fill_history: List[Dict] = []
    
    def reset(
        self,
        market_data: List[Dict],
        arrival_price: Optional[float] = None
    ) -> np.ndarray:
        """
        Reset environment with new market data
        
        Args:
            market_data: List of OHLCV + bid/ask data
            arrival_price: Decision price (default: first mid)
            
        Returns:
            Initial observation
        """
        self._market_data = market_data
        self._current_step = 0
        self._executed_qty = 0
        self._total_cost = 0.0
        self._fill_history = []
        self._done = False
        
        if market_data:
            first = market_data[0]
            self._arrival_price = arrival_price or (
                (first.get('bid', first['close']) + first.get('ask', first['close'])) / 2
            )
        else:
            self._arrival_price = 0
        
        return self._get_observation()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one step in the environment
        
        Args:
            action: Action index from ExecutionAction
            
        Returns:
            observation, reward, done, info
        """
        if self._done:
            return self._get_observation(), 0.0, True, {}
        
        action_enum = ExecutionAction(action)
        current_data = self._market_data[self._current_step]
        
        # Execute action
        fill_qty, fill_price, fill_cost = self._execute_action(action_enum, current_data)
        
        if fill_qty > 0:
            self._executed_qty += fill_qty
            self._total_cost += fill_cost
            self._fill_history.append({
                'step': self._current_step,
                'action': action_enum.name,
                'quantity': fill_qty,
                'price': fill_price,
                'cost': fill_cost
            })
        
        # Calculate reward
        reward = self._calculate_reward(fill_qty, fill_price, action_enum)
        
        # Advance step
        self._current_step += 1
        
        # Check termination
        if self._executed_qty >= self.target_quantity:
            self._done = True
        elif self._current_step >= len(self._market_data):
            self._done = True
        elif self._current_step * self.step_interval >= self.time_horizon:
            self._done = True
        
        # Get observation
        obs = self._get_observation()
        
        # Info for logging
        info = {
            'executed_qty': self._executed_qty,
            'remaining_qty': max(0, self.target_quantity - self._executed_qty),
            'avg_price': self._total_cost / max(1, self._executed_qty),
            'slippage_bps': self._calculate_slippage_bps(),
            'completion_pct': min(100, self._executed_qty / self.target_quantity * 100)
        }
        
        return obs, reward, self._done, info
    
    def _execute_action(
        self,
        action: ExecutionAction,
        data: Dict
    ) -> Tuple[int, float, float]:
        """
        Simulate order execution for given action
        
        Returns: (filled_quantity, fill_price, total_cost)
        """
        remaining = self.target_quantity - self._executed_qty
        
        bid = data.get('bid', data['close'] * 0.999)
        ask = data.get('ask', data['close'] * 1.001)
        mid = (bid + ask) / 2
        spread = ask - bid
        
        volume = data.get('volume', 10000)
        
        if action == ExecutionAction.WAIT:
            return 0, 0.0, 0.0
        
        elif action == ExecutionAction.MARKET_ORDER:
            # Execute all remaining at market (worst price)
            qty = min(remaining, int(volume * 0.1))  # Max 10% of volume
            price = ask * 1.001  # Slight slippage
            return qty, price, qty * price
        
        elif action == ExecutionAction.LIMIT_AGGRESSIVE:
            # Likely to fill, slight improvement over market
            qty = min(remaining, int(volume * 0.05))
            fill_prob = 0.8  # High fill probability
            if np.random.random() < fill_prob:
                price = ask - spread * 0.25
                return qty, price, qty * price
            return 0, 0.0, 0.0
        
        elif action == ExecutionAction.LIMIT_PASSIVE:
            # May not fill, but better price
            qty = min(remaining, int(volume * 0.03))
            fill_prob = 0.4  # Lower fill probability
            if np.random.random() < fill_prob:
                price = bid + spread * 0.1
                return qty, price, qty * price
            return 0, 0.0, 0.0
        
        elif action == ExecutionAction.TWAP_START:
            # Execute fixed chunk (TWAP slice)
            time_remaining = (len(self._market_data) - self._current_step) + 1
            qty = min(remaining, max(1, remaining // time_remaining))
            price = mid
            return qty, price, qty * price
        
        elif action == ExecutionAction.VWAP_START:
            # Volume-weighted execution
            qty = min(remaining, int(volume * 0.02))
            price = mid * 0.9999  # Slight improvement
            return qty, price, qty * price
        
        return 0, 0.0, 0.0
    
    def _calculate_reward(
        self,
        fill_qty: int,
        fill_price: float,
        action: ExecutionAction
    ) -> float:
        """
        Calculate reward for the step
        
        Reward = -slippage_cost + completion_bonus - urgency_penalty
        """
        reward = 0.0
        
        if fill_qty > 0:
            # Negative slippage cost
            slippage = (fill_price - self._arrival_price) / self._arrival_price
            reward -= slippage * fill_qty * 100  # Scale
            
            # Progress bonus
            progress = fill_qty / self.target_quantity
            reward += progress * 10
        
        # Waiting penalty (opportunity cost)
        if action == ExecutionAction.WAIT:
            time_progress = self._current_step * self.step_interval / self.time_horizon
            remaining_pct = 1 - (self._executed_qty / self.target_quantity)
            
            # Higher penalty as time runs out with remaining quantity
            urgency_penalty = self.urgency * time_progress * remaining_pct
            reward -= urgency_penalty
        
        # Completion bonus
        if self._executed_qty >= self.target_quantity:
            time_efficiency = 1 - (self._current_step * self.step_interval / self.time_horizon)
            reward += 50 * (1 + time_efficiency)
        
        # Penalty for not completing
        if self._done and self._executed_qty < self.target_quantity:
            shortfall = (self.target_quantity - self._executed_qty) / self.target_quantity
            reward -= shortfall * 100
        
        return reward
    
    def _calculate_slippage_bps(self) -> float:
        """Calculate slippage in basis points vs arrival"""
        if self._executed_qty == 0:
            return 0.0
        
        avg_price = self._total_cost / self._executed_qty
        slippage = (avg_price - self._arrival_price) / self._arrival_price
        return slippage * 10000  # Convert to bps
    
    def _get_observation(self) -> np.ndarray:
        """Get current observation array"""
        # Market state
        if self._current_step < len(self._market_data):
            data = self._market_data[self._current_step]
            market_obs = self._data_to_market_state(data).to_array()
        else:
            market_obs = np.zeros(self.MARKET_STATE_DIM, dtype=np.float32)
        
        # Execution state
        elapsed = self._current_step * self.step_interval
        exec_state = ExecutionState(
            target_quantity=self.target_quantity,
            executed_quantity=self._executed_qty,
            remaining_quantity=max(0, self.target_quantity - self._executed_qty),
            avg_fill_price=self._total_cost / max(1, self._executed_qty),
            slippage_bps=self._calculate_slippage_bps(),
            execution_progress=self._executed_qty / self.target_quantity,
            elapsed_seconds=elapsed,
            remaining_seconds=max(0, self.time_horizon - elapsed),
            time_progress=min(1.0, elapsed / self.time_horizon),
            urgency_factor=self.urgency
        )
        exec_obs = exec_state.to_array()
        
        return np.concatenate([market_obs, exec_obs])
    
    def _data_to_market_state(self, data: Dict) -> MarketState:
        """Convert data dict to MarketState"""
        bid = data.get('bid', data['close'] * 0.999)
        ask = data.get('ask', data['close'] * 1.001)
        mid = (bid + ask) / 2
        spread = ask - bid
        
        return MarketState(
            timestamp=data.get('timestamp', datetime.now()),
            bid=bid,
            ask=ask,
            mid=mid,
            spread=spread,
            spread_bps=spread / mid * 10000,
            bid_size=data.get('bid_size', 1000),
            ask_size=data.get('ask_size', 1000),
            volume_imbalance=0.0,
            last_trade_price=data.get('close', mid),
            last_trade_size=data.get('volume', 1000) // 100,
            vwap_5min=data.get('vwap', mid),
            volatility_5min=data.get('volatility', 0.01),
            book_depth_bid=data.get('book_depth_bid', 10000),
            book_depth_ask=data.get('book_depth_ask', 10000)
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics"""
        return {
            'target_quantity': self.target_quantity,
            'executed_quantity': self._executed_qty,
            'completion_pct': self._executed_qty / self.target_quantity * 100,
            'avg_fill_price': self._total_cost / max(1, self._executed_qty),
            'arrival_price': self._arrival_price,
            'slippage_bps': self._calculate_slippage_bps(),
            'total_cost': self._total_cost,
            'n_fills': len(self._fill_history),
            'steps_taken': self._current_step,
            'fill_history': self._fill_history
        }
