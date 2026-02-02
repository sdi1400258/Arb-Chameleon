"""
Flashbots bundle builder and submitter for MEV strategies
"""
import requests
import json
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from typing import List, Dict, Optional
import sys
sys.path.append('..')
import config


class FlashbotsClient:
    """
    Client for submitting transaction bundles to Flashbots
    """
    
    def __init__(
        self,
        w3: Web3,
        flashbots_rpc: str = config.FLASHBOTS_RPC,
        signing_key: Optional[str] = None
    ):
        self.w3 = w3
        self.flashbots_rpc = flashbots_rpc
        
        # Flashbots requires a signing key for authentication
        if signing_key:
            self.signer: LocalAccount = Account.from_key(signing_key)
        else:
            # Generate a random key for testing (DO NOT use in production)
            self.signer: LocalAccount = Account.create()
        
        print(f"Flashbots client initialized with signer: {self.signer.address}")
    
    def build_bundle(
        self,
        transactions: List[Dict],
        target_block: int
    ) -> Dict:
        """
        Build a Flashbots bundle
        
        Args:
            transactions: List of transaction dictionaries
            target_block: Target block number for inclusion
            
        Returns:
            Bundle dictionary
        """
        signed_txs = []
        
        for tx in transactions:
            # Sign each transaction
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                private_key=tx.get('private_key', self.signer.key)
            )
            signed_txs.append(signed_tx.rawTransaction.hex())
        
        bundle = {
            'txs': signed_txs,
            'blockNumber': hex(target_block),
            'minTimestamp': 0,
            'maxTimestamp': 0
        }
        
        return bundle
    
    def simulate_bundle(
        self,
        bundle: Dict,
        state_block: Optional[int] = None
    ) -> Dict:
        """
        Simulate a bundle using Flashbots simulation API
        
        Args:
            bundle: Bundle to simulate
            state_block: Block number to simulate against
            
        Returns:
            Simulation results
        """
        if state_block is None:
            state_block = self.w3.eth.block_number
        
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'eth_callBundle',
            'params': [
                {
                    'txs': bundle['txs'],
                    'blockNumber': bundle['blockNumber'],
                    'stateBlockNumber': hex(state_block)
                }
            ]
        }
        
        try:
            # Sign the request
            headers = self._get_flashbots_headers(payload)
            
            response = requests.post(
                self.flashbots_rpc,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'result': result.get('result', {}),
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'result': None,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }
    
    def send_bundle(
        self,
        bundle: Dict,
        target_block: Optional[int] = None
    ) -> Dict:
        """
        Send a bundle to Flashbots
        
        Args:
            bundle: Bundle to send
            target_block: Target block (overrides bundle blockNumber)
            
        Returns:
            Submission result
        """
        if target_block:
            bundle['blockNumber'] = hex(target_block)
        
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'eth_sendBundle',
            'params': [bundle]
        }
        
        try:
            # Sign the request
            headers = self._get_flashbots_headers(payload)
            
            response = requests.post(
                self.flashbots_rpc,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if 'error' in result:
                    return {
                        'success': False,
                        'bundle_hash': None,
                        'error': result['error']
                    }
                
                return {
                    'success': True,
                    'bundle_hash': result.get('result', {}).get('bundleHash'),
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'bundle_hash': None,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'bundle_hash': None,
                'error': str(e)
            }
    
    def get_bundle_stats(
        self,
        bundle_hash: str,
        target_block: int
    ) -> Dict:
        """
        Get statistics for a submitted bundle
        
        Args:
            bundle_hash: Hash of the bundle
            target_block: Target block number
            
        Returns:
            Bundle statistics
        """
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'flashbots_getBundleStats',
            'params': [
                {
                    'bundleHash': bundle_hash,
                    'blockNumber': hex(target_block)
                }
            ]
        }
        
        try:
            headers = self._get_flashbots_headers(payload)
            
            response = requests.post(
                self.flashbots_rpc,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'stats': result.get('result', {}),
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'stats': None,
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'stats': None,
                'error': str(e)
            }
    
    def _get_flashbots_headers(self, payload: Dict) -> Dict:
        """
        Generate Flashbots authentication headers
        
        Args:
            payload: JSON-RPC payload
            
        Returns:
            Headers dictionary
        """
        # Flashbots requires signing the payload
        message = Web3.keccak(text=json.dumps(payload))
        signed_message = self.signer.signHash(message)
        
        signature = signed_message.signature.hex()
        
        return {
            'Content-Type': 'application/json',
            'X-Flashbots-Signature': f"{self.signer.address}:{signature}"
        }
    
    def create_arbitrage_bundle(
        self,
        arb_tx: Dict,
        target_block: int,
        max_priority_fee: int = 0
    ) -> Dict:
        """
        Create a bundle for an arbitrage transaction
        
        Args:
            arb_tx: Arbitrage transaction
            target_block: Target block for inclusion
            max_priority_fee: Maximum priority fee (for miner tip)
            
        Returns:
            Bundle ready for submission
        """
        # Add Flashbots-specific fields
        arb_tx['maxPriorityFeePerGas'] = max_priority_fee
        
        bundle = self.build_bundle([arb_tx], target_block)
        
        return bundle


if __name__ == "__main__":
    # Test the Flashbots client
    from market_data import MarketDataProvider
    
    provider = MarketDataProvider(config.RPC_URL)
    client = FlashbotsClient(provider.w3)
    
    print(f"Flashbots client ready")
    print(f"Signer address: {client.signer.address}")
