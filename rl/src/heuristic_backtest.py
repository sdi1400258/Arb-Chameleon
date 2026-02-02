"""
Heuristic (Rule-Based) Backtester
PROVES that the environment allows profit, even if the RL agent is currently too dumb to find it.
"""
import sys
import argparse
import numpy as np
from backtest import HistoricalBacktester, BacktestResult
from arb_env import ArbitrageEnv

class HeuristicBacktester(HistoricalBacktester):
    def __init__(self, initial_capital=100000.0, gas_multiplier=0.01):
        # Override init to skip model loading and set L2 gas
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.model = None
        
        # CORRECTLY PASS INITIAL CAPITAL
        self.env = ArbitrageEnv(
            simulation_mode=True, 
            gas_multiplier=gas_multiplier,
            initial_capital=initial_capital
        )
        
        self.trades = []
        self.capital_history = [initial_capital]

    def run_backtest(self, num_episodes=100, max_steps_per_episode=1000):
        print(f"\n STARTING HEURISTIC 'PERFECT TRADER' SIMULATION")
        print(f"Goal: Prove that profit exists in the system.\n")
        
        # Stats
        total_trades = 0
        successful_trades = 0
        failed_trades = 0
        total_pnl = 0.0
        total_gas_spent = 0.0
        
        for episode in range(num_episodes):
            obs, info = self.env.reset()
            episode_pnl = 0.0
            
            for step in range(max_steps_per_episode):
                spread = obs[0]
                
                # Rule: If spread > 0.1%
                if spread >= 0.001: 
                    # Decide trade size based on capital
                    # Can we afford $10,000? No.
                    # Can we afford $1,000? No.
                    # Can we afford $100? Yes. (Index 1)
                    
                    if self.current_capital >= 10000:
                        size_idx = 3.0 # $10,000
                    elif self.current_capital >= 1000:
                        size_idx = 2.0 # $1,000
                    elif self.current_capital >= 100:
                        size_idx = 1.0 # $100
                    else:
                        size_idx = 0.0 # $50
                    
                    # Trade!
                    action = np.array([0.0005, size_idx, 0.0, 5.0, 0.0], dtype=np.float32)
                else:
                    # Do nothing
                    action = np.array([0.9, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
                
                obs, reward, terminated, truncated, info = self.env.step(action)
                
                if info.get('pnl', 0) != 0:
                    total_trades += 1
                    total_pnl += info['pnl']
                    total_gas_spent += info['gas_cost']
                    episode_pnl += info['pnl']
                    
                    if info['success']:
                        successful_trades += 1
                    else:
                        failed_trades += 1
                    
                    self.current_capital += info['pnl']
                    self.capital_history.append(self.current_capital)
                    
                    # Log big wins (or small wins)
                    if info['pnl'] > 0.1:
                         pass # Silence spam for small capital runs
                    if info['pnl'] > 5.0:
                         print(f" BIG WIN: +${info['pnl']:.2f} (Spread: {spread*100:.3f}%)")

                if terminated or truncated:
                    break
            
            if (episode+1) % 10 == 0:
                print(f"Episode {episode+1}: Capital = ${self.current_capital:,.2f}")

        # Metrics
        result = BacktestResult(
            total_trades=total_trades,
            successful_trades=successful_trades,
            failed_trades=failed_trades,
            total_pnl=total_pnl,
            total_gas_spent=total_gas_spent,
            net_pnl=total_pnl,
            win_rate=successful_trades/total_trades if total_trades else 0,
            avg_profit_per_trade=total_pnl/total_trades if total_trades else 0,
            max_drawdown=self._calculate_max_drawdown(),
            sharpe_ratio=self._calculate_sharpe_ratio(),
            trades=self.trades
        )
        self._print_results(result)
        return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--capital", type=float, default=100000.0)
    args = parser.parse_args()
    
    bt = HeuristicBacktester(initial_capital=args.capital)
    bt.run_backtest(num_episodes=args.episodes)
