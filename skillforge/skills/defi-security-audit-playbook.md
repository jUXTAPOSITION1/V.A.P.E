### DeFi Security Audit Playbook
#### When to Use
This playbook is designed to be used when performing a security audit on DeFi smart contracts, particularly those that have been identified as high-risk or have been compromised in the past.

#### Step-by-Step Procedure
1. **Initialize the audit environment**:
	* Set up a clean environment with the necessary tools, including `slither`, `mythril`, `echidna`, and `foundry`.
	* Ensure that all tools are up-to-date and verified.
2. **Gather contract information**:
	* Identify the contract address and ABI.
	* Use `base_rpc` to retrieve contract bytecode and other relevant information.
3. **Run static analysis tools**:
	* Use `slither` to analyze the contract's code and identify potential vulnerabilities.
	* Run `mythril` to detect potential security issues, such as reentrancy attacks.
4. **Perform fuzz testing**:
	* Use `echidna` to perform fuzz testing on the contract and identify potential issues.
5. **Run dynamic analysis tools**:
	* Use `foundry` to deploy and test the contract on a local network.
	* Run `garak` to analyze the contract's behavior and identify potential security issues.
6. **Analyze results and identify vulnerabilities**:
	* Review the results from the static and dynamic analysis tools.
	* Identify potential vulnerabilities and prioritize them based on severity and likelihood of exploitation.
7. **Create a report and provide recommendations**:
	* Create a detailed report outlining the vulnerabilities and potential risks.
	* Provide recommendations for remediation and mitigation.

#### Quality Gates
* All tools must be verified and up-to-date before use.
* All contract information must be accurate and complete.
* All analysis results must be thoroughly reviewed and validated.

#### Limitations
* This playbook is not a substitute for human review and expertise.
* The effectiveness of this playbook depends on the quality of the tools and the accuracy of the contract information.
* This playbook may not detect all potential vulnerabilities or security issues.

#### Example Use Case
This playbook can be used to audit a DeFi smart contract that has been identified as high-risk or has been compromised in the past. For example, the `Taiko Bridge` contract that was exploited due to a leaked RSA-3072 signing key can be audited using this playbook to identify potential vulnerabilities and provide recommendations for remediation and mitigation.

#### Tools Used
* `slither`
* `mythril`
* `echidna`
* `foundry`
* `garak`
* `base_rpc`

Note: This playbook is based on real data and uses verified tools to provide a comprehensive security audit process for DeFi smart contracts.

_Distilled 2026-07-02T09:20:01Z from real SKILLFORGE memory._
