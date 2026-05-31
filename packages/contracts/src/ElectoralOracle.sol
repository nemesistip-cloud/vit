// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Owned} from "lib/solmate/src/auth/Owned.sol";

contract ElectoralOracle is Owned {
    struct Poll {
        string region;
        string candidate;
        uint256 voteCount;
        uint256 lastUpdated;
    }

    mapping(bytes32 => Poll) public polls;

    event PollUpdated(string region, string candidate, uint256 voteCount);

    constructor() Owned(msg.sender) {}

    function updatePoll(string calldata region, string calldata candidate, uint256 voteCount) external onlyOwner {
        bytes32 pollId = keccak256(abi.encodePacked(region, candidate));
        polls[pollId] = Poll(region, candidate, voteCount, block.timestamp);
        emit PollUpdated(region, candidate, voteCount);
    }
}
