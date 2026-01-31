/**
 * Aptos chain config: testnet node URL, USDC asset, network id.
 * From X402_HACKATHON_PLAN §15.1.
 */

export const APTOS_TESTNET_NODE_URL = 'https://fullnode.testnet.aptoslabs.com/v1';
export const APTOS_MAINNET_NODE_URL = 'https://fullnode.mainnet.aptoslabs.com/v1';

/** USDC asset type on Aptos testnet (resource address). */
export const USDC_ASSET_TESTNET =
  '0x69091fbab5f7d635ee7ac5098cf0c1efbe31d68fec0f2cd565e8d168daf52832';

export const NETWORK_ID_TESTNET = 'aptos:2';
export const NETWORK_ID_MAINNET = 'aptos:1';

export const config = {
  testnet: {
    nodeUrl: APTOS_TESTNET_NODE_URL,
    networkId: NETWORK_ID_TESTNET,
    usdcAsset: USDC_ASSET_TESTNET,
  },
  mainnet: {
    nodeUrl: APTOS_MAINNET_NODE_URL,
    networkId: NETWORK_ID_MAINNET,
    usdcAsset: null, // set per mainnet deployment
  },
};

/**
 * @param {'testnet'|'mainnet'} [env] - default testnet
 * @returns {{ nodeUrl: string, networkId: string, usdcAsset: string|null }}
 */
export function getAptosConfig(env = 'testnet') {
  return config[env] || config.testnet;
}
