// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SecuritizationNotarization
 * @dev Smart contract for notarizing securitization pools on-chain
 * Supports multi-signer notarization with signature verification
 */
contract SecuritizationNotarization {
    struct NotarizationRecord {
        string poolId;
        bytes32 poolHash;
        address[] signers;
        mapping(address => bytes) signatures;
        bool completed;
        uint256 completedAt;
    }
    
    mapping(string => NotarizationRecord) public notarizations;
    mapping(string => bool) public poolNotarized;
    
    event NotarizationCreated(
        string indexed poolId,
        bytes32 poolHash,
        address[] signers
    );
    
    event SignatureAdded(
        string indexed poolId,
        address signer,
        bytes signature
    );
    
    event NotarizationCompleted(
        string indexed poolId,
        bytes32 poolHash,
        uint256 timestamp
    );
    
    /**
     * @dev Create a new notarization request
     * @param poolId Unique pool identifier
     * @param poolHash Hash of the CDM payload
     * @param signers Array of required signer addresses
     */
    function createNotarization(
        string memory poolId,
        bytes32 poolHash,
        address[] memory signers
    ) external {
        require(!poolNotarized[poolId], "Pool already notarized");
        require(signers.length > 0, "At least one signer required");
        
        NotarizationRecord storage record = notarizations[poolId];
        record.poolId = poolId;
        record.poolHash = poolHash;
        record.signers = signers;
        record.completed = false;
        
        emit NotarizationCreated(poolId, poolHash, signers);
    }
    
    /**
     * @dev Add a signature to the notarization
     * @param poolId Pool identifier
     * @param signature Signature bytes
     */
    function addSignature(
        string memory poolId,
        bytes memory signature
    ) external {
        NotarizationRecord storage record = notarizations[poolId];
        require(!record.completed, "Notarization already completed");
        require(record.signers.length > 0, "Notarization not found");
        
        address signer = msg.sender;
        bool isAuthorized = false;
        
        for (uint i = 0; i < record.signers.length; i++) {
            if (record.signers[i] == signer) {
                isAuthorized = true;
                break;
            }
        }
        
        require(isAuthorized, "Not an authorized signer");
        require(record.signatures[signer].length == 0, "Already signed");
        
        // Verify signature matches pool hash
        bytes32 messageHash = keccak256(abi.encodePacked(
            "\x19Ethereum Signed Message:\n32",
            record.poolHash
        ));
        
        address recovered = recoverSigner(messageHash, signature);
        require(recovered == signer, "Invalid signature");
        
        record.signatures[signer] = signature;
        
        emit SignatureAdded(poolId, signer, signature);
        
        // Check if all signers have signed
        bool allSigned = true;
        for (uint i = 0; i < record.signers.length; i++) {
            if (record.signatures[record.signers[i]].length == 0) {
                allSigned = false;
                break;
            }
        }
        
        if (allSigned) {
            record.completed = true;
            record.completedAt = block.timestamp;
            poolNotarized[poolId] = true;
            
            emit NotarizationCompleted(poolId, record.poolHash, block.timestamp);
        }
    }
    
    /**
     * @dev Recover signer address from signature
     */
    function recoverSigner(
        bytes32 messageHash,
        bytes memory signature
    ) internal pure returns (address) {
        require(signature.length == 65, "Invalid signature length");
        
        bytes32 r;
        bytes32 s;
        uint8 v;
        
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        
        if (v < 27) {
            v += 27;
        }
        
        require(v == 27 || v == 28, "Invalid signature");
        
        return ecrecover(messageHash, v, r, s);
    }
    
    /**
     * @dev Get notarization status
     */
    function getNotarizationStatus(string memory poolId)
        external
        view
        returns (
            bool completed,
            uint256 signersCount,
            uint256 signaturesCount
        )
    {
        NotarizationRecord storage record = notarizations[poolId];
        completed = record.completed;
        signersCount = record.signers.length;
        
        uint256 count = 0;
        for (uint i = 0; i < record.signers.length; i++) {
            if (record.signatures[record.signers[i]].length > 0) {
                count++;
            }
        }
        signaturesCount = count;
    }
}
