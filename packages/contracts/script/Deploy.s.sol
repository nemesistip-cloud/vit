// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import "lib/forge-std/src/Script.sol";
import "../src/VITToken.sol";
import "../src/UniversalOracle.sol";
import "../src/LoyaltyVault.sol";
import "../src/ShopManager.sol";

contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        VITToken vit = new VITToken();
        UniversalOracle oracle = new UniversalOracle();
        LoyaltyVault vault = new LoyaltyVault(address(vit));
        ShopManager shops = new ShopManager();

        console.log("VITToken deployed at:", address(vit));
        console.log("UniversalOracle deployed at:", address(oracle));
        console.log("LoyaltyVault deployed at:", address(vault));
        console.log("ShopManager deployed at:", address(shops));

        vm.stopBroadcast();
    }
}
