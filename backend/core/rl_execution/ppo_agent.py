"""
PPO Agent for Order Execution
Custom Proximal Policy Optimization implementation
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
import logging
import pickle

logger = logging.getLogger(__name__)


@dataclass
class PPOConfig:
    """PPO Hyperparameters"""
    # Network architecture
    hidden_sizes: Tuple[int, ...] = (64, 64)
    activation: str = "tanh"
    
    # PPO specific
    clip_ratio: float = 0.2
    target_kl: float = 0.01
    
    # Training
    learning_rate: float = 3e-4
    gamma: float = 0.99  # Discount factor
    gae_lambda: float = 0.95  # GAE parameter
    
    # Batching
    batch_size: int = 64
    n_epochs: int = 10
    
    # Entropy
    entropy_coef: float = 0.01
    value_coef: float = 0.5


class SimpleNeuralNetwork:
    """
    Simple numpy-based neural network for PPO
    (No external ML dependencies required)
    """
    
    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        hidden_sizes: Tuple[int, ...] = (64, 64),
        activation: str = "tanh"
    ):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_sizes = hidden_sizes
        
        # Initialize weights
        self.weights = []
        self.biases = []
        
        prev_dim = input_dim
        for hidden_dim in hidden_sizes:
            # Xavier initialization
            w = np.random.randn(prev_dim, hidden_dim) * np.sqrt(2.0 / prev_dim)
            b = np.zeros(hidden_dim)
            self.weights.append(w)
            self.biases.append(b)
            prev_dim = hidden_dim
        
        # Output layer
        w = np.random.randn(prev_dim, output_dim) * 0.01
        b = np.zeros(output_dim)
        self.weights.append(w)
        self.biases.append(b)
        
        self.activation = activation
    
    def _activate(self, x: np.ndarray) -> np.ndarray:
        """Apply activation function"""
        if self.activation == "tanh":
            return np.tanh(x)
        elif self.activation == "relu":
            return np.maximum(0, x)
        else:
            return x
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass"""
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            x = x @ w + b
            if i < len(self.weights) - 1:  # No activation on output
                x = self._activate(x)
        return x
    
    def get_params(self) -> List[np.ndarray]:
        """Get all parameters"""
        params = []
        for w, b in zip(self.weights, self.biases):
            params.extend([w, b])
        return params
    
    def set_params(self, params: List[np.ndarray]) -> None:
        """Set all parameters"""
        idx = 0
        for i in range(len(self.weights)):
            self.weights[i] = params[idx]
            self.biases[i] = params[idx + 1]
            idx += 2


class PPOAgent:
    """
    Proximal Policy Optimization agent for execution
    
    Uses actor-critic architecture:
    - Actor: Policy network (state -> action probabilities)
    - Critic: Value network (state -> state value)
    """
    
    def __init__(
        self,
        obs_dim: int,
        n_actions: int,
        config: Optional[PPOConfig] = None
    ):
        self.obs_dim = obs_dim
        self.n_actions = n_actions
        self.config = config or PPOConfig()
        
        # Networks
        self.actor = SimpleNeuralNetwork(
            obs_dim, n_actions, self.config.hidden_sizes, self.config.activation
        )
        self.critic = SimpleNeuralNetwork(
            obs_dim, 1, self.config.hidden_sizes, self.config.activation
        )
        
        # Experience buffer
        self.buffer = {
            'observations': [],
            'actions': [],
            'rewards': [],
            'values': [],
            'log_probs': [],
            'dones': []
        }
        
        # Training stats
        self.training_stats = {
            'policy_loss': [],
            'value_loss': [],
            'entropy': [],
            'kl_divergence': []
        }
    
    def get_action(
        self,
        observation: np.ndarray,
        deterministic: bool = False
    ) -> Tuple[int, float]:
        """
        Select action given observation
        
        Args:
            observation: State observation
            deterministic: If True, select argmax action
            
        Returns:
            action, log_probability
        """
        obs = observation.reshape(1, -1)
        
        # Get action logits
        logits = self.actor.forward(obs)[0]
        
        # Softmax for probabilities
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / (exp_logits.sum() + 1e-8)
        
        if deterministic:
            action = np.argmax(probs)
        else:
            action = np.random.choice(self.n_actions, p=probs)
        
        log_prob = np.log(probs[action] + 1e-8)
        
        return int(action), float(log_prob)
    
    def get_value(self, observation: np.ndarray) -> float:
        """Get value estimate for state"""
        obs = observation.reshape(1, -1)
        value = self.critic.forward(obs)[0, 0]
        return float(value)
    
    def store_transition(
        self,
        obs: np.ndarray,
        action: int,
        reward: float,
        value: float,
        log_prob: float,
        done: bool
    ) -> None:
        """Store transition in buffer"""
        self.buffer['observations'].append(obs)
        self.buffer['actions'].append(action)
        self.buffer['rewards'].append(reward)
        self.buffer['values'].append(value)
        self.buffer['log_probs'].append(log_prob)
        self.buffer['dones'].append(done)
    
    def compute_returns_and_advantages(
        self,
        last_value: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute returns and GAE advantages
        """
        rewards = np.array(self.buffer['rewards'])
        values = np.array(self.buffer['values'])
        dones = np.array(self.buffer['dones'])
        
        n_steps = len(rewards)
        advantages = np.zeros(n_steps)
        returns = np.zeros(n_steps)
        
        # GAE calculation
        gae = 0
        for t in reversed(range(n_steps)):
            if t == n_steps - 1:
                next_value = last_value
                next_done = 1
            else:
                next_value = values[t + 1]
                next_done = dones[t + 1]
            
            delta = rewards[t] + self.config.gamma * next_value * (1 - next_done) - values[t]
            gae = delta + self.config.gamma * self.config.gae_lambda * (1 - next_done) * gae
            advantages[t] = gae
            returns[t] = gae + values[t]
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        return returns, advantages
    
    def update(self) -> Dict[str, float]:
        """
        Perform PPO update
        
        Returns training statistics
        """
        if len(self.buffer['observations']) == 0:
            return {}
        
        # Get data
        observations = np.array(self.buffer['observations'])
        actions = np.array(self.buffer['actions'])
        old_log_probs = np.array(self.buffer['log_probs'])
        
        # Compute returns and advantages
        last_obs = observations[-1]
        last_value = self.get_value(last_obs)
        returns, advantages = self.compute_returns_and_advantages(last_value)
        
        # Simple gradient-free optimization (evolutionary)
        # In production, use proper gradient descent
        best_actor_params = self.actor.get_params()
        best_critic_params = self.critic.get_params()
        best_loss = float('inf')
        
        for epoch in range(self.config.n_epochs):
            # Perturb parameters slightly
            actor_params = [p + np.random.randn(*p.shape) * 0.01 for p in best_actor_params]
            critic_params = [p + np.random.randn(*p.shape) * 0.01 for p in best_critic_params]
            
            self.actor.set_params(actor_params)
            self.critic.set_params(critic_params)
            
            # Compute loss
            policy_loss = 0
            value_loss = 0
            
            for i in range(len(observations)):
                obs = observations[i].reshape(1, -1)
                
                # Policy loss
                logits = self.actor.forward(obs)[0]
                exp_logits = np.exp(logits - np.max(logits))
                probs = exp_logits / (exp_logits.sum() + 1e-8)
                new_log_prob = np.log(probs[actions[i]] + 1e-8)
                
                ratio = np.exp(new_log_prob - old_log_probs[i])
                clipped_ratio = np.clip(ratio, 1 - self.config.clip_ratio, 1 + self.config.clip_ratio)
                
                policy_loss -= min(ratio * advantages[i], clipped_ratio * advantages[i])
                
                # Value loss
                value_pred = self.critic.forward(obs)[0, 0]
                value_loss += (value_pred - returns[i]) ** 2
            
            total_loss = policy_loss + self.config.value_coef * value_loss
            
            if total_loss < best_loss:
                best_loss = total_loss
                best_actor_params = actor_params
                best_critic_params = critic_params
        
        # Set best parameters
        self.actor.set_params(best_actor_params)
        self.critic.set_params(best_critic_params)
        
        # Clear buffer
        for key in self.buffer:
            self.buffer[key] = []
        
        stats = {
            'policy_loss': float(policy_loss / len(observations)),
            'value_loss': float(value_loss / len(observations)),
            'n_samples': len(observations)
        }
        
        self.training_stats['policy_loss'].append(stats['policy_loss'])
        self.training_stats['value_loss'].append(stats['value_loss'])
        
        return stats
    
    def save(self, path: str) -> None:
        """Save agent to file"""
        data = {
            'actor_weights': self.actor.weights,
            'actor_biases': self.actor.biases,
            'critic_weights': self.critic.weights,
            'critic_biases': self.critic.biases,
            'config': self.config,
            'obs_dim': self.obs_dim,
            'n_actions': self.n_actions
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Agent saved to {path}")
    
    def load(self, path: str) -> None:
        """Load agent from file"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        self.actor.weights = data['actor_weights']
        self.actor.biases = data['actor_biases']
        self.critic.weights = data['critic_weights']
        self.critic.biases = data['critic_biases']
        self.config = data['config']
        
        logger.info(f"Agent loaded from {path}")


class ExecutionTrainer:
    """
    Training loop for RL execution agent
    """
    
    def __init__(
        self,
        env,  # TradingEnvironment
        agent: PPOAgent,
        n_episodes: int = 1000,
        log_interval: int = 100
    ):
        self.env = env
        self.agent = agent
        self.n_episodes = n_episodes
        self.log_interval = log_interval
        
        # Training history
        self.episode_rewards = []
        self.episode_slippages = []
        self.episode_completions = []
    
    def train(self, market_data_samples: List[List[Dict]]) -> Dict[str, Any]:
        """
        Train the agent on market data samples
        
        Args:
            market_data_samples: List of market data episodes
            
        Returns:
            Training summary
        """
        logger.info(f"Starting training for {self.n_episodes} episodes")
        
        for episode in range(self.n_episodes):
            # Select random market data
            market_data = market_data_samples[episode % len(market_data_samples)]
            
            # Reset environment
            obs = self.env.reset(market_data)
            episode_reward = 0
            done = False
            
            while not done:
                # Get action
                action, log_prob = self.agent.get_action(obs)
                value = self.agent.get_value(obs)
                
                # Step environment
                next_obs, reward, done, info = self.env.step(action)
                
                # Store transition
                self.agent.store_transition(obs, action, reward, value, log_prob, done)
                
                episode_reward += reward
                obs = next_obs
            
            # Update agent
            if (episode + 1) % 10 == 0:
                self.agent.update()
            
            # Log metrics
            metrics = self.env.get_metrics()
            self.episode_rewards.append(episode_reward)
            self.episode_slippages.append(metrics['slippage_bps'])
            self.episode_completions.append(metrics['completion_pct'])
            
            if (episode + 1) % self.log_interval == 0:
                avg_reward = np.mean(self.episode_rewards[-self.log_interval:])
                avg_slippage = np.mean(self.episode_slippages[-self.log_interval:])
                avg_completion = np.mean(self.episode_completions[-self.log_interval:])
                
                logger.info(
                    f"Episode {episode + 1}: "
                    f"Reward={avg_reward:.2f}, "
                    f"Slippage={avg_slippage:.2f}bps, "
                    f"Completion={avg_completion:.1f}%"
                )
        
        return {
            'n_episodes': self.n_episodes,
            'final_avg_reward': np.mean(self.episode_rewards[-100:]),
            'final_avg_slippage': np.mean(self.episode_slippages[-100:]),
            'final_avg_completion': np.mean(self.episode_completions[-100:])
        }
    
    def evaluate(
        self,
        market_data_samples: List[List[Dict]],
        n_episodes: int = 100
    ) -> Dict[str, Any]:
        """Evaluate agent performance"""
        rewards = []
        slippages = []
        completions = []
        
        for episode in range(n_episodes):
            market_data = market_data_samples[episode % len(market_data_samples)]
            obs = self.env.reset(market_data)
            done = False
            ep_reward = 0
            
            while not done:
                action, _ = self.agent.get_action(obs, deterministic=True)
                obs, reward, done, _ = self.env.step(action)
                ep_reward += reward
            
            metrics = self.env.get_metrics()
            rewards.append(ep_reward)
            slippages.append(metrics['slippage_bps'])
            completions.append(metrics['completion_pct'])
        
        return {
            'mean_reward': np.mean(rewards),
            'std_reward': np.std(rewards),
            'mean_slippage_bps': np.mean(slippages),
            'std_slippage_bps': np.std(slippages),
            'mean_completion_pct': np.mean(completions),
            'n_episodes': n_episodes
        }
