# Arb Chameleon

## Deep Reinforcement Learning for Cross-DEX Arbitrage

This project explores the application of Reinforcement Learning to decentralized finance arbitrage. The system is designed to identify and execute atomic price spreads across various decentralized exchanges (DEXs) while accounting for real-world constraints such as gas volatility, slippage, and swap fees.

## System Architecture

The repository is organized into three distinct layers that handle execution, monitoring, and strategy optimization.

### 1. Atomic Execution Layer (Solidity)
Built using Solidity and the Foundry framework, this layer ensures that all trades are executed atomically. 
- **Profit Enforcement**: The ProfitGuard contract validates the contract's balance before and after execution. If the trade does not result in a net profit after all transaction costs, the entire operation reverts.
- **Capital Efficiency**: Integrated with Aave V3 to utilize flash loans, allowing for high-volume trades without requiring significant upfront capital.

### 2. Market Monitoring (Python)
The monitoring bot provides real-time visibility into the DeFi ecosystem.
- **Public Discovery**: Uses public APIs to scan price spreads across Uniswap, SushiSwap, Curve, and other AMMs without the need for private infrastructure.
- **Multi-Chain Presets**: Includes pre-configured profiles for Ethereum, Arbitrum, Base, Polygon, BSC, and Solana to accurately simulate regional costs and timing.

### 3. Strategy Optimization (RL)
The core decision engine is a Proximal Policy Optimization (PPO) agent.
- **Realistic Training**: The agent is trained on a custom Gymnasium environment that simulates competitive market conditions and network congestion.
- **Decision Logic**: Instead of static thresholds, the agent dynamically adjusts trade entry based on current spread, liquidity depth, and gas forecasts.

## Getting Started

Follow these steps to set up the environment and run a live paper trading simulation.

### 1. Installation

Clone the repository and install the required dependencies within a virtual environment.

```bash
git clone https://github.com/sdi1400258/Arb-Chameleon.git
cd Arb-Chameleon
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Paper Trading Simulation

The simulation utilizes live market data to identify spreads while applying realistic cost penalties.

```bash
cd bot
# Example: Test on Solana with $1,000 capital
./paper_trade.sh solana 1000

# Example: Test on Base with $2,500 capital
./paper_trade.sh base 2500
```

### 3. Contract Testing

Validate the safety and logic of the smart contracts using the Foundry test suite.

```bash
forge test -vv
```

## Economic Considerations

During development, it became clear that gas fees are the primary barrier to small-scale arbitrage on Ethereum Mainnet. This project explicitly addresses this by:
- Prioritizing Layer 2 (L2) and low-fee environments where spreads are more capturesble for normal capital sizes.
- Factoring in standard DEX fees (typically 0.3%) and a slippage buffer (0.1%) to ensure paper results are grounded in reality.

## Roadmap

- Integration with Flashbots for MEV protection on Ethereum Mainnet.
- Expansion of the RL state space to include mempool data and pending transaction counts.
- Dynamic capital allocation based on pool liquidity depth.

## Disclaimer

This software is for research and educational purposes only. Cryptocurrency arbitrage involves significant risk, including capital loss and smart contract vulnerabilities. Always perform rigorous testing in non-production environments before considering the use of real assets.
