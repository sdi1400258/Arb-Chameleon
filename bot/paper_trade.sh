#!/bin/bash
# Global Paper Trading Script
# Usage: ./paper_trade.sh [ethereum|base|polygon|bsc|solana] [capital]

NETWORK=${1:-base}
CAPITAL=${2:-1000}

echo "Ready for $NETWORK Paper Trading..."
echo "Simulating ${NETWORK^^} architecture and fee structure."
echo "--------------------------------------------------------"

source ../venv/bin/activate
python enhanced_bot.py \
    --network $NETWORK \
    --capital $CAPITAL \
    --iterations 5
