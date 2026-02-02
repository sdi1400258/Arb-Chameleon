// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./ProfitGuard.sol";
import "./DexAdapter.sol";
import "./FlashLoanHandler.sol";

/**
 * @title ArbExecutor
 * @notice Main contract for executing atomic arbitrage operations
 * @dev Combines flash loans, DEX swaps, and profit enforcement
 */
contract ArbExecutor is 
    Ownable, 
    ReentrancyGuard, 
    ProfitGuard, 
    DexAdapter, 
    FlashLoanHandler 
{
    
    // Struct to define arbitrage parameters
    struct ArbParams {
        address baseToken;          // The token we start and end with
        uint256 minProfit;          // Minimum profit required (in baseToken)
        bool useFlashLoan;          // Whether to use flash loan
        uint256 flashLoanAmount;    // Amount to borrow (if using flash loan)
        SwapStep[] swaps;           // Array of swaps to execute
    }
    
    // Struct to define a single swap step
    struct SwapStep {
        address router;             // DEX router address
        address tokenIn;            // Input token
        address tokenOut;           // Output token
        uint256 amountIn;           // Amount to swap (0 = use all balance)
        uint256 minAmountOut;       // Minimum output amount
        bool isV3;                  // True for V3, false for V2
        uint24 fee;                 // V3 pool fee (ignored for V2)
        address[] path;             // V2 path (ignored for V3)
    }
    
    // Events
    event ArbitrageExecuted(
        address indexed baseToken,
        uint256 profit,
        uint256 gasUsed
    );
    
    event FlashLoanExecuted(
        address indexed asset,
        uint256 amount,
        uint256 premium
    );
    
    // Errors
    error InvalidParameters();
    error ExecutionFailed();
    
    // Safety limits
    uint256 public maxTradeSize = 1000000 * 1e18; // 1M tokens
    uint256 public dailyLossLimit = 10000 * 1e18; // 10k tokens
    uint256 public dailyLoss;
    uint256 public lastResetDay;
    
    bool public killSwitch;
    
    constructor(address _aavePool) 
        Ownable(msg.sender)
        FlashLoanHandler(_aavePool) 
    {}
    
    /**
     * @notice Execute an arbitrage operation
     * @param params The arbitrage parameters
     */
    function executeArbitrage(ArbParams calldata params) 
        external 
        onlyOwner 
        nonReentrant 
    {
        if (killSwitch) revert ExecutionFailed();
        
        _resetDailyLossIfNeeded();
        
        uint256 gasStart = gasleft();
        
        if (params.useFlashLoan) {
            // Encode params for flash loan callback
            bytes memory encodedParams = abi.encode(params);
            _initiateFlashLoan(
                params.baseToken,
                params.flashLoanAmount,
                encodedParams
            );
        } else {
            // Execute without flash loan
            _executeSwaps(params);
        }
        
        uint256 gasUsed = gasStart - gasleft();
        emit ArbitrageExecuted(params.baseToken, 0, gasUsed);
    }
    
    /**
     * @notice Flash loan callback - executes the arbitrage
     * @param asset The borrowed asset
     * @param amount The borrowed amount
     * @param premium The flash loan fee
     * @param initiator The initiator of the flash loan
     * @param params Encoded arbitrage parameters
     */
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override onlyAavePool returns (bool) {
        if (initiator != address(this)) {
            revert UnauthorizedFlashLoan();
        }
        
        // Decode parameters
        ArbParams memory arbParams = abi.decode(params, (ArbParams));
        
        // Execute the arbitrage swaps
        _executeSwaps(arbParams);
        
        // Approve repayment
        uint256 totalDebt = amount + premium;
        IERC20(asset).approve(AAVE_POOL, totalDebt);
        
        emit FlashLoanExecuted(asset, amount, premium);
        
        return true;
    }
    
    /**
     * @notice Internal function to execute a series of swaps
     * @param params The arbitrage parameters
     */
    function _executeSwaps(ArbParams memory params) internal {
        uint256 startBalance = _getBalance(params.baseToken);
        
        // Execute each swap in sequence
        for (uint256 i = 0; i < params.swaps.length; i++) {
            SwapStep memory step = params.swaps[i];
            
            // Use entire balance if amountIn is 0
            uint256 amountIn = step.amountIn;
            if (amountIn == 0) {
                amountIn = IERC20(step.tokenIn).balanceOf(address(this));
            }
            
            if (step.isV3) {
                _swapV3(
                    step.router,
                    step.tokenIn,
                    step.tokenOut,
                    step.fee,
                    amountIn,
                    step.minAmountOut
                );
            } else {
                _swapV2(
                    step.router,
                    amountIn,
                    step.minAmountOut,
                    step.path
                );
            }
        }
        
        // Enforce profit requirement
        _enforceProfit(params.baseToken, startBalance, params.minProfit);
    }
    
    /**
     * @notice Emergency withdrawal function
     * @param token The token to withdraw
     * @param amount The amount to withdraw
     */
    function withdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).transfer(owner(), amount);
    }
    
    /**
     * @notice Toggle the kill switch
     */
    function toggleKillSwitch() external onlyOwner {
        killSwitch = !killSwitch;
    }
    
    /**
     * @notice Update safety limits
     */
    function updateLimits(
        uint256 _maxTradeSize,
        uint256 _dailyLossLimit
    ) external onlyOwner {
        maxTradeSize = _maxTradeSize;
        dailyLossLimit = _dailyLossLimit;
    }
    
    /**
     * @notice Reset daily loss counter if a new day has started
     */
    function _resetDailyLossIfNeeded() internal {
        uint256 currentDay = block.timestamp / 1 days;
        if (currentDay > lastResetDay) {
            dailyLoss = 0;
            lastResetDay = currentDay;
        }
    }
    
    /**
     * @notice Receive ETH
     */
    receive() external payable {}
}
