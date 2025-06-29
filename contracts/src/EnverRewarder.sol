// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin-contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";

contract EnverRewarder is ERC20Upgradeable {
	// uint256(bytes32(uint256(keccak256("enver.rewarder.storage")) - 1) & ~bytes32(uint256(0xff)))
	uint256 private constant RewarderStorageLocation = 0x1fa32c48b9b6c958e0c80f8a4f5fdeca03fab99406b58f04af72bca72aed7e00;

	struct RewarderStorage {
		uint256 rewardPerShare;
		uint256 totalSupply;
	}

	constructor() {
		_disableInitializers();
	}

	function initialize() public initializer {
		__ERC20_init("Enver Protocol", "ENVR");
		_mint(msg.sender, 1_000_000_000 * 10 ** decimals());
	}

	// soon :)
	receive() external payable {}
	fallback() external payable {}
}