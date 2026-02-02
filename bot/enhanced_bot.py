"""
Enhanced bot with GRANULAR cost breakdown
"""
import sys
import time
from typing import Dict, Optional, List
import os

# Fix paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from config import *
from src.market_data import MarketDataProvider
import numpy as np


class EnhancedArbBot:
    """
    Arbitrage bot with Detailed Cost Analysis
    """
    
    def __init__(
        self,
        rpc_url: str,
        network: str = "base",
        shadow_mode: bool = True
    ):
        self.shadow_mode = shadow_mode
        self.network = network.lower()
        self.market_data = MarketDataProvider(rpc_url)
        
        # Refined Network Presets (More precise)
        self.NETWORKS = {
            "ethereum": {"gas": 40.0,   "fee": 0.003,  "slippage": 0.0005}, # Tight slippage, huge gas
            "arbitrum": {"gas": 0.20,   "fee": 0.001,  "slippage": 0.001},  # L2 optimization
            "base":     {"gas": 0.05,   "fee": 0.003,  "slippage": 0.001},  # Standard L2
            "polygon":  {"gas": 0.03,   "fee": 0.003,  "slippage": 0.001},  
            "bsc":      {"gas": 0.25,   "fee": 0.0025, "slippage": 0.001}, 
            "solana":   {"gas": 0.001,  "fee": 0.003,  "slippage": 0.001}   # Standard 0.3% fee, low slip
        }
        
        config = self.NETWORKS.get(self.network, self.NETWORKS["base"])
        self.AVG_GAS_USD = config["gas"]
        self.DEX_FEE_RATE = config["fee"]
        self.SLIPPAGE_RATE = config["slippage"]
        
        print(f"Network: {self.network.upper()} initialized")

    def observe_market(self):
        try:
            market_state = self.market_data.get_market_state([])
            p_a = market_state['prices'].get('price_a', 0)
            p_b = market_state['prices'].get('price_b', 0)
            dex_a = market_state['prices'].get('dex_a', 'N/A')
            dex_b = market_state['prices'].get('dex_b', 'N/A')
            
            if p_a > 0 and p_b > 0:
                raw_spread = abs(p_a - p_b) / min(p_a, p_b)
                return raw_spread, p_a, p_b, dex_a, dex_b
            return 0, 0, 0, "", ""
        except:
            return 0, 0, 0, "", ""

    def run(self, iterations=10, trade_size=1000):
        print("\n" + "="*70)
        print(f"DETAILED ARB COST ANALYSIS | Capital: ${trade_size}")
        print(f"Network: {self.network.upper()}")
        print("Prices: LIVE (DexScreener API) | Costs: REALISTIC PRESETS")
        print("="*70 + "\n")
        
        total_profitable = 0
        total_net_pnl = 0.0
        
        for i in range(iterations):
            spread, p_a, p_b, dex_a, dex_b = self.observe_market()
            
            if spread > 0:
                # BREAKDOWN
                gross_profit = trade_size * spread
                dex_fees = trade_size * self.DEX_FEE_RATE * 2 # Two trades
                slippage = trade_size * self.SLIPPAGE_RATE
                gas_cost = self.AVG_GAS_USD
                
                net_profit = gross_profit - dex_fees - slippage - gas_cost
                
                print(f"[#{i+1}] {dex_a} (${p_a:.2f}) vs {dex_b} (${p_b:.2f})")
                print(f"    Raw Spread:  {spread*100:.3f}% (+${gross_profit:.2f})")
                print(f"    - DEX Fees:  -${dex_fees:.2f} ({self.DEX_FEE_RATE*200:.2f}%)")
                print(f"    - Slippage:  -${slippage:.2f} ({self.SLIPPAGE_RATE*100:.2f}%)")
                print(f"    - Gas Cost:  -${gas_cost:.4f}")
                
                if net_profit > 0:
                    total_profitable += 1
                    total_net_pnl += net_profit
                    print(f"    [VIABLE] Net: +${net_profit:.2f}")
                else:
                    print(f"    [LOSS]   Net: ${net_profit:.2f}")
                print("-" * 30)
            
            time.sleep(5)
            
        print("\n" + "="*70)
        print(f"SUMMARY FOR {self.network.upper()} OVER {iterations} ITERATIONS")
        print(f"  Total Net Gain/Loss: ${total_net_pnl:.2f}")
        print(f"  Success Rate:        {total_profitable}/{iterations}")
        print("="*70 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", default="base")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--capital", type=float, default=1000)
    args = parser.parse_args()
    
    bot = EnhancedArbBot(rpc_url="https://cloudflare-eth.com", network=args.network)
    bot.run(iterations=args.iterations, trade_size=args.capital)
