// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Owned} from "lib/solmate/src/auth/Owned.sol";
import {BaseRelayRecipient} from "./BaseRelayRecipient.sol";

contract UniversalOracle is Owned, BaseRelayRecipient {
    struct Signal {
        string category; // sports, elections, policy, ecommerce
        string externalId; // e.g. fixture_id
        bytes data; // payload
        uint8 confidence; // 0-100
        uint256 timestamp;
        address provider;
    }

    mapping(bytes32 => Signal) public signals;
    mapping(address => bool) public authorizedProviders;

    event SignalPublished(bytes32 indexed signalId, string category, string externalId, uint8 confidence);

    constructor(address trustedForwarder) Owned(msg.sender) {
        authorizedProviders[msg.sender] = true;
        _setTrustedForwarder(trustedForwarder);
    }

    function setProvider(address provider, bool status) external onlyOwner {
        authorizedProviders[provider] = status;
    }

    function publishSignal(
        string calldata category,
        string calldata externalId,
        bytes calldata data,
        uint8 confidence
    ) external {
        address sender = _msgSender();
        require(authorizedProviders[sender], "Not authorized");
        bytes32 signalId = keccak256(abi.encodePacked(category, externalId, block.timestamp));

        signals[signalId] = Signal({
            category: category,
            externalId: externalId,
            data: data,
            confidence: confidence,
            timestamp: block.timestamp,
            provider: sender
        });

        emit SignalPublished(signalId, category, externalId, confidence);
    }
}
