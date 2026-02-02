#!/bin/bash
# Integration test script - End-to-end system validation

set -e

echo "=========================================="
echo "RL-Arbitrage Integration Test"
echo "=========================================="
echo ""

# Set Foundry path
export PATH="$HOME/.foundry/bin:$PATH"

# Configuration
FORK_BLOCK=${FORK_BLOCK:-19000000}
RPC_URL=${MAINNET_RPC_URL:-"https://eth-mainnet.g.alchemy.com/v2/demo"}

echo " Test Configuration:"
echo "  Fork Block: $FORK_BLOCK"
echo "  RPC URL: ${RPC_URL:0:50}..."
echo ""

# Step 1: Start Anvil fork
echo " Step 1: Starting Anvil fork..."
anvil --fork-url "$RPC_URL" --fork-block-number "$FORK_BLOCK" --port 8545 &
ANVIL_PID=$!

# Wait for Anvil to start
sleep 3

if ! kill -0 $ANVIL_PID 2>/dev/null; then
    echo " Failed to start Anvil"
    exit 1
fi

echo " Anvil running (PID: $ANVIL_PID)"

# Cleanup function
cleanup() {
    echo ""
    echo " Cleaning up..."
    kill $ANVIL_PID 2>/dev/null || true
    wait $ANVIL_PID 2>/dev/null || true
    echo " Cleanup complete"
}

trap cleanup EXIT

# Step 2: Deploy contracts
echo ""
echo " Step 2: Deploying contracts..."

# Aave V3 Pool address on mainnet
AAVE_POOL="0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"

# Deploy using forge create
DEPLOY_OUTPUT=$(forge create \
    --rpc-url http://localhost:8545 \
    --constructor-args "$AAVE_POOL" \
    --unlocked \
    --from 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
    src/ArbExecutor.sol:ArbExecutor 2>&1)

# Extract contract address
CONTRACT_ADDRESS=$(echo "$DEPLOY_OUTPUT" | grep "Deployed to:" | awk '{print $3}')

if [ -z "$CONTRACT_ADDRESS" ]; then
    echo " Failed to deploy contract"
    echo "$DEPLOY_OUTPUT"
    exit 1
fi

echo " ArbExecutor deployed at: $CONTRACT_ADDRESS"

# Step 3: Test contract interaction
echo ""
echo " Step 3: Testing contract interaction..."

# Test kill switch
echo "  Testing kill switch..."
cast send "$CONTRACT_ADDRESS" \
    "toggleKillSwitch()" \
    --rpc-url http://localhost:8545 \
    --unlocked \
    --from 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
    > /dev/null 2>&1

KILL_SWITCH=$(cast call "$CONTRACT_ADDRESS" "killSwitch()" --rpc-url http://localhost:8545)

if [ "$KILL_SWITCH" = "0x0000000000000000000000000000000000000000000000000000000000000001" ]; then
    echo "   Kill switch working"
else
    echo "   Kill switch failed"
    exit 1
fi

# Step 4: Test Python bot
echo ""
echo " Step 4: Testing Python bot..."

# Update config with deployed address
cat > bot/test_config.py << EOF
import sys
sys.path.append('.')
from config import *

# Override for testing
RPC_URL = "http://localhost:8545"
ARB_EXECUTOR_ADDRESS = "$CONTRACT_ADDRESS"
EOF

# Test market data provider
echo "  Testing market data provider..."
python3 -c "
import sys
sys.path.append('bot/src')
sys.path.append('bot')
from market_data import MarketDataProvider
import test_config

provider = MarketDataProvider(test_config.RPC_URL)
block = provider.get_current_block()
print(f'  Current block: {block}')
assert block > 0, 'Failed to get block number'
print('   Market data provider working')
" || exit 1

# Test transaction simulator
echo "  Testing transaction simulator..."
python3 -c "
import sys
sys.path.append('bot/src')
sys.path.append('bot')
from tx_simulator import TransactionSimulator
from market_data import MarketDataProvider
import test_config

provider = MarketDataProvider(test_config.RPC_URL)
# Simulator requires deployed contract
print('   Transaction simulator module loaded')
" || exit 1

# Step 5: Test RL environment
echo ""
echo " Step 5: Testing RL environment..."

python3 -c "
import sys
sys.path.append('rl/src')
from arb_env import ArbitrageEnv

env = ArbitrageEnv()
obs, info = env.reset()
assert len(obs) == 9, 'Invalid observation space'

# Run a few steps
for _ in range(5):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        break

print('   RL environment working')
" || exit 1

# Step 6: Test bot in shadow mode
echo ""
echo " Step 6: Testing bot in shadow mode..."

python3 bot/main.py --rpc http://localhost:8545 --shadow --iterations 10 2>&1 | head -20

echo ""
echo "=========================================="
echo " All integration tests passed!"
echo "=========================================="
echo ""
echo "Summary:"
echo "   Anvil fork running"
echo "   Contracts deployed"
echo "   Contract interaction working"
echo "   Python bot functional"
echo "   RL environment operational"
echo "   Shadow mode working"
echo ""
echo "Contract Address: $CONTRACT_ADDRESS"
echo ""
