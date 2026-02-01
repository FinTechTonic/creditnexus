"""
Test the Aptos verifier with mock transactions
"""

import asyncio
from decimal import Decimal
from aptos_verifier import AptosVerifier, APTOS_USDC_ASSET


# Test wallets (from hackathon)
WALLET_3 = "0x924c2e983753bb29b45ae9b4036d48861f204da096b36af710c95d1742b05ad4"
WALLET_4 = "0xf1697d22257fd39653319eb3a2ee23fca2ca99b26f7fc79090249fbfbc401e03"


def create_mock_payment_payload(
    sender: str,
    receiver: str,
    amount_usd: str,
    signature: str = "0xmock_signature_12345"
) -> dict:
    """Create a mock payment payload for testing"""
    verifier = AptosVerifier(set(), set())
    atomic_amount = verifier.usd_to_atomic(amount_usd)

    return {
        "signature": signature,
        "transaction": {
            "sender": sender,
            "receiver": receiver,
            "amount": str(atomic_amount),
            "asset": APTOS_USDC_ASSET,
            "sequence_number": 1,
            "gas_unit_price": "100",
            "max_gas_amount": "1000"
        },
        "network": "aptos:2"
    }


def create_payment_requirements(
    amount_usd: str,
    pay_to: str,
    resource: str = "/mcp/test"
) -> dict:
    """Create payment requirements for testing"""
    return {
        "amount": amount_usd,
        "currency": "USD",
        "network": "aptos:2",
        "asset": APTOS_USDC_ASSET,
        "payTo": pay_to,
        "resource": resource,
        "description": "Test payment"
    }


async def test_valid_payment():
    """Test a valid payment that should pass all checks"""
    print("\n=== Test 1: Valid Payment ===")

    verifier = AptosVerifier(
        agent_allowlist={WALLET_4},  # Wallet 4 is the payer
        payto_allowlist={WALLET_3}   # Wallet 3 is the receiver
    )

    # Create mock payment: Wallet 4 sends 0.06 USDC to Wallet 3
    payload = create_mock_payment_payload(
        sender=WALLET_4,
        receiver=WALLET_3,
        amount_usd="0.06"
    )

    requirements = create_payment_requirements(
        amount_usd="0.06",
        pay_to=WALLET_3
    )

    result = await verifier.verify(payload, requirements)

    print(f"Result: {result}")
    assert result["isValid"] == True, f"Expected valid, got: {result}"
    assert result["payer"] == WALLET_4
    print("✅ PASSED")


async def test_insufficient_amount():
    """Test payment with insufficient amount"""
    print("\n=== Test 2: Insufficient Amount ===")

    verifier = AptosVerifier(
        agent_allowlist={WALLET_4},
        payto_allowlist={WALLET_3}
    )

    # Wallet 4 sends only 0.03 USDC but 0.06 is required
    payload = create_mock_payment_payload(
        sender=WALLET_4,
        receiver=WALLET_3,
        amount_usd="0.03"  # Too little!
    )

    requirements = create_payment_requirements(
        amount_usd="0.06",
        pay_to=WALLET_3
    )

    result = await verifier.verify(payload, requirements)

    print(f"Result: {result}")
    assert result["isValid"] == False
    assert "insufficient_amount" in result["invalidReason"]
    print("✅ PASSED")


async def test_wrong_receiver():
    """Test payment to wrong receiver"""
    print("\n=== Test 3: Wrong Receiver ===")

    verifier = AptosVerifier(
        agent_allowlist={WALLET_4},
        payto_allowlist={WALLET_3}
    )

    # Wallet 4 sends to wrong address
    wrong_address = "0x1234567890abcdef"
    payload = create_mock_payment_payload(
        sender=WALLET_4,
        receiver=wrong_address,  # Wrong!
        amount_usd="0.06"
    )

    requirements = create_payment_requirements(
        amount_usd="0.06",
        pay_to=WALLET_3  # Should be Wallet 3
    )

    result = await verifier.verify(payload, requirements)

    print(f"Result: {result}")
    assert result["isValid"] == False
    assert "invalid_receiver" in result["invalidReason"]
    print("✅ PASSED")


async def test_not_allowlisted():
    """Test payment from non-allowlisted address"""
    print("\n=== Test 4: Not Allowlisted ===")

    verifier = AptosVerifier(
        agent_allowlist={WALLET_3},  # Only Wallet 3 is allowed
        payto_allowlist={WALLET_3}
    )

    # Wallet 4 tries to pay but is not allowlisted
    payload = create_mock_payment_payload(
        sender=WALLET_4,  # Not in allowlist!
        receiver=WALLET_3,
        amount_usd="0.06"
    )

    requirements = create_payment_requirements(
        amount_usd="0.06",
        pay_to=WALLET_3
    )

    result = await verifier.verify(payload, requirements)

    print(f"Result: {result}")
    assert result["isValid"] == False
    assert "not_allowlisted" in result["invalidReason"]
    print("✅ PASSED")


async def test_settlement():
    """Test settlement of a valid payment"""
    print("\n=== Test 5: Settlement ===")

    verifier = AptosVerifier(
        agent_allowlist={WALLET_4},
        payto_allowlist={WALLET_3}
    )

    payload = create_mock_payment_payload(
        sender=WALLET_4,
        receiver=WALLET_3,
        amount_usd="0.06"
    )

    requirements = create_payment_requirements(
        amount_usd="0.06",
        pay_to=WALLET_3
    )

    # First verify
    verification = await verifier.verify(payload, requirements)
    assert verification["isValid"] == True

    # Then settle
    settlement = await verifier.settle(payload, verification)

    print(f"Settlement: {settlement}")
    assert settlement["success"] == True
    assert settlement["transaction"] is not None
    assert settlement["payer"] == WALLET_4
    print("✅ PASSED")


async def test_usd_conversion():
    """Test USD to atomic conversion"""
    print("\n=== Test 6: USD Conversion ===")

    verifier = AptosVerifier(set(), set())

    # Test various amounts
    test_cases = [
        ("0.06", 60000),       # 6 cents
        ("0.45", 450000),      # 45 cents
        ("3.65", 3650000),     # $3.65
        ("1.00", 1000000),     # 1 dollar
        ("0.000001", 1),       # Smallest unit
    ]

    for usd, expected_atomic in test_cases:
        atomic = verifier.usd_to_atomic(usd)
        print(f"  {usd} USD = {atomic} atomic units (expected {expected_atomic})")
        assert atomic == expected_atomic, f"Conversion failed for {usd}"

        # Test reverse conversion
        back_to_usd = verifier.atomic_to_usd(str(atomic))
        print(f"  {atomic} atomic = {back_to_usd} USD")
        # Compare as Decimal to avoid string formatting issues
        assert back_to_usd == Decimal(usd), f"Reverse conversion failed: {back_to_usd} != {usd}"

    print("✅ PASSED")


async def main():
    """Run all tests"""
    print("🧪 Testing Aptos Verifier")
    print("=" * 60)

    tests = [
        test_usd_conversion,
        test_valid_payment,
        test_insufficient_amount,
        test_wrong_receiver,
        test_not_allowlisted,
        test_settlement,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
