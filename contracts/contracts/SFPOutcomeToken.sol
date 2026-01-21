// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title SFPOutcomeToken
 * @dev ERC-1155 for SFP (Structured Financial Product) outcome tokens on L2.
 * Used for Polymarket-style prediction market outcomes on OUTCOME_TOKEN_CHAIN_ID.
 * Only owner (or configured minter) can mint; holders can transfer/sell per ERC-1155.
 */
contract SFPOutcomeToken is ERC1155, Ownable {
    event OutcomeMinted(
        uint256 indexed outcomeTokenId,
        address indexed to,
        uint256 amount,
        bytes data
    );

    constructor(string memory uri_) ERC1155(uri_) Ownable(msg.sender) {}

    /**
     * @dev Mint outcome tokens to a recipient. Only owner. outcomeTokenId is the
     * ERC-1155 token id (e.g. market-specific outcome index). amount in token units.
     */
    function mint(
        address to,
        uint256 outcomeTokenId,
        uint256 amount,
        bytes memory data
    ) external onlyOwner {
        require(to != address(0), "Invalid recipient");
        _mint(to, outcomeTokenId, amount, data);
        emit OutcomeMinted(outcomeTokenId, to, amount, data);
    }

    /**
     * @dev Batch mint for multiple outcome ids to one recipient.
     */
    function mintBatch(
        address to,
        uint256[] memory ids,
        uint256[] memory amounts,
        bytes memory data
    ) external onlyOwner {
        require(to != address(0), "Invalid recipient");
        require(ids.length == amounts.length, "Length mismatch");
        _mintBatch(to, ids, amounts, data);
    }

    /**
     * @dev Update base URI for token metadata.
     */
    function setURI(string memory newUri) external onlyOwner {
        _setURI(newUri);
    }
}
