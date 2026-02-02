"""
L2 (Arbitrum/Base) Simulation Backtester
Demonstrates strategy profitability with L2 gas costs
"""
import sys
import argparse
from backtest import HistoricalBacktester, BacktestResult
from arb_env import ArbitrageEnv

class L2Backtester(HistoricalBacktester):
    def __init__(self, model_path=None, initial_capital=100.0, gas_multiplier=0.01):
        super().__init__(model_path, initial_capital)
        
        # OVERRIDE environment with L2 gas settings
        self.env = ArbitrageEnv(simulation_mode=True, gas_multiplier=gas_multiplier)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run L2 historical backtest")
    parser.add_argument("--model", default=None, help="Path to RL model")
    parser.add_argument("--episodes", type=int, default=100, help="Number of episodes")
    parser.add_argument("--capital", type=float, default=100, help="Initial capital")
    parser.add_argument("--output", default="l2_backtest_results.json", help="Output file")
    
    args = parser.parse_args()
    
    print(f"\n STARTING L2 SIMULATION (Gas Fees ~1% of L1)")
    print(f"Goal: Minimize gas costs to show strategy logic works\n")
    
    backtester = L2Backtester(
        model_path=args.model,
        initial_capital=args.capital,
        gas_multiplier=0.01 # 99% cheaper gas
    )
    
    result = backtester.run_backtest(num_episodes=args.episodes)
    backtester.save_results(args.output, result)
