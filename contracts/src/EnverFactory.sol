// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin-contracts-upgradeable/access/Ownable2StepUpgradeable.sol";

import "./Organization.sol";

contract EnverFactory is Ownable2StepUpgradeable {
	struct FactoryStorage {
		mapping(bytes32 => address) organizations;
	}

	// uint256(bytes32(uint256(keccak256("enver.factory.storage"))-1) & ~bytes32(uint256(0xff)))
	uint256 private constant FactoryStorageLocation = 0xeb3626bd1ed2d7129edad48926490ac18369e3b2cc88259e04b14d0e8a11e400;

	event OrganizationCreated(bytes32 indexed orgId, address indexed orgAddress);

	constructor() {
		_disableInitializers();
	}

	function initialize() public initializer {
		__Ownable_init(msg.sender);
	}

	function _getFactoryStorage() private pure returns (FactoryStorage storage $) {
		assembly {
			$.slot := FactoryStorageLocation
		}
	}

	function createOrganization(bytes32 orgId) external onlyOwner returns (address newOrg) {
		FactoryStorage storage $ = _getFactoryStorage();
		require($.organizations[orgId] == address(0), "Organization already exists");

		newOrg = address(new Organization());
		$.organizations[orgId] = newOrg;

		emit OrganizationCreated(orgId, newOrg);
	}
}