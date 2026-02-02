"""
Historical backtesting framework for validating RL strategies
"""
import sys
import json
import argparse
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import numpy as np

sys.path.append('..')
sys.path.append('../rl/src')
from arb_env import ArbitrageEnv
from stable_baselines3 import PPO


@dataclass
class BacktestResult:
    """Results from a backtest run"""
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_pnl: float
    total_gas_spent: float
    net_pnl: float
    win_rate: float
    avg_profit_per_trade: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Dict]


class HistoricalBacktester:
    """
    Backtesting framework for RL arbitrage strategies
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        initial_capital: float = 10000.0
    ):
        """
        Initialize backtester
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Load RL model
        if model_path:
            print(f"Loading model from {model_path}")
            self.model = PPO.load(model_path)
        else:
            print("No model provided, using random policy")
            self.model = None
        
        # Create environment
        self.env = ArbitrageEnv(simulation_mode=True)
        
        # Results tracking
        self.trades: List[Dict] = []
        self.capital_history: List[float] = [initial_capital]
    
    def run_backtest(
        self,
        num_episodes: int = 100,
        max_steps_per_episode: int = 1000
    ) -> BacktestResult:
        """
        Run backtest simulation
        """
        print(f"\n{'='*60}")
        print(f"Starting Backtest")
        print(f"{'='*60}")
        print(f"Episodes: {num_episodes}")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"{'='*60}\n")
        
        total_trades = 0
        successful_trades = 0
        failed_trades = 0
        total_pnl = 0.0
        total_gas_spent = 0.0
        
        for episode in range(num_episodes):
            obs, info = self.env.reset()
            episode_pnl = 0.0
            
            if self.current_capital <= 0:
                print(f" Bankruptcy! Stopping backtest at Episode {episode}")
                break

            for step in range(max_steps_per_episode):
                # Get action from model or random
                if self.model:
                    action, _states = self.model.predict(obs, deterministic=True)
                else:
                    action = self.env.action_space.sample()
                
                # Step environment
                obs, reward, terminated, truncated, info = self.env.step(action)
                
                # Record trade
                if info.get('pnl', 0) != 0:
                    total_trades += 1
                    trade_pnl = info['pnl']
                    gas_cost = info['gas_cost']
                    
                    if info['success']:
                        successful_trades += 1
                    else:
                        failed_trades += 1
                    
                    total_pnl += trade_pnl
                    total_gas_spent += gas_cost
                    episode_pnl += trade_pnl
                    
                    # Update capital
                    self.current_capital += trade_pnl
                    self.capital_history.append(self.current_capital)
                    
                    # Record trade details
                    self.trades.append({
                        'episode': episode,
                        'step': step,
                        'pnl': trade_pnl,
                        'gas_cost': gas_cost,
                        'success': info['success'],
                        'capital': self.current_capital
                    })
                    
                    if self.current_capital <= 0:
                        break # End episode on bankruptcy
                
                if terminated or truncated:
                    break
            
            # Print episode summary
            if (episode + 1) % 10 == 0:
                print(f"Episode {episode + 1}/{num_episodes}: "
                      f"PnL = ${episode_pnl:.2f}, "
                      f"Capital = ${self.current_capital:,.2f}")
        
        # Calculate metrics
        win_rate = successful_trades / total_trades if total_trades > 0 else 0
        avg_profit = total_pnl / total_trades if total_trades > 0 else 0
        
        # NET PNL FIX: total_pnl already includes gas costs from arb_env
        net_pnl = total_pnl 
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()
        
        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        result = BacktestResult(
            total_trades=total_trades,
            successful_trades=successful_trades,
            failed_trades=failed_trades,
            total_pnl=total_pnl,
            total_gas_spent=total_gas_spent,
            net_pnl=net_pnl,
            win_rate=win_rate,
            avg_profit_per_trade=avg_profit,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=self.trades
        )
        
        self._print_results(result)
        
        return result
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from capital history"""
        if len(self.capital_history) < 2:
            return 0.0
        
        peak = self.capital_history[0]
        max_dd = 0.0
        
        for capital in self.capital_history:
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd * 100  # Return as percentage
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from trade returns"""
        if len(self.trades) < 2:
            return 0.0
        
        returns = [trade['pnl'] for trade in self.trades]
        
        if len(returns) == 0:
            return 0.0
        
        # Calculate volatility 
        std_return = np.std(returns)
        if std_return == 0:
            return 0.0
            
        mean_return = np.mean(returns)
        
        # Annualized Sharpe (assuming 252 trading days)
        sharpe = (mean_return / std_return) * np.sqrt(252)
        
        return float(sharpe)
    
    def _print_results(self, result: BacktestResult):
        """Print backtest results"""
        print(f"\n{'='*60}")
        print(f"Backtest Results")
        print(f"{'='*60}")
        print(f"Total Trades:          {result.total_trades}")
        print(f"Successful Trades:     {result.successful_trades}")
        print(f"Failed Trades:         {result.failed_trades}")
        print(f"Win Rate:              {result.win_rate*100:.2f}%")
        print(f"")
        print(f"Total PnL:             ${result.total_pnl:,.2f}")
        print(f"Total Gas Spent:       ${result.total_gas_spent:,.2f}")
        print(f"Net PnL:               ${result.net_pnl:,.2f}")
        print(f"Avg Profit/Trade:      ${result.avg_profit_per_trade:.2f}")
        print(f"")
        print(f"Initial Capital:       ${self.initial_capital:,.2f}")
        print(f"Final Capital:         ${self.current_capital:,.2f}")
        print(f"Return:                {((self.current_capital/self.initial_capital - 1)*100):.2f}%")
        print(f"")
        print(f"Max Drawdown:          {result.max_drawdown:.2f}%")
        print(f"Sharpe Ratio:          {result.sharpe_ratio:.2f}")
        print(f"{'='*60}\n")
    
    def save_results(self, filepath: str, result: BacktestResult):
        """Save backtest results to JSON file"""
        data = {
            'summary': {
                'total_trades': result.total_trades,
                'successful_trades': result.successful_trades,
                'failed_trades': result.failed_trades,
                'win_rate': result.win_rate,
                'total_pnl': result.total_pnl,
                'total_gas_spent': result.total_gas_spent,
                'net_pnl': result.net_pnl,
                'avg_profit_per_trade': result.avg_profit_per_trade,
                'max_drawdown': float(result.max_drawdown),
                'sharpe_ratio': float(result.sharpe_ratio),
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'return_pct': (self.current_capital / self.initial_capital - 1) * 100
            },
            'trades': result.trades,
            'capital_history': self.capital_history
        }

        def default(o):
            if isinstance(o, (np.int_, np.intc, np.intp, np.int8,
                              np.int16, np.int32, np.int64, np.uint8,
                              np.uint16, np.uint32, np.uint64)):
                return int(o)
            elif isinstance(o, (np.float16, np.float32, np.float64)):
                return float(o)
            elif isinstance(o, (np.ndarray,)): 
                return o.tolist()
            return str(o)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=default)
        
        print(f"Results saved to {filepath}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run historical backtest")
    parser.add_argument("--model", default=None, help="Path to RL model")
    parser.add_argument("--episodes", type=int, default=100, help="Number of episodes")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    parser.add_argument("--output", default="backtest_results.json", help="Output file")
    
    args = parser.parse_args()
    
    backtester = HistoricalBacktester(
        model_path=args.model,
        initial_capital=args.capital
    )
    
    result = backtester.run_backtest(num_episodes=args.episodes)
    backtester.save_results(args.output, result)
