// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {ERC20} from "lib/solmate/src/tokens/ERC20.sol";
import {Owned} from "lib/solmate/src/auth/Owned.sol";

contract VITToken is ERC20, Owned {
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18;

    constructor() ERC20("VIT Blockchain", "VIT", 18) Owned(msg.sender) {
        _mint(msg.sender, 100_000_000 * 10**18); // 10% Initial supply
    }

    function mint(address to, uint256 amount) external onlyOwner {
        require(totalSupply + amount <= MAX_SUPPLY, "Exceeds Max Supply");
        _mint(to, amount);
    }

    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }
}
