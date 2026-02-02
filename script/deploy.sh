#!/bin/bash
# Deployment script for ArbExecutor contract

set -e

echo "Deploying ArbExecutor contract..."

# Set Foundry path
export PATH="$HOME/.foundry/bin:$PATH"

# Configuration
RPC_URL="${RPC_URL:-http://localhost:8545}"
AAVE_POOL="${AAVE_POOL:-0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2}"

echo "RPC URL: $RPC_URL"
echo "Aave Pool: $AAVE_POOL"

# Deploy contract
forge create \
    --rpc-url "$RPC_URL" \
    --constructor-args "$AAVE_POOL" \
    src/ArbExecutor.sol:ArbExecutor \
    --unlocked \
    --from 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

echo "Deployment complete!"
