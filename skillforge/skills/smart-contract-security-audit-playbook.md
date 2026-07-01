### Smart Contract Security Audit Playbook
#### When to use:
This playbook is used to perform a comprehensive security audit of smart contracts using a combination of static analysis and fuzz testing tools.

#### Step-by-Step Procedure:
1. **Initialize the environment**: Set up a Linux-based system with the necessary dependencies installed, including `foundry`, `slither`, `mythril`, `echidna`, and `aderyn`.
2. **Clone the contract repository**: Clone the repository containing the smart contract code using `git clone`.
3. **Install dependencies**: Install the required dependencies using `forge install`.
4. **Run static analysis**:
	* Use `slither` to analyze the contract code for potential security vulnerabilities: `slither .`
	* Use `mythril` to analyze the contract code for potential security vulnerabilities: `mythril analyze .`
	* Use `echidna` to analyze the contract code for potential security vulnerabilities: `echidna .`
	* Use `aderyn` to analyze the contract code for potential security vulnerabilities: `aderyn .`
5. **Run fuzz testing**:
	* Use `echidna` to perform fuzz testing on the contract code: `echidna test`
6. **Analyze results**: Review the output from the static analysis and fuzz testing tools to identify potential security vulnerabilities.
7. **Verify findings**: Verify the findings using `foundry` to ensure that the identified vulnerabilities are valid.

#### Quality Gates:
* All identified vulnerabilities must be verified using `foundry` before being reported.
* The contract code must be updated to address all identified vulnerabilities before being deployed.

#### Limitations:
* This playbook only covers static analysis and fuzz testing, and may not identify all potential security vulnerabilities.
* The effectiveness of this playbook depends on the quality of the contract code and the accuracy of the analysis tools.

#### Tools Used:
* `foundry`: A development framework for Ethereum smart contracts.
* `slither`: A static analysis tool for Ethereum smart contracts.
* `mythril`: A static analysis tool for Ethereum smart contracts.
* `echidna`: A fuzz testing tool for Ethereum smart contracts.
* `aderyn`: A static analysis tool for Ethereum smart contracts.

#### Example Use Case:
This playbook can be used to perform a security audit of a smart contract before it is deployed to the mainnet. For example, a developer can use this playbook to identify potential security vulnerabilities in their contract code and address them before deploying the contract.

_Distilled 2026-07-01T09:57:18Z from real SKILLFORGE memory._
