#!/bin/bash
# Safer deployment script for Sepolia Testnet

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Sepolia Testnet Deployment"
echo "=========================================="
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.example to .env and fill in your details."
    exit 1
fi

# Load environment variables
source .env

# Validate variables
if [ -z "$SEPOLIA_RPC_URL" ] || [ -z "$PRIVATE_KEY" ] || [ -z "$ETHERSCAN_API_KEY" ]; then
    echo -e "${RED}Error: Missing required environment variables!${NC}"
    echo "Check SEPOLIA_RPC_URL, PRIVATE_KEY, and ETHERSCAN_API_KEY in .env"
    exit 1
fi

# Set Foundry path
export PATH="$HOME/.foundry/bin:$PATH"

# Aave V3 Pool on Sepolia (verify this address)
# https://docs.aave.com/developers/deployed-contracts/v3-mainnet/sepolia
AAVE_POOL_SEPOLIA="0x6Ae43d3271ff6888e7Fc43Fd7321a503ff738951" 

echo "Configuration:"
echo "  Assets: Sepolia"
echo "  RPC: ${SEPOLIA_RPC_URL:0:20}..."
echo "  Aave Pool: $AAVE_POOL_SEPOLIA"
echo ""

read -p "Are you sure you want to deploy? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

echo ""
echo " Deploying ArbExecutor..."

# Deploy and verify
forge create \
    --rpc-url "$SEPOLIA_RPC_URL" \
    --private-key "$PRIVATE_KEY" \
    --constructor-args "$AAVE_POOL_SEPOLIA" \
    --etherscan-api-key "$ETHERSCAN_API_KEY" \
    --verify \
    src/ArbExecutor.sol:ArbExecutor

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN} Deployment Successful!${RED}"
    echo "Next steps:"
    echo "1. Copy the deployed contract address"
    echo "2. Update bot/config.py with the new address"
    echo "3. Run the bot validation script"
else
    echo ""
    echo -e "${RED} Deployment Failed!${NC}"
    exit 1
fi
