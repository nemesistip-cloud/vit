// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Owned} from "lib/solmate/src/auth/Owned.sol";

contract ShopManager is Owned {
    struct Shop {
        string name;
        address owner;
        string location;
        bool active;
        uint256 commissionRate; // in basis points
    }

    mapping(address => Shop) public shops;
    address[] public shopList;

    event ShopRegistered(address indexed shopAddress, string name, string location);

    constructor() Owned(msg.sender) {}

    function registerShop(address shopAddress, string calldata name, string calldata location, uint256 commissionRate) external onlyOwner {
        require(shops[shopAddress].owner == address(0), "Shop already registered");

        shops[shopAddress] = Shop({
            name: name,
            owner: shopAddress,
            location: location,
            active: true,
            commissionRate: commissionRate
        });
        shopList.push(shopAddress);

        emit ShopRegistered(shopAddress, name, location);
    }

    function setShopStatus(address shopAddress, bool status) external onlyOwner {
        shops[shopAddress].active = status;
    }
}
