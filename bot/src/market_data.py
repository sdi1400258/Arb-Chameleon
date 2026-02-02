"""
Market data provider for monitoring DEX prices and blockchain state
ROBUST Version - No API Keys Required
"""
from web3 import Web3
from typing import Dict, List, Tuple
import time
import requests

class MarketDataProvider:
    """Monitors on-chain prices and provides market state"""
    
    def __init__(self, rpc_url: str):
        # We use a public RPC just for basic block/gas metadata
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
    
    def get_current_block(self) -> int:
        try: return self.w3.eth.block_number
        except: return 0
    
    def get_gas_price(self) -> int:
        try: return self.w3.eth.gas_price
        except: return 20 * 10**9

    def get_live_dex_spread(self) -> Dict[str, any]:
        """
        Fetch ALL WETH prices on Ethereum DEXs and find the biggest spread.
        No API keys needed. No account needed.
        """
        result = {"price_a": 0.0, "price_b": 0.0, "dex_a": "N/A", "dex_b": "N/A"}
        
        try:
            # Get all WETH-related pairs on Ethereum
            url = "https://api.dexscreener.com/latest/dex/tokens/0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                return result
                
            data = response.json()
            if not data or 'pairs' not in data or not data['pairs']:
                return result
            
            ethereum_pairs = [p for p in data['pairs'] if p.get('chainId') == 'ethereum']
            if len(ethereum_pairs) < 2:
                return result

            # Sort by price to find the max spread
            valid_prices = []
            for p in ethereum_pairs:
                try:
                    price = float(p.get('priceUsd', 0))
                    if price > 500: # ensure it's WETH-like
                        valid_prices.append({
                            'price': price,
                            'dex': p.get('dexId', 'Unknown')
                        })
                except:
                    continue

            if len(valid_prices) < 2:
                return result

            # Find Max and Min
            valid_prices.sort(key=lambda x: x['price'])
            
            p_min = valid_prices[0]
            p_max = valid_prices[-1]

            return {
                "price_a": p_max['price'],
                "price_b": p_min['price'],
                "dex_a": p_max['dex'],
                "dex_b": p_min['dex']
            }
        except Exception as e:
            # print(f"DEBUG: Price API Error: {e}")
            return result

    def get_market_state(self, pairs: List) -> Dict:
        spread_data = self.get_live_dex_spread()
        
        return {
            'block_number': self.get_current_block(),
            'gas_price': self.get_gas_price(),
            'timestamp': int(time.time()),
            'prices': {
                'price_a': spread_data['price_a'],
                'price_b': spread_data['price_b'],
                'dex_a': spread_data['dex_a'],
                'dex_b': spread_data['dex_b']
            }
        }
