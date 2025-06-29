// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin-contracts-upgradeable/proxy/utils/Initializable.sol";

contract Organization is Initializable {
	struct Signer {
		string name;
		uint256 clearance; // higher better
	}

	struct Document {
		string contentIdentifier; // IPFS CID
		address signer;
	}

	struct OrganizationStorage {
		mapping(address => Signer) signers;
		mapping(bytes32 => Document) documents;
	}

	event SignerAdded(address indexed signer, string name, uint256 clearance);
	event SignerRemoved(address indexed signer);
	event SignerUpdated(address indexed by, address indexed signer, string name, uint256 clearance);
	event Signed(address indexed signer, bytes32 indexed documentId, string contentIdentifier);

	// uint256(bytes32(uint256(keccak256("enver.organization.storage")) - 1) & ~bytes32(uint256(0xff)))
	uint256 private constant OrganizationStorageLocation = 0x2c5710643274822e9146eebc0dd5a89aeab71cfdbd022359a604f85d0af1ba00;

	constructor() {
		_disableInitializers();
	}

	function _getOrganizationStorage() private pure returns (OrganizationStorage storage $) {
		assembly {	
			$.slot := OrganizationStorageLocation
		}
	}

	function initialize() public initializer {
		_addSigner(msg.sender, "admin", type(uint256).max);
	}

	function addSigner(address signer, string memory name, uint256 clearance) external {
		OrganizationStorage storage $ = _getOrganizationStorage();
		require(msg.sender == address(this) || $.signers[msg.sender].clearance > clearance, "Insufficient clearance");
		_addSigner(signer, name, clearance);
	}

	function changeSigner(address signer, string memory name, uint256 clearance) external {
		OrganizationStorage storage $ = _getOrganizationStorage();
		Signer memory author = $.signers[msg.sender];
		require(
			msg.sender == address(this) ||
			author.clearance > clearance ||
			(author.clearance == type(uint256).max && clearance == type(uint256).max)
		, "Insufficient clearance");
		require($.signers[signer].clearance > 0, "Signer does not exist");

		$.signers[signer] = Signer(name, clearance);
		emit SignerUpdated(msg.sender, signer, name, clearance);
	}

	function _addSigner(address signer, string memory name, uint256 clearance) internal {
		OrganizationStorage storage $ = _getOrganizationStorage();
		require(signer != address(0), "Invalid signer address");
		require(bytes(name).length > 0, "Name cannot be empty");

		$.signers[signer] = Signer(name, clearance);
		emit SignerAdded(signer, name, clearance);
	}
}