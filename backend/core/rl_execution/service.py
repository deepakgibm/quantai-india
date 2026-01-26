"""
RL Execution Service
High-level API for using the RL execution agent
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
import os

from .environment import TradingEnvironment
from .ppo_agent import PPOAgent, ExecutionTrainer

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRequest:
    """Request for RL-optimized execution"""
    symbol: str
    quantity: int
    side: str  # 'BUY' or 'SELL'
    urgency: float = 0.5  # 0 = patient, 1 = urgent
    time_horizon_seconds: float = 300.0


@dataclass
class ExecutionResult:
    """Result of RL-optimized execution"""
    symbol: str
    target_quantity: int
    executed_quantity: int
    avg_fill_price: float
    slippage_bps: float
    completion_pct: float
    n_fills: int
    actions_taken: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'target_quantity': self.target_quantity,
            'executed_quantity': self.executed_quantity,
            'avg_fill_price': round(self.avg_fill_price, 2),
            'slippage_bps': round(self.slippage_bps, 2),
            'completion_pct': round(self.completion_pct, 2),
            'n_fills': self.n_fills,
            'actions_taken': self.actions_taken
        }


class RLExecutionService:
    """
    Service for RL-optimized order execution
    
    Features:
    - Pre-trained PPO agent for execution decisions
    - Adapts to market microstructure
    - Minimizes implementation shortfall
    """
    
    MODEL_PATH = "models/rl_execution_agent.pkl"
    
    def __init__(self):
        self.env = TradingEnvironment()
        self.agent = PPOAgent(
            obs_dim=TradingEnvironment.OBSERVATION_DIM,
            n_actions=TradingEnvironment.N_ACTIONS
        )
        self._is_trained = False
    
    def load_model(self, path: Optional[str] = None) -> bool:
        """Load pre-trained model"""
        model_path = path or self.MODEL_PATH
        
        if os.path.exists(model_path):
            try:
                self.agent.load(model_path)
                self._is_trained = True
                logger.info(f"Loaded RL model from {model_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return False
        return False
    
    def save_model(self, path: Optional[str] = None) -> bool:
        """Save trained model"""
        model_path = path or self.MODEL_PATH
        
        try:
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            self.agent.save(model_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def train(
        self,
        market_data_samples: List[List[Dict]],
        n_episodes: int = 1000
    ) -> Dict[str, Any]:
        """
        Train the RL agent
        
        Args:
            market_data_samples: List of market data episodes
            n_episodes: Number of training episodes
            
        Returns:
            Training summary
        """
        trainer = ExecutionTrainer(
            env=self.env,
            agent=self.agent,
            n_episodes=n_episodes
        )
        
        result = trainer.train(market_data_samples)
        self._is_trained = True
        
        return result
    
    def execute(
        self,
        request: ExecutionRequest,
        market_data: List[Dict]
    ) -> ExecutionResult:
        """
        Execute order using RL agent
        
        Args:
            request: Execution request
            market_data: Current market data stream
            
        Returns:
            Execution result
        """
        # Configure environment
        self.env.target_quantity = request.quantity
        self.env.time_horizon = request.time_horizon_seconds
        self.env.urgency = request.urgency
        
        # Reset with market data
        obs = self.env.reset(market_data)
        
        done = False
        actions_taken = []
        
        while not done:
            # Get action from agent
            action, _ = self.agent.get_action(obs, deterministic=True)
            
            # Step environment
            obs, reward, done, info = self.env.step(action)
            
            # Log action
            from .environment import ExecutionAction
            actions_taken.append(ExecutionAction(action).name)
        
        # Get final metrics
        metrics = self.env.get_metrics()
        
        return ExecutionResult(
            symbol=request.symbol,
            target_quantity=metrics['target_quantity'],
            executed_quantity=metrics['executed_quantity'],
            avg_fill_price=metrics['avg_fill_price'],
            slippage_bps=metrics['slippage_bps'],
            completion_pct=metrics['completion_pct'],
            n_fills=metrics['n_fills'],
            actions_taken=actions_taken
        )
    
    def simulate_execution(
        self,
        symbol: str,
        quantity: int,
        historical_data: List[Dict],
        urgency: float = 0.5
    ) -> Dict[str, Any]:
        """
        Simulate execution on historical data
        
        Returns comparison of RL vs naive execution
        """
        request = ExecutionRequest(
            symbol=symbol,
            quantity=quantity,
            side='BUY',
            urgency=urgency
        )
        
        # RL execution
        rl_result = self.execute(request, historical_data)
        
        # Naive market order (baseline)
        if historical_data:
            naive_price = historical_data[0].get('ask', historical_data[0]['close'])
            arrival_price = (historical_data[0].get('bid', historical_data[0]['close']) + 
                           historical_data[0].get('ask', historical_data[0]['close'])) / 2
            naive_slippage = (naive_price - arrival_price) / arrival_price * 10000
        else:
            naive_slippage = 10.0  # Default 10 bps
        
        return {
            'rl_execution': rl_result.to_dict(),
            'naive_slippage_bps': round(naive_slippage, 2),
            'improvement_bps': round(naive_slippage - rl_result.slippage_bps, 2),
            'is_trained': self._is_trained
        }


# Singleton instance
_rl_service: Optional[RLExecutionService] = None


def get_rl_service() -> RLExecutionService:
    """Get or create RL execution service"""
    global _rl_service
    if _rl_service is None:
        _rl_service = RLExecutionService()
        _rl_service.load_model()  # Try to load pre-trained
    return _rl_service
