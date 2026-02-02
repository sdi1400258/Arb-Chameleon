"""
Simple script to verify RPC connection and account status
"""
import os
import sys
from web3 import Web3
from dotenv import load_dotenv

def main():
    # Load .env
    load_dotenv()
    
    rpc_url = os.getenv("SEPOLIA_RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")
    
    if not rpc_url:
        print(" Error: SEPOLIA_RPC_URL not found in .env")
        return
    
    if not private_key:
        print(" Error: PRIVATE_KEY not found in .env")
        return
        
    print(f"Connecting to RPC: {rpc_url[:25]}...")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    try:
        if w3.is_connected():
            print(" Successfully connected to Sepolia!")
            
            # Get chain ID
            chain_id = w3.eth.chain_id
            print(f"   Chain ID: {chain_id}")
            
            if chain_id != 11155111:
                print(f"    Warning: Chain ID {chain_id} is not Sepolia (11155111)")
                
            # Get account address
            account = w3.eth.account.from_key(private_key)
            print(f"   Address: {account.address}")
            
            # Get balance
            balance_wei = w3.eth.get_balance(account.address)
            balance_eth = w3.from_wei(balance_wei, 'ether')
            print(f"   Balance: {balance_eth:.4f} ETH")
            
            if balance_eth < 0.1:
                print("    Warning: Balance might be too low for deployment")
            else:
                print("    Balance sufficient for deployment")
                
        else:
            print(" Failed to connect to RPC")
            
    except Exception as e:
        print(f" Error: {str(e)}")

if __name__ == "__main__":
    main()
