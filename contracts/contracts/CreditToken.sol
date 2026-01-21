// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CreditToken
 * @dev ERC-721 NFT representing credit balances on organization blockchain.
 * Each token represents a user's credit balance with type-specific amounts.
 * Used by RollingCreditsService for subscription-generated credits.
 */
contract CreditToken is ERC721Enumerable, ERC721URIStorage, Ownable {
    struct CreditBalanceStruct {
        uint256 signing;
        uint256 documentReview;
        uint256 verification;
        uint256 trading;
        uint256 loaning;
        uint256 borrowing;
        uint256 complianceCheck;
        uint256 securitization;
        uint256 riskAnalysis;
        uint256 quantitativeAnalysis;
        uint256 stockPredictionDaily;
        uint256 stockPredictionHourly;
        uint256 stockPrediction15min;
        uint256 universal;
    }

    mapping(uint256 => CreditBalanceStruct) public creditBalances;
    mapping(address => uint256) public userTokenIds;
    mapping(uint256 => address) public tokenOwners;

    uint256 private _tokenIdCounter;

    event CreditsMinted(uint256 indexed tokenId, address indexed user, CreditBalanceStruct credits);
    event CreditsUpdated(uint256 indexed tokenId, address indexed user, string creditType, uint256 amount, bool isSpend);
    event CreditsBridged(uint256 indexed tokenId, uint256 targetChainId, address targetAddress);

    constructor() ERC721("CreditNexus Credits", "CNCRED") Ownable(msg.sender) {}

    /**
     * @dev Mint credit token for user (called when subscription generates credits).
     */
    function mintCredits(address user, CreditBalanceStruct memory credits) external onlyOwner returns (uint256) {
        require(user != address(0), "Invalid user address");
        uint256 tokenId = _tokenIdCounter++;
        _safeMint(user, tokenId);
        creditBalances[tokenId] = credits;
        userTokenIds[user] = tokenId;
        tokenOwners[tokenId] = user;
        emit CreditsMinted(tokenId, user, credits);
        return tokenId;
    }

    /**
     * @dev Update credits for a token (spend or earn). Amount in 4 decimals (e.g. 10000 = 1.0).
     */
    function updateCredits(uint256 tokenId, string memory creditType, uint256 amount, bool isSpend) external onlyOwner {
        require(ownerOf(tokenId) != address(0), "Token does not exist");
        CreditBalanceStruct storage balance = creditBalances[tokenId];
        if (isSpend) {
            require(_getCreditBalance(balance, creditType) >= amount, "Insufficient credits");
            _decreaseCreditBalance(balance, creditType, amount);
        } else {
            _increaseCreditBalance(balance, creditType, amount);
        }
        emit CreditsUpdated(tokenId, tokenOwners[tokenId], creditType, amount, isSpend);
    }

    function getCreditBalance(uint256 tokenId, string memory creditType) external view returns (uint256) {
        require(ownerOf(tokenId) != address(0), "Token does not exist");
        return _getCreditBalance(creditBalances[tokenId], creditType);
    }

    function getAllCredits(uint256 tokenId) external view returns (CreditBalanceStruct memory) {
        require(ownerOf(tokenId) != address(0), "Token does not exist");
        return creditBalances[tokenId];
    }

    function lockForBridge(uint256 tokenId, uint256 /* duration */) external onlyOwner {
        require(ownerOf(tokenId) != address(0), "Token does not exist");
        // Placeholder: lock state can be added when bridge is implemented.
    }

    function bridgeCredits(uint256 tokenId, uint256 targetChainId, address targetAddress) external onlyOwner {
        require(ownerOf(tokenId) != address(0), "Token does not exist");
        emit CreditsBridged(tokenId, targetChainId, targetAddress);
    }

    function _getCreditBalance(CreditBalanceStruct memory balance, string memory creditType) internal pure returns (uint256) {
        bytes32 h = keccak256(bytes(creditType));
        if (h == keccak256("signing")) return balance.signing;
        if (h == keccak256("document_review")) return balance.documentReview;
        if (h == keccak256("verification")) return balance.verification;
        if (h == keccak256("trading")) return balance.trading;
        if (h == keccak256("loaning")) return balance.loaning;
        if (h == keccak256("borrowing")) return balance.borrowing;
        if (h == keccak256("compliance_check")) return balance.complianceCheck;
        if (h == keccak256("securitization")) return balance.securitization;
        if (h == keccak256("risk_analysis")) return balance.riskAnalysis;
        if (h == keccak256("quantitative_analysis")) return balance.quantitativeAnalysis;
        if (h == keccak256("stock_prediction_daily")) return balance.stockPredictionDaily;
        if (h == keccak256("stock_prediction_hourly")) return balance.stockPredictionHourly;
        if (h == keccak256("stock_prediction_15min")) return balance.stockPrediction15min;
        if (h == keccak256("universal")) return balance.universal;
        return 0;
    }

    function _increaseCreditBalance(CreditBalanceStruct storage balance, string memory creditType, uint256 amount) internal {
        bytes32 h = keccak256(bytes(creditType));
        if (h == keccak256("signing")) balance.signing += amount;
        else if (h == keccak256("document_review")) balance.documentReview += amount;
        else if (h == keccak256("verification")) balance.verification += amount;
        else if (h == keccak256("trading")) balance.trading += amount;
        else if (h == keccak256("loaning")) balance.loaning += amount;
        else if (h == keccak256("borrowing")) balance.borrowing += amount;
        else if (h == keccak256("compliance_check")) balance.complianceCheck += amount;
        else if (h == keccak256("securitization")) balance.securitization += amount;
        else if (h == keccak256("risk_analysis")) balance.riskAnalysis += amount;
        else if (h == keccak256("quantitative_analysis")) balance.quantitativeAnalysis += amount;
        else if (h == keccak256("stock_prediction_daily")) balance.stockPredictionDaily += amount;
        else if (h == keccak256("stock_prediction_hourly")) balance.stockPredictionHourly += amount;
        else if (h == keccak256("stock_prediction_15min")) balance.stockPrediction15min += amount;
        else if (h == keccak256("universal")) balance.universal += amount;
    }

    function _decreaseCreditBalance(CreditBalanceStruct storage balance, string memory creditType, uint256 amount) internal {
        bytes32 h = keccak256(bytes(creditType));
        if (h == keccak256("signing")) balance.signing -= amount;
        else if (h == keccak256("document_review")) balance.documentReview -= amount;
        else if (h == keccak256("verification")) balance.verification -= amount;
        else if (h == keccak256("trading")) balance.trading -= amount;
        else if (h == keccak256("loaning")) balance.loaning -= amount;
        else if (h == keccak256("borrowing")) balance.borrowing -= amount;
        else if (h == keccak256("compliance_check")) balance.complianceCheck -= amount;
        else if (h == keccak256("securitization")) balance.securitization -= amount;
        else if (h == keccak256("risk_analysis")) balance.riskAnalysis -= amount;
        else if (h == keccak256("quantitative_analysis")) balance.quantitativeAnalysis -= amount;
        else if (h == keccak256("stock_prediction_daily")) balance.stockPredictionDaily -= amount;
        else if (h == keccak256("stock_prediction_hourly")) balance.stockPredictionHourly -= amount;
        else if (h == keccak256("stock_prediction_15min")) balance.stockPrediction15min -= amount;
        else if (h == keccak256("universal")) balance.universal -= amount;
    }

    function _update(address to, uint256 tokenId, address auth) internal override(ERC721, ERC721Enumerable) returns (address) {
        return super._update(to, tokenId, auth);
    }

    function _increaseBalance(address account, uint128 value) internal override(ERC721, ERC721Enumerable) {
        super._increaseBalance(account, value);
    }

    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC721Enumerable, ERC721URIStorage) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}
