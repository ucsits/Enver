// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable2StepUpgradeable.sol";

contract EnverFactory is Ownable2StepUpgradeable {
	struct EnverFactoryStorage {
		mapping(bytes32 => address) organizations;
	}

	constructor() {
		_disableInitializers();
	}

	function initialize() public initializer {
		__Ownable_init(msg.sender);
	}
}