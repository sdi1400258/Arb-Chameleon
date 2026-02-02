// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title ProfitGuard
 * @notice Enforces profitability invariants for arbitrage operations
 * @dev This contract ensures that all trades result in a net profit
 */
abstract contract ProfitGuard {
    
    error InsufficientProfit(uint256 actual, uint256 required);
    error NegativeProfit(uint256 startBalance, uint256 endBalance);
    
    /**
     * @notice Validates that the profit meets the minimum threshold
     * @param token The token to check balance for
     * @param startBalance The balance before the operation
     * @param minProfit The minimum required profit
     */
    function _enforceProfit(
        address token,
        uint256 startBalance,
        uint256 minProfit
    ) internal view {
        uint256 endBalance = IERC20(token).balanceOf(address(this));
        
        if (endBalance <= startBalance) {
            revert NegativeProfit(startBalance, endBalance);
        }
        
        uint256 actualProfit = endBalance - startBalance;
        
        if (actualProfit < minProfit) {
            revert InsufficientProfit(actualProfit, minProfit);
        }
    }
    
    /**
     * @notice Returns the current balance of a token
     * @param token The token address
     * @return The balance of the token held by this contract
     */
    function _getBalance(address token) internal view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }
}
