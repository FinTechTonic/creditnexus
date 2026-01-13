// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./SecuritizationToken.sol";

/**
 * @title SecuritizationPaymentRouter
 * @dev Router contract for handling x402 payments for securitization
 * Processes payments and distributes to tranche holders via SecuritizationToken
 */
contract SecuritizationPaymentRouter is Ownable {
    address public constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    SecuritizationToken public securitizationToken;
    
    struct PaymentSchedule {
        string poolId;
        uint256 nextPaymentDate;
        uint256 paymentAmount;
        bool active;
    }
    
    mapping(string => PaymentSchedule) public paymentSchedules;
    
    event PaymentProcessed(
        string indexed poolId,
        uint256 totalAmount,
        uint256 timestamp
    );
    
    constructor(address _securitizationToken) Ownable(msg.sender) {
        securitizationToken = SecuritizationToken(_securitizationToken);
    }
    
    /**
     * @dev Process payment distribution for a pool
     * Called after x402 payment settlement
     * @param poolId Pool identifier
     * @param totalAmount Total payment amount in USDC
     */
    function processPoolPayment(
        string memory poolId,
        uint256 totalAmount
    ) external onlyOwner {
        require(totalAmount > 0, "Amount must be greater than zero");
        
        // Get all tranche tokens for this pool
        uint256[] memory tokenIds = securitizationToken.getPoolTokens(poolId);
        require(tokenIds.length > 0, "No tranches found for pool");
        
        // Calculate total principal for all active tranches
        uint256 totalPrincipal = 0;
        for (uint i = 0; i < tokenIds.length; i++) {
            SecuritizationToken.TranchePosition memory position = 
                securitizationToken.getTranchePosition(tokenIds[i]);
            if (position.active) {
                totalPrincipal += position.principalAmount;
            }
        }
        
        // Distribute payments according to waterfall
        // Senior tranches get paid first, then mezzanine, then equity
        uint256 remaining = totalAmount;
        
        // Sort by payment priority (simple bubble sort for small arrays)
        // In production, use a more efficient sorting algorithm
        for (uint i = 0; i < tokenIds.length - 1; i++) {
            for (uint j = 0; j < tokenIds.length - i - 1; j++) {
                SecuritizationToken.TranchePosition memory pos1 = 
                    securitizationToken.getTranchePosition(tokenIds[j]);
                SecuritizationToken.TranchePosition memory pos2 = 
                    securitizationToken.getTranchePosition(tokenIds[j + 1]);
                
                if (pos1.paymentPriority > pos2.paymentPriority) {
                    uint256 temp = tokenIds[j];
                    tokenIds[j] = tokenIds[j + 1];
                    tokenIds[j + 1] = temp;
                }
            }
        }
        
        // Distribute payments in priority order
        for (uint i = 0; i < tokenIds.length && remaining > 0; i++) {
            SecuritizationToken.TranchePosition memory position = 
                securitizationToken.getTranchePosition(tokenIds[i]);
            
            if (!position.active) continue;
            
            // Calculate payment for this tranche based on priority
            uint256 tranchePayment = 0;
            
            if (position.paymentPriority == 1) {
                // Senior tranche: pay interest first, then principal
                uint256 interestDue = (position.principalAmount * position.interestRate) / 10000;
                if (remaining >= interestDue) {
                    tranchePayment = interestDue;
                    remaining -= interestDue;
                } else {
                    tranchePayment = remaining;
                    remaining = 0;
                }
            } else if (position.paymentPriority == 2) {
                // Mezzanine: pay after senior
                if (remaining > 0) {
                    uint256 interestDue = (position.principalAmount * position.interestRate) / 10000;
                    tranchePayment = remaining >= interestDue ? interestDue : remaining;
                    remaining -= tranchePayment;
                }
            } else {
                // Equity: residual payments
                if (remaining > 0) {
                    tranchePayment = remaining;
                    remaining = 0;
                }
            }
            
            if (tranchePayment > 0) {
                // Transfer USDC to router first (caller must approve)
                IERC20(USDC).transferFrom(msg.sender, address(this), tranchePayment);
                
                // Distribute to tranche holder
                securitizationToken.distributePayment(
                    tokenIds[i],
                    tranchePayment,
                    "interest"
                );
            }
        }
        
        emit PaymentProcessed(poolId, totalAmount, block.timestamp);
    }
    
    /**
     * @dev Set payment schedule for a pool
     */
    function setPaymentSchedule(
        string memory poolId,
        uint256 nextPaymentDate,
        uint256 paymentAmount
    ) external onlyOwner {
        paymentSchedules[poolId] = PaymentSchedule({
            poolId: poolId,
            nextPaymentDate: nextPaymentDate,
            paymentAmount: paymentAmount,
            active: true
        });
    }
}
