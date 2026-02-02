// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

// Aave V3 Pool interface (simplified)
interface IPool {
    function flashLoanSimple(
        address receiverAddress,
        address asset,
        uint256 amount,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

// Aave V3 Flash Loan callback interface
interface IFlashLoanSimpleReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}

/**
 * @title FlashLoanHandler
 * @notice Handles flash loan integration with Aave V3
 * @dev Implements the callback interface for Aave flash loans
 */
abstract contract FlashLoanHandler {
    
    error FlashLoanFailed();
    error UnauthorizedFlashLoan();
    
    address public immutable AAVE_POOL;
    
    constructor(address _aavePool) {
        AAVE_POOL = _aavePool;
    }
    
    /**
     * @notice Initiates a flash loan from Aave
     * @param asset The token to borrow
     * @param amount The amount to borrow
     * @param params Encoded parameters for the arbitrage
     */
    function _initiateFlashLoan(
        address asset,
        uint256 amount,
        bytes memory params
    ) internal {
        IPool(AAVE_POOL).flashLoanSimple(
            address(this),
            asset,
            amount,
            params,
            0 // referral code
        );
    }
    
    /**
     * @notice Callback function called by Aave during flash loan
     * @dev Must be implemented by inheriting contract
     * @param asset The borrowed asset
     * @param amount The borrowed amount
     * @param premium The flash loan fee
     * @param initiator The initiator of the flash loan
     * @param params Encoded arbitrage parameters
     * @return True if the operation was successful
     */
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external virtual returns (bool);
    
    /**
     * @notice Ensures only Aave pool can call the flash loan callback
     */
    modifier onlyAavePool() {
        if (msg.sender != AAVE_POOL) {
            revert UnauthorizedFlashLoan();
        }
        _;
    }
}
