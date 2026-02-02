"""
Main bot orchestrator that integrates RL agent with on-chain execution
"""
import sys
import time
from typing import Dict, Optional
sys.path.append('bot')
sys.path.append('rl/src')

from bot.config import *
from bot.src.market_data import MarketDataProvider
from rl.src.arb_env import ArbitrageEnv
from stable_baselines3 import PPO
import numpy as np


class ArbBot:
    """
    Main arbitrage bot that coordinates:
    1. Market monitoring (deterministic)
    2. RL agent decision-making (adaptive)
    3. Transaction construction and submission (deterministic)
    """
    
    def __init__(
        self,
        rpc_url: str,
        model_path: Optional[str] = None,
        shadow_mode: bool = True
    ):
        """
        Initialize the arbitrage bot
        
        Args:
            rpc_url: Blockchain RPC endpoint
            model_path: Path to trained RL model (None = use defaults)
            shadow_mode: If True, only log actions without executing
        """
        self.shadow_mode = shadow_mode
        self.market_data = MarketDataProvider(rpc_url)
        
        # Load RL agent if model path provided
        if model_path:
            print(f"Loading RL model from {model_path}")
            self.rl_agent = PPO.load(model_path)
        else:
            print("No RL model provided, using default heuristics")
            self.rl_agent = None
        
        # Statistics
        self.total_opportunities = 0
        self.total_executed = 0
        self.total_pnl = 0.0
        
        print(f"ArbBot initialized (Shadow Mode: {shadow_mode})")
    
    def get_rl_action(self, state: np.ndarray) -> Dict:
        """
        Get action from RL agent
        
        Args:
            state: Market state observation
            
        Returns:
            Dictionary with action parameters
        """
        if self.rl_agent is None:
            # Default heuristic strategy
            return {
                'threshold': 0.002,  # 0.2% minimum profit
                'trade_size': 5000,
                'strategy': 'dex_arb',
                'priority_fee': 2.0,
                'use_flashloan': False
            }
        
        # Get action from RL agent
        action, _states = self.rl_agent.predict(state, deterministic=True)
        
        # Parse action
        trade_sizes = [1000, 5000, 20000, 100000]
        strategies = ['dex_arb', 'triangular', 'backrun', 'liquidation']
        
        return {
            'threshold': float(action[0]),
            'trade_size': trade_sizes[int(np.clip(action[1], 0, 3))],
            'strategy': strategies[int(np.clip(action[2], 0, 3))],
            'priority_fee': float(action[3]),
            'use_flashloan': action[4] > 0.5
        }
    
    def observe_market(self) -> np.ndarray:
        """
        Observe current market state and convert to RL state
        
        Returns:
            State vector for RL agent
        """
        # Get current market data
        block = self.market_data.get_current_block()
        gas_price = self.market_data.get_gas_price()
        
        # In production, this would analyze actual DEX pairs
        # For now, return a simulated state
        state = np.array([
            np.random.uniform(0.0, 0.05),  # price_spread
            np.random.uniform(0.3, 1.0),   # pool_liquidity
            np.random.uniform(0.0, 0.5),   # volatility
            min(gas_price / 1e11, 1.0),    # gas_price (normalized)
            np.random.uniform(0.0, 1.0),   # mempool_congestion
            0.7,  # recent_success_rate
            0.1,  # recent_reverts
            (time.time() % 86400) / 86400,  # time_of_day
            0.2,  # block_time_variance
        ], dtype=np.float32)
        
        return state
    
    def should_execute(self, action: Dict, state: np.ndarray) -> bool:
        """
        Determine if trade should be executed based on RL action and market state
        
        Args:
            action: RL agent action
            state: Current market state
            
        Returns:
            True if trade should execute
        """
        price_spread = state[0]
        threshold = action['threshold']
        
        # Basic profitability check
        if price_spread < threshold:
            return False
        
        # Gas price check
        gas_price = self.market_data.get_gas_price()
        if gas_price > MAX_GAS_PRICE * 1e9:
            print(f"Gas price too high: {gas_price / 1e9:.2f} gwei")
            return False
        
        return True
    
    def execute_trade(self, action: Dict):
        """
        Execute the arbitrage trade
        
        Args:
            action: Trade parameters from RL agent
        """
        if self.shadow_mode:
            print(f"[SHADOW] Would execute: {action}")
            return
        
        # In production, this would:
        # 1. Construct transaction parameters
        # 2. Simulate the transaction
        # 3. Submit to blockchain (public or private bundle)
        # 4. Monitor for inclusion
        
        print(f"[LIVE] Executing: {action}")
        # TODO: Implement actual transaction submission
    
    def run(self, max_iterations: Optional[int] = None):
        """
        Main bot loop
        
        Args:
            max_iterations: Maximum iterations (None = infinite)
        """
        iteration = 0
        
        print("Starting bot main loop...")
        
        while max_iterations is None or iteration < max_iterations:
            try:
                # Observe market
                state = self.observe_market()
                
                # Get RL action
                action = self.get_rl_action(state)
                
                # Check if should execute
                if self.should_execute(action, state):
                    self.total_opportunities += 1
                    print(f"\n[Opportunity #{self.total_opportunities}]")
                    print(f"  Spread: {state[0]*100:.3f}%")
                    print(f"  Threshold: {action['threshold']*100:.3f}%")
                    print(f"  Trade Size: ${action['trade_size']}")
                    print(f"  Strategy: {action['strategy']}")
                    
                    self.execute_trade(action)
                    self.total_executed += 1
                
                # Sleep to avoid overwhelming the RPC
                time.sleep(1)
                iteration += 1
                
            except KeyboardInterrupt:
                print("\nBot stopped by user")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(5)
        
        print(f"\nBot Statistics:")
        print(f"  Total Opportunities: {self.total_opportunities}")
        print(f"  Total Executed: {self.total_executed}")
        print(f"  Total PnL: ${self.total_pnl:.2f}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the arbitrage bot")
    parser.add_argument("--rpc", default=RPC_URL, help="RPC URL")
    parser.add_argument("--model", default=None, help="Path to RL model")
    parser.add_argument("--shadow", action="store_true", help="Run in shadow mode")
    parser.add_argument("--iterations", type=int, default=100, help="Max iterations")
    
    args = parser.parse_args()
    
    bot = ArbBot(
        rpc_url=args.rpc,
        model_path=args.model,
        shadow_mode=args.shadow
    )
    
    bot.run(max_iterations=args.iterations)
