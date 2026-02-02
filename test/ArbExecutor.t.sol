// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/ArbExecutor.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockERC20 is ERC20 {
    constructor(string memory name, string memory symbol) ERC20(name, symbol) {
        _mint(msg.sender, 1000000 * 10**18);
    }
    
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract ArbExecutorTest is Test {
    ArbExecutor public arbExecutor;
    MockERC20 public tokenA;
    MockERC20 public tokenB;
    
    address public owner = address(this);
    address public mockAavePool = address(0x1234);
    
    function setUp() public {
        arbExecutor = new ArbExecutor(mockAavePool);
        tokenA = new MockERC20("Token A", "TKNA");
        tokenB = new MockERC20("Token B", "TKNB");
        
        // Fund the executor
        tokenA.mint(address(arbExecutor), 100000 * 10**18);
    }
    
    function testKillSwitch() public {
        arbExecutor.toggleKillSwitch();
        assertTrue(arbExecutor.killSwitch());
    }
    
    function testWithdraw() public {
        uint256 amount = 1000 * 10**18;
        uint256 balanceBefore = tokenA.balanceOf(owner);
        
        arbExecutor.withdraw(address(tokenA), amount);
        
        assertEq(tokenA.balanceOf(owner), balanceBefore + amount);
    }
    
    function testUpdateLimits() public {
        uint256 newMaxTradeSize = 500000 * 10**18;
        uint256 newDailyLossLimit = 5000 * 10**18;
        
        arbExecutor.updateLimits(newMaxTradeSize, newDailyLossLimit);
        
        assertEq(arbExecutor.maxTradeSize(), newMaxTradeSize);
        assertEq(arbExecutor.dailyLossLimit(), newDailyLossLimit);
    }
}
