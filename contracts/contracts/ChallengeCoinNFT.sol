// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title ChallengeCoinNFT
 * @dev ERC-721 NFT representing a securitized asset (challenge coin).
 * Each NFT represents ownership/proof of a securitized asset.
 * Can be traded across chains via lockForBridge -> bridgeToken (burn on source; mint on dest by bridge).
 */
contract ChallengeCoinNFT is ERC721Enumerable, ERC721URIStorage, Ownable {
    struct AssetMetadata {
        string assetId;
        string dealId;
        string assetType;
        uint256 principalAmount;
        uint256 issueDate;
        address issuer;
        string metadataURI;
        bool locked;
        uint256 lockedUntil;
    }

    mapping(uint256 => AssetMetadata) public assetMetadata;
    mapping(string => uint256) public assetIdToTokenId;
    mapping(address => bool) public authorizedIssuers;

    uint256 private _tokenIdCounter;

    event ChallengeCoinMinted(
        uint256 indexed tokenId,
        string indexed assetId,
        string dealId,
        address indexed issuer,
        address to
    );
    event ChallengeCoinLocked(uint256 indexed tokenId, uint256 lockedUntil);
    event ChallengeCoinUnlocked(uint256 indexed tokenId);
    event ChallengeCoinBridged(
        uint256 indexed tokenId,
        uint256 indexed targetChainId,
        address indexed targetAddress
    );
    event IssuerAuthorized(address indexed issuer);
    event IssuerRevoked(address indexed issuer);

    constructor() ERC721("ChallengeCoin", "CHAL") Ownable(msg.sender) {
        _tokenIdCounter = 1;
    }

    /**
     * @dev Mint challenge coin NFT for securitized asset. Callable by owner or authorizedIssuers.
     */
    function mintChallengeCoin(
        address to,
        string memory assetId,
        string memory dealId,
        string memory assetType,
        uint256 principalAmount,
        string memory metadataURI
    ) external returns (uint256) {
        require(
            authorizedIssuers[msg.sender] || msg.sender == owner(),
            "Not authorized to issue challenge coins"
        );
        require(assetIdToTokenId[assetId] == 0, "Asset ID already minted");
        require(to != address(0), "Invalid recipient");

        uint256 tokenId = _tokenIdCounter++;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, metadataURI);

        assetMetadata[tokenId] = AssetMetadata({
            assetId: assetId,
            dealId: dealId,
            assetType: assetType,
            principalAmount: principalAmount,
            issueDate: block.timestamp,
            issuer: msg.sender,
            metadataURI: metadataURI,
            locked: false,
            lockedUntil: 0
        });
        assetIdToTokenId[assetId] = tokenId;

        emit ChallengeCoinMinted(tokenId, assetId, dealId, msg.sender, to);
        return tokenId;
    }

    /**
     * @dev Lock NFT for cross-chain transfer. Only token owner.
     */
    function lockForBridge(uint256 tokenId, uint256 lockDuration) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(!assetMetadata[tokenId].locked, "Already locked");

        assetMetadata[tokenId].locked = true;
        assetMetadata[tokenId].lockedUntil = block.timestamp + lockDuration;

        emit ChallengeCoinLocked(tokenId, assetMetadata[tokenId].lockedUntil);
    }

    /**
     * @dev Unlock NFT after bridge transfer or if bridge is cancelled. Only owner.
     */
    function unlockFromBridge(uint256 tokenId) external onlyOwner {
        require(assetMetadata[tokenId].locked, "Not locked");

        assetMetadata[tokenId].locked = false;
        assetMetadata[tokenId].lockedUntil = 0;

        emit ChallengeCoinUnlocked(tokenId);
    }

    /**
     * @dev Mark NFT as bridged: burn on source. Mint on destination is done by bridge/relayer.
     * Only owner (bridge backoffice). Token must be locked.
     */
    function bridgeToken(
        uint256 tokenId,
        uint256 targetChainId,
        address targetAddress
    ) external onlyOwner {
        require(assetMetadata[tokenId].locked, "Token must be locked");
        require(targetAddress != address(0), "Invalid target");

        string memory assetId = assetMetadata[tokenId].assetId;

        _burn(tokenId);
        delete assetIdToTokenId[assetId];
        delete assetMetadata[tokenId];

        emit ChallengeCoinBridged(tokenId, targetChainId, targetAddress);
    }

    /**
     * @dev Authorize an address to mint challenge coins.
     */
    function authorizeIssuer(address issuer) external onlyOwner {
        require(issuer != address(0), "Invalid issuer");
        authorizedIssuers[issuer] = true;
        emit IssuerAuthorized(issuer);
    }

    /**
     * @dev Revoke issuer authorization.
     */
    function revokeIssuer(address issuer) external onlyOwner {
        authorizedIssuers[issuer] = false;
        emit IssuerRevoked(issuer);
    }

    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override(ERC721, ERC721Enumerable) returns (address) {
        return super._update(to, tokenId, auth);
    }

    function _increaseBalance(
        address account,
        uint128 value
    ) internal override(ERC721, ERC721Enumerable) {
        super._increaseBalance(account, value);
    }

    function tokenURI(
        uint256 tokenId
    ) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721Enumerable, ERC721URIStorage) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    function getAssetMetadata(uint256 tokenId) external view returns (AssetMetadata memory) {
        require(ownerOf(tokenId) != address(0), "Token does not exist");
        return assetMetadata[tokenId];
    }
}
