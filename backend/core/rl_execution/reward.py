"""
RL Reward Functions Module
Custom reward functions for order execution optimization
"""

import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RewardType(Enum):
    """Types of reward functions"""
    SLIPPAGE_ONLY = "slippage"
    EXECUTION_QUALITY = "execution_quality"
    RISK_ADJUSTED = "risk_adjusted"
    COMPOSITE = "composite"


@dataclass
class RewardConfig:
    """Configuration for reward calculation"""
    # Weights for composite reward
    slippage_weight: float = 0.4
    completion_weight: float = 0.3
    drawdown_weight: float = 0.2
    time_penalty_weight: float = 0.1
    
    # Thresholds
    target_slippage_bps: float = 5.0  # Target slippage in bps
    max_acceptable_slippage_bps: float = 20.0
    completion_bonus: float = 50.0
    incomplete_penalty: float = 100.0
    
    # Drawdown penalty
    drawdown_penalty_multiplier: float = 2.0
    
    # Time urgency
    urgency_penalty_start: float = 0.5  # Start penalty at 50% time elapsed


@dataclass
class RewardComponents:
    """Breakdown of reward components"""
    slippage_reward: float
    completion_reward: float
    drawdown_penalty: float
    time_penalty: float
    total_reward: float
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'slippage': round(self.slippage_reward, 4),
            'completion': round(self.completion_reward, 4),
            'drawdown': round(self.drawdown_penalty, 4),
            'time': round(self.time_penalty, 4),
            'total': round(self.total_reward, 4)
        }


class RewardCalculator:
    """
    Calculate rewards for RL execution agent
    
    Objectives:
    - Minimize slippage vs arrival price
    - Minimize drawdown during execution
    - Complete execution within time limit
    - Optimize execution quality
    """
    
    def __init__(self, config: Optional[RewardConfig] = None):
        self.config = config or RewardConfig()
    
    def calculate(
        self,
        fill_price: float,
        arrival_price: float,
        fill_quantity: int,
        target_quantity: int,
        executed_quantity: int,
        elapsed_time_pct: float,  # 0 to 1
        current_drawdown_pct: float = 0.0,
        is_done: bool = False,
        action_type: str = "market"
    ) -> RewardComponents:
        """
        Calculate step reward
        
        Args:
            fill_price: Price of fill
            arrival_price: Decision price
            fill_quantity: Quantity filled this step
            target_quantity: Total target quantity
            executed_quantity: Total executed so far
            elapsed_time_pct: Time elapsed as fraction
            current_drawdown_pct: Current execution drawdown
            is_done: Episode complete?
            action_type: Type of action taken
            
        Returns:
            Reward components breakdown
        """
        # 1. Slippage reward (negative for positive slippage)
        slippage_reward = self._slippage_reward(
            fill_price, arrival_price, fill_quantity, target_quantity
        )
        
        # 2. Completion reward
        completion_reward = self._completion_reward(
            fill_quantity, target_quantity, executed_quantity, is_done
        )
        
        # 3. Drawdown penalty
        drawdown_penalty = self._drawdown_penalty(current_drawdown_pct)
        
        # 4. Time penalty
        time_penalty = self._time_penalty(
            elapsed_time_pct,
            executed_quantity,
            target_quantity
        )
        
        # Combine with weights
        total = (
            self.config.slippage_weight * slippage_reward +
            self.config.completion_weight * completion_reward +
            self.config.drawdown_weight * drawdown_penalty +
            self.config.time_penalty_weight * time_penalty
        )
        
        return RewardComponents(
            slippage_reward=slippage_reward,
            completion_reward=completion_reward,
            drawdown_penalty=drawdown_penalty,
            time_penalty=time_penalty,
            total_reward=total
        )
    
    def _slippage_reward(
        self,
        fill_price: float,
        arrival_price: float,
        fill_quantity: int,
        target_quantity: int
    ) -> float:
        """
        Calculate slippage-based reward
        
        Reward = -slippage_bps * scale
        Better than target = positive reward
        """
        if fill_quantity == 0 or arrival_price == 0:
            return 0.0
        
        slippage_pct = (fill_price - arrival_price) / arrival_price
        slippage_bps = slippage_pct * 10000
        
        # Target slippage comparison
        target_bps = self.config.target_slippage_bps
        
        # Reward: positive if beating target, negative otherwise
        improvement_bps = target_bps - slippage_bps
        
        # Scale by fill size
        size_factor = fill_quantity / target_quantity
        
        # Clip extreme values
        reward = np.clip(improvement_bps * size_factor, -50, 50)
        
        return float(reward)
    
    def _completion_reward(
        self,
        fill_quantity: int,
        target_quantity: int,
        executed_quantity: int,
        is_done: bool
    ) -> float:
        """
        Calculate completion-based reward
        
        Progressive reward for execution progress
        Large bonus/penalty at completion
        """
        reward = 0.0
        
        if fill_quantity > 0:
            # Progress reward
            progress = fill_quantity / target_quantity
            reward += progress * 10
        
        if is_done:
            completion_pct = executed_quantity / target_quantity
            
            if completion_pct >= 1.0:
                # Full completion bonus
                reward += self.config.completion_bonus
            else:
                # Incomplete penalty (scaled by shortfall)
                shortfall = 1.0 - completion_pct
                reward -= self.config.incomplete_penalty * shortfall
        
        return reward
    
    def _drawdown_penalty(self, drawdown_pct: float) -> float:
        """
        Penalize execution drawdown
        
        During execution, unrealized P&L can swing.
        Penalize large negative swings.
        """
        if drawdown_pct <= 0:
            return 0.0
        
        # Quadratic penalty for larger drawdowns
        penalty = -self.config.drawdown_penalty_multiplier * (drawdown_pct ** 2) * 100
        
        return float(penalty)
    
    def _time_penalty(
        self,
        elapsed_pct: float,
        executed_quantity: int,
        target_quantity: int
    ) -> float:
        """
        Penalize slow execution
        
        Penalty increases as time runs out with remaining quantity
        """
        if elapsed_pct < self.config.urgency_penalty_start:
            return 0.0
        
        remaining_pct = 1.0 - (executed_quantity / target_quantity)
        time_over_threshold = elapsed_pct - self.config.urgency_penalty_start
        normalized_time = time_over_threshold / (1 - self.config.urgency_penalty_start)
        
        # Penalty scales with remaining qty and time pressure
        penalty = -remaining_pct * normalized_time * 20
        
        return float(penalty)


class AdaptiveRewardCalculator(RewardCalculator):
    """
    Adaptive reward calculator that adjusts based on market conditions
    """
    
    def __init__(self, config: Optional[RewardConfig] = None):
        super().__init__(config)
        self.volatility_scale = 1.0
        self.spread_scale = 1.0
    
    def update_market_conditions(
        self,
        current_volatility: float,
        baseline_volatility: float,
        current_spread_bps: float,
        baseline_spread_bps: float
    ) -> None:
        """Update scaling based on market conditions"""
        # In high volatility, lower slippage expectations
        self.volatility_scale = baseline_volatility / (current_volatility + 1e-8)
        self.volatility_scale = np.clip(self.volatility_scale, 0.5, 2.0)
        
        # In wide spreads, adjust target slippage
        self.spread_scale = baseline_spread_bps / (current_spread_bps + 1e-8)
        self.spread_scale = np.clip(self.spread_scale, 0.5, 2.0)
    
    def calculate(self, **kwargs) -> RewardComponents:
        """Calculate with adaptive scaling"""
        result = super().calculate(**kwargs)
        
        # Scale slippage reward by market conditions
        result.slippage_reward *= self.volatility_scale * self.spread_scale
        
        # Recalculate total
        result.total_reward = (
            self.config.slippage_weight * result.slippage_reward +
            self.config.completion_weight * result.completion_reward +
            self.config.drawdown_weight * result.drawdown_penalty +
            self.config.time_penalty_weight * result.time_penalty
        )
        
        return result


# VWAP-based reward for benchmark comparison
class VWAPRewardCalculator(RewardCalculator):
    """
    Calculate reward relative to VWAP benchmark
    
    Trading better than VWAP = positive reward
    """
    
    def __init__(self, config: Optional[RewardConfig] = None):
        super().__init__(config)
        self.vwap_prices: List[float] = []
        self.vwap_volumes: List[int] = []
    
    def update_vwap(self, price: float, volume: int) -> None:
        """Add price/volume to VWAP calculation"""
        self.vwap_prices.append(price)
        self.vwap_volumes.append(volume)
    
    def get_vwap(self) -> float:
        """Calculate current VWAP"""
        if not self.vwap_prices:
            return 0.0
        
        total_pv = sum(p * v for p, v in zip(self.vwap_prices, self.vwap_volumes))
        total_v = sum(self.vwap_volumes)
        
        return total_pv / (total_v + 1e-8)
    
    def calculate_vs_vwap(
        self,
        avg_execution_price: float,
        is_buy: bool = True
    ) -> float:
        """
        Calculate reward vs VWAP benchmark
        
        For buy: better = below VWAP
        For sell: better = above VWAP
        """
        vwap = self.get_vwap()
        if vwap == 0:
            return 0.0
        
        diff_bps = (avg_execution_price - vwap) / vwap * 10000
        
        if is_buy:
            # For buy, negative diff is good
            return -diff_bps
        else:
            # For sell, positive diff is good
            return diff_bps
    
    def reset(self) -> None:
        """Reset VWAP calculation"""
        self.vwap_prices = []
        self.vwap_volumes = []
