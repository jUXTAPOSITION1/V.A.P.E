### Smart Contract Security Audit Playbook
#### When to use:
This playbook is designed to be used when performing a security audit on a smart contract. It is particularly useful when dealing with contracts that have been flagged for potential security issues or when investigating anomalies in contract behavior.

#### Step-by-Step Procedure:
1. **Initial Setup**: Ensure you have the necessary tools installed, including `slither`, `mythril`, and `echidna`.
2. **Contract Review**: Use `slither` to analyze the contract code and identify potential security vulnerabilities.
	* Run `slither <contract_address> --json` to generate a JSON report of the contract's security issues.
3. **Dynamic Analysis**: Use `mythril` to perform dynamic analysis on the contract.
	* Run `mythril <contract_address> --json` to generate a JSON report of the contract's security issues.
4. **Fuzz Testing**: Use `echidna` to perform fuzz testing on the contract.
	* Run `echidna <contract_address> --json` to generate a JSON report of the contract's security issues.
5. **Manual Review**: Manually review the contract code and analysis reports to identify potential security issues.
6. **Verification**: Use `foundry` to verify the contract's functionality and ensure it behaves as expected.
7. **Reporting**: Document all findings and recommendations in a clear and concise report.

#### Quality Gates:
* All contracts must be analyzed using `slither`, `mythril`, and `echidna` before being deployed.
* All identified security issues must be addressed before deployment.
* Contracts must be manually reviewed by a security expert before deployment.

#### Limitations:
* This playbook is not foolproof and may not identify all potential security issues.
* The effectiveness of this playbook relies on the quality of the tools used and the expertise of the security analyst performing the audit.

#### Example Use Case:
```bash
# Analyze the contract using slither
slither 0x7F42440C --json > slither_report.json

# Perform dynamic analysis using mythril
mythril 0x7F42440C --json > mythril_report.json

# Perform fuzz testing using echidna
echidna 0x7F42440C --json > echidna_report.json

# Manually review the contract code and analysis reports
# ...

# Verify the contract's functionality using foundry
foundry verify 0x7F42440C
```
Note: Replace `0x7F42440C` with the actual contract address being audited.

_Distilled 2026-07-07T09:50:13Z from real SKILLFORGE memory._
