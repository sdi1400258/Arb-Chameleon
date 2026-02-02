// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

// Uniswap V2 Router interface
interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);
    
    function getAmountsOut(uint amountIn, address[] calldata path)
        external view returns (uint[] memory amounts);
}

// Uniswap V3 Router interface (simplified)
interface IUniswapV3Router {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    
    function exactInputSingle(ExactInputSingleParams calldata params)
        external payable returns (uint256 amountOut);
}

/**
 * @title DexAdapter
 * @notice Adapter for interacting with various DEX protocols
 * @dev Supports Uniswap V2 and V3 style interfaces
 */
abstract contract DexAdapter {
    
    error SwapFailed(address router, address tokenIn, address tokenOut);
    
    /**
     * @notice Execute a swap on Uniswap V2
     * @param router The V2 router address
     * @param amountIn Amount of input tokens
     * @param amountOutMin Minimum amount of output tokens
     * @param path The swap path
     * @return amountOut The actual amount received
     */
    function _swapV2(
        address router,
        uint256 amountIn,
        uint256 amountOutMin,
        address[] memory path
    ) internal returns (uint256 amountOut) {
        IERC20(path[0]).approve(router, amountIn);
        
        uint[] memory amounts = IUniswapV2Router(router).swapExactTokensForTokens(
            amountIn,
            amountOutMin,
            path,
            address(this),
            block.timestamp
        );
        
        if (amounts.length == 0 || amounts[amounts.length - 1] < amountOutMin) {
            revert SwapFailed(router, path[0], path[path.length - 1]);
        }
        
        return amounts[amounts.length - 1];
    }
    
    /**
     * @notice Execute a swap on Uniswap V3
     * @param router The V3 router address
     * @param tokenIn Input token address
     * @param tokenOut Output token address
     * @param fee The pool fee tier
     * @param amountIn Amount of input tokens
     * @param amountOutMin Minimum amount of output tokens
     * @return amountOut The actual amount received
     */
    function _swapV3(
        address router,
        address tokenIn,
        address tokenOut,
        uint24 fee,
        uint256 amountIn,
        uint256 amountOutMin
    ) internal returns (uint256 amountOut) {
        IERC20(tokenIn).approve(router, amountIn);
        
        IUniswapV3Router.ExactInputSingleParams memory params = 
            IUniswapV3Router.ExactInputSingleParams({
                tokenIn: tokenIn,
                tokenOut: tokenOut,
                fee: fee,
                recipient: address(this),
                deadline: block.timestamp,
                amountIn: amountIn,
                amountOutMinimum: amountOutMin,
                sqrtPriceLimitX96: 0
            });
        
        amountOut = IUniswapV3Router(router).exactInputSingle(params);
        
        if (amountOut < amountOutMin) {
            revert SwapFailed(router, tokenIn, tokenOut);
        }
    }
}
