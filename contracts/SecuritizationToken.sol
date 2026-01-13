// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title SecuritizationToken
 * @dev ERC-721 NFT representing ownership of securitization tranches
 * Each NFT represents a tranche position with payment rights
 * Integrates with x402 for USDC payment distributions
 */
contract SecuritizationToken is ERC721Enumerable, Ownable {
    // USDC token address (Base network)
    address public constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    
    struct TranchePosition {
        string poolId;
        string trancheId;
        uint256 principalAmount;  // In USDC (6 decimals)
        uint256 interestRate;     // Basis points (e.g., 500 = 5%)
        uint256 paymentPriority; // Lower = higher priority
        uint256 totalPaid;        // Cumulative payments received
        bool active;
    }
    
    mapping(uint256 => TranchePosition) public tranchePositions;
    mapping(string => uint256[]) public poolTokens; // poolId => tokenIds
    
    event TrancheMinted(
        uint256 indexed tokenId,
        string poolId,
        string trancheId,
        address owner,
        uint256 principalAmount
    );
    
    event PaymentDistributed(
        uint256 indexed tokenId,
        uint256 amount,
        string paymentType // "interest" or "principal"
    );
    
    constructor() ERC721("SecuritizationTranche", "SEC-TR") Ownable(msg.sender) {}
    
    /**
     * @dev Mint NFT for tranche position
     * @param to Owner address
     * @param poolId Pool identifier
     * @param trancheId Tranche identifier
     * @param principalAmount Principal amount in USDC (6 decimals)
     * @param interestRate Interest rate in basis points
     * @param paymentPriority Payment priority
     */
    function mintTranche(
        address to,
        string memory poolId,
        string memory trancheId,
        uint256 principalAmount,
        uint256 interestRate,
        uint256 paymentPriority
    ) external onlyOwner returns (uint256) {
        uint256 tokenId = totalSupply() + 1;
        
        _safeMint(to, tokenId);
        
        tranchePositions[tokenId] = TranchePosition({
            poolId: poolId,
            trancheId: trancheId,
            principalAmount: principalAmount,
            interestRate: interestRate,
            paymentPriority: paymentPriority,
            totalPaid: 0,
            active: true
        });
        
        poolTokens[poolId].push(tokenId);
        
        emit TrancheMinted(tokenId, poolId, trancheId, to, principalAmount);
        
        return tokenId;
    }
    
    /**
     * @dev Distribute payment to tranche holder
     * Called by payment service after x402 settlement
     * @param tokenId NFT token ID
     * @param amount Payment amount in USDC (6 decimals)
     * @param paymentType "interest" or "principal"
     */
    function distributePayment(
        uint256 tokenId,
        uint256 amount,
        string memory paymentType
    ) external onlyOwner {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        TranchePosition storage position = tranchePositions[tokenId];
        require(position.active, "Tranche not active");
        
        address owner = ownerOf(tokenId);
        
        // Transfer USDC to token owner
        IERC20(USDC).transfer(owner, amount);
        
        position.totalPaid += amount;
        
        emit PaymentDistributed(tokenId, amount, paymentType);
    }
    
    /**
     * @dev Get tranche position details
     */
    function getTranchePosition(uint256 tokenId)
        external
        view
        returns (TranchePosition memory)
    {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return tranchePositions[tokenId];
    }
    
    /**
     * @dev Get all tokens for a pool
     */
    function getPoolTokens(string memory poolId)
        external
        view
        returns (uint256[] memory)
    {
        return poolTokens[poolId];
    }
}
