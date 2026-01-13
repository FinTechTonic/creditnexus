const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await hre.ethers.provider.getBalance(deployer.address)).toString());

  // Deploy SecuritizationNotarization
  console.log("\nDeploying SecuritizationNotarization...");
  const SecuritizationNotarization = await hre.ethers.getContractFactory("SecuritizationNotarization");
  const notarization = await SecuritizationNotarization.deploy();
  await notarization.waitForDeployment();
  const notarizationAddress = await notarization.getAddress();
  console.log("SecuritizationNotarization deployed to:", notarizationAddress);

  // Deploy SecuritizationToken
  console.log("\nDeploying SecuritizationToken...");
  const SecuritizationToken = await hre.ethers.getContractFactory("SecuritizationToken");
  const token = await SecuritizationToken.deploy();
  await token.waitForDeployment();
  const tokenAddress = await token.getAddress();
  console.log("SecuritizationToken deployed to:", tokenAddress);

  // Deploy SecuritizationPaymentRouter
  console.log("\nDeploying SecuritizationPaymentRouter...");
  const SecuritizationPaymentRouter = await hre.ethers.getContractFactory("SecuritizationPaymentRouter");
  const router = await SecuritizationPaymentRouter.deploy(tokenAddress);
  await router.waitForDeployment();
  const routerAddress = await router.getAddress();
  console.log("SecuritizationPaymentRouter deployed to:", routerAddress);

  console.log("\n=== Deployment Summary ===");
  console.log("SecuritizationNotarization:", notarizationAddress);
  console.log("SecuritizationToken:", tokenAddress);
  console.log("SecuritizationPaymentRouter:", routerAddress);
  
  console.log("\nAdd these addresses to your .env file:");
  console.log(`SECURITIZATION_NOTARIZATION_CONTRACT=${notarizationAddress}`);
  console.log(`SECURITIZATION_TOKEN_CONTRACT=${tokenAddress}`);
  console.log(`SECURITIZATION_PAYMENT_ROUTER_CONTRACT=${routerAddress}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
