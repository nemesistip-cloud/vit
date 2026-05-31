// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Owned} from "lib/solmate/src/auth/Owned.sol";
import {ERC20} from "lib/solmate/src/tokens/ERC20.sol";

contract LoyaltyVault is Owned {
    ERC20 public vitToken;

    struct Attestation {
        bytes32 signalId;
        uint256 amountPaid;
        uint256 timestamp;
    }

    mapping(address => Attestation[]) public userAttestations;
    uint256 public totalLoyaltyCollected;

    event LoyaltyPaid(address indexed user, bytes32 indexed signalId, uint256 amount);

    constructor(address _vitToken) Owned(msg.sender) {
        vitToken = ERC20(_vitToken);
    }

    function attestAndPay(bytes32 signalId, uint256 amount) external {
        require(vitToken.transferFrom(msg.sender, address(this), amount), "Transfer failed");

        userAttestations[msg.sender].push(Attestation({
            signalId: signalId,
            amountPaid: amount,
            timestamp: block.timestamp
        }));

        totalLoyaltyCollected += amount;
        emit LoyaltyPaid(msg.sender, signalId, amount);
    }

    function withdraw(address to, uint256 amount) external onlyOwner {
        require(vitToken.transfer(to, amount), "Withdraw failed");
    }
}
