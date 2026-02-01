/**
 * Build Aptos payment payload for x402 verify/settle.
 * Signs a transfer (0x1::primary_fungible_store::transfer) and returns
 * payload in facilitator shape: { transaction, senderAuthenticator } (BCS bytes as arrays).
 */

import { getAptosConfig } from './config.js';
import { getWallet } from './wallet.js';

/**
 * Build signed Aptos payment payload for the given payment requirements.
 * Amount is in atomic units (e.g. 6e4 for 0.06 USDC with 6 decimals).
 * @param {import('../x402/types.js').PaymentRequirements} paymentRequirements - amount, asset, payTo, network
 * @param {{ address: string, privateKey: string }} [wallet] - optional; uses saved wallet if omitted
 * @returns {Promise<{ scheme: string, network: string, payload: { transaction: number[], senderAuthenticator: number[] } }>}
 */
export async function buildAptosPaymentPayload(paymentRequirements, wallet) {
  const w = wallet || getWallet();
  const network = paymentRequirements.network || 'aptos:2';
  const amount = BigInt(
    typeof paymentRequirements.amount === 'number'
      ? paymentRequirements.amount
      : String(paymentRequirements.amount)
  );
  const asset = paymentRequirements.asset || '';
  const payTo = paymentRequirements.payTo || '';

  try {
    const { Account, Aptos, AptosConfig, Network, Ed25519PrivateKey } = await import('@aptos-labs/ts-sdk');

    // Create Ed25519PrivateKey from hex string
    const privateKey = new Ed25519PrivateKey(w.privateKey);
    const account = Account.fromPrivateKey({ privateKey, legacy: false });

    const net = network === 'aptos:1' ? Network.MAINNET : Network.TESTNET;
    const aptosConfig = new AptosConfig({ fullnode: getAptosConfig(network === 'aptos:1' ? 'mainnet' : 'testnet').nodeUrl, network: net });
    const aptos = new Aptos(aptosConfig);

    // For APT (AptosCoin), use aptos_account::transfer instead of primary_fungible_store
    const isAptCoin = asset === '0x1::aptos_coin::AptosCoin';

    const builder = await aptos.transaction.build.simple({
      sender: account.accountAddress,
      withFeePayer: false,
      data: isAptCoin ? {
        function: '0x1::aptos_account::transfer',
        functionArguments: [payTo, amount],
      } : {
        function: '0x1::primary_fungible_store::transfer',
        typeArguments: [asset],
        functionArguments: [payTo, amount],
      },
    });

    // Sign the transaction and get the authenticator
    const accountAuthenticator = await aptos.transaction.sign({ signer: account, transaction: builder });

    // Get BCS bytes
    const transactionBytes = builder.bcsToBytes();
    const senderAuthenticatorBytes = accountAuthenticator.bcsToBytes();

    return {
      scheme: paymentRequirements.scheme || 'exact',
      network,
      payload: {
        transaction: Array.from(transactionBytes),
        senderAuthenticator: Array.from(senderAuthenticatorBytes),
      },
    };
  } catch (e) {
    if (e.code === 'ERR_MODULE_NOT_FOUND' || (e.message && e.message.includes('@aptos-labs/ts-sdk'))) {
      throw new Error('Aptos SDK required: npm install @aptos-labs/ts-sdk');
    }
    throw e;
  }
}
