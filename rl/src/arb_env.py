"""
Reinforcement Learning Environment for Arbitrage Trading

This environment simulates the arbitrage decision-making process.
The RL agent controls WHEN to trade, HOW MUCH, and WITH WHAT PARAMETERS.
It does NOT directly execute trades - that's the bot's job.
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, Tuple, Optional


class ArbitrageEnv(gym.Env):
    """
    Custom Gymnasium environment for arbitrage strategy optimization
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, simulation_mode: bool = True, gas_multiplier: float = 1.0, initial_capital: float = 100.0):
        super().__init__()
        
        self.simulation_mode = simulation_mode
        self.gas_multiplier = gas_multiplier 
        self.initial_capital = initial_capital  # Now configurable!
        
        # Define observation space (9 features)
        self.observation_space = spaces.Box(
            low=np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            high=np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]),
            dtype=np.float32
        )
        
        # Define action space
        # [threshold, trade_size_idx, strategy_idx, priority_fee, use_flashloan]
        self.action_space = spaces.Box(
            low=np.array([0.0005, 0.0, 0.0, 0.0, 0.0]),
            high=np.array([0.005, 3.0, 3.0, 5.0, 1.0]),
            dtype=np.float32
        )
        
        # Trade size options (in USD)
        self.trade_sizes = [50, 100, 1000, 10000]
        
        # Strategy options
        self.strategies = ['dex_arb', 'triangular', 'backrun', 'liquidation']
        
        # Episode tracking
        self.current_step = 0
        self.max_steps = 1000
        self.total_pnl = 0.0
        self.total_gas_spent = 0.0
        self.num_reverts = 0
        self.num_successes = 0
        
        # State tracking
        self.state = None
        self.reset()
    
    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset the environment to initial state"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.total_pnl = 0.0
        self.total_gas_spent = 0.0
        self.num_reverts = 0
        self.num_successes = 0
        
        # Initialize with random market state
        self.state = self._generate_market_state()
        
        return self.state, {}
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one step in the environment
        """
        self.current_step += 1
        
        # Parse action
        threshold = float(action[0])
        trade_size_idx = int(np.clip(action[1], 0, 3))
        strategy_idx = int(np.clip(action[2], 0, 3))
        priority_fee = float(action[3])
        use_flashloan = action[4] > 0.5
        
        trade_size = self.trade_sizes[trade_size_idx]
        strategy = self.strategies[strategy_idx]
        
        # Check Capital Constraints
        # If not using flash loan, cannot trade more than current capital
        current_capital = self.initial_capital + self.total_pnl
        if not use_flashloan and trade_size > current_capital:
             # Penalize attempting to trade without funds
             return self.state, -10.0, False, False, {
                'pnl': 0.0,
                'gas_cost': 0.0, 
                'success': False,
                'reason': 'insufficient_capital',
                'total_pnl': self.total_pnl,
                'num_successes': self.num_successes,
                'num_reverts': self.num_reverts
            }
        
        # Simulate trade execution
        trade_result = self._simulate_trade(
            threshold=threshold,
            trade_size=trade_size,
            strategy=strategy,
            priority_fee=priority_fee,
            use_flashloan=use_flashloan
        )
        
        # Calculate reward
        reward = self._calculate_reward(trade_result)
        
        # Update state
        self.state = self._generate_market_state()
        
        # Check if episode is done
        terminated = self.total_pnl < -10000  # Daily loss limit
        truncated = self.current_step >= self.max_steps
        
        info = {
            'pnl': trade_result['pnl'],
            'gas_cost': trade_result['gas_cost'],
            'success': trade_result['success'],
            'total_pnl': self.total_pnl,
            'num_successes': self.num_successes,
            'num_reverts': self.num_reverts
        }
        
        return self.state, reward, terminated, truncated, info
    
    def _generate_market_state(self) -> np.ndarray:
        """
        Generate a realistic simulated market state
        """
        # 99% of time, spread is near zero or negative (fees)
        # 1% of time, a small opportunity appears
        if np.random.random() < 0.01:
            # Opportunity: 0.05% to 0.5% spread (rarely higher)
            price_spread = np.random.exponential(0.002)
        else:
            # No opportunity: 0% to 0.05% (eaten by fees)
            price_spread = np.random.uniform(0.0, 0.0005)

        return np.array([
            price_spread,
            np.random.uniform(0.1, 1.0),    # pool_liquidity (1.0 = deep)
            np.random.uniform(0.0, 0.2),    # volatility (lower is normal)
            np.random.uniform(0.2, 0.8),    # gas_price (normalized)
            np.random.uniform(0.5, 1.0),    # mempool_congestion (usually busy)
            self.num_successes / max(1, self.current_step),  # recent_success_rate
            self.num_reverts / max(1, self.current_step),    # recent_reverts
            (self.current_step % 24) / 24.0,  # time_of_day
            np.random.uniform(0.0, 0.1),   # block_time_variance
        ], dtype=np.float32)
    
    def _simulate_trade(
        self,
        threshold: float,
        trade_size: float,
        strategy: str,
        priority_fee: float,
        use_flashloan: bool
    ) -> Dict:
        """
        Simulate realistic trade execution
        """
        # Extract current market conditions
        price_spread = self.state[0]
        liquidity = self.state[1]
        congestion = self.state[4]
        
        # 1. Check Threshold
        if price_spread < threshold:
             return {
                'success': False,
                'pnl': 0.0,
                'gas_cost': 0.0,
                'reverted': False
            }

        # 2. Calculate Costs (Real-world estimates)
        # Base gas: ~150k for swap, ~300k for Flashloan
        base_gas_units = 300000 if use_flashloan else 150000
        
        # Apply GAS MULTIPLIER (For L2 Simulations)
        base_gas_units = base_gas_units * self.gas_multiplier
        
        # Gas Price: 20 gwei base + priority fee
        # ETH Price: $2500
        current_gas_price_gwei = 20 + (priority_fee * 10) # 20-70 gwei
        gas_cost_eth = base_gas_units * current_gas_price_gwei * 1e-9
        gas_cost_usd = gas_cost_eth * 2500

        # 3. Calculate Slippage (Price Impact)
        pool_depth_usd = liquidity * 10_000_000 
        price_impact = (trade_size / pool_depth_usd) ** 1.5
        
        # 4. Flash Loan Fee (0.09% usually, simplified to 0.05%)
        flash_loan_fee = trade_size * 0.0009 if use_flashloan else 0

        # 5. DEX Fees & Profit
        gross_profit = trade_size * price_spread
        slippage_cost = trade_size * price_impact
        net_profit = gross_profit - slippage_cost - gas_cost_usd - flash_loan_fee

        # 6. Competition / MEV Revert Chance
        base_revert_prob = 0.8 if congestion > 0.8 else 0.3
        revert_reduction = (priority_fee / 5.0) * 0.4
        revert_prob = max(0.1, base_revert_prob - revert_reduction)
        
        is_reverted = np.random.random() < revert_prob

        if is_reverted:
            failed_gas_cost = gas_cost_usd * 0.6 
            return {
                'success': False,
                'pnl': -failed_gas_cost,
                'gas_cost': failed_gas_cost,
                'reverted': True
            }

        return {
            'success': True,
            'pnl': net_profit, 
            'gas_cost': gas_cost_usd,
            'reverted': False
        }
    
    def _calculate_reward(self, trade_result: Dict) -> float:
        """
        Calculate reward for the RL agent
        """
        reward = float(trade_result['pnl'])
        
        if trade_result['reverted']:
            reward -= 100.0
        
        if trade_result['gas_cost'] > 50:
            reward -= (trade_result['gas_cost'] - 50) * 2
        
        if not trade_result['success'] and self.state[0] > 0.01:
            reward -= 5.0
        
        return float(reward)
    
    def render(self):
        """Render the environment state"""
        if self.render_mode == 'human':
            print(f"Step: {self.current_step}, Total PnL: ${self.total_pnl:.2f}, "
                  f"Successes: {self.num_successes}, Reverts: {self.num_reverts}")
