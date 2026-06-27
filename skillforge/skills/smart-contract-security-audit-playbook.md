### Smart Contract Security Audit Playbook
#### When to use:
This playbook is designed to be used when performing a security audit on a smart contract. It leverages a suite of tools including `slither`, `aderyn`, `mythril`, `echidna`, and `foundry` to identify potential vulnerabilities.

#### Step-by-Step Procedure:
1. **Initialize the environment**: Ensure that all necessary tools are installed and up-to-date. This includes `slither`, `aderyn`, `mythril`, `echidna`, and `foundry`.
2. **Run static analysis tools**:
   - Use `slither` to analyze the contract for potential security vulnerabilities: `slither <contract_path> --json <output_file>`
   - Use `aderyn` to identify potential reentrancy attacks: `aderyn <contract_path> --json <output_file>`
   - Use `mythril` to detect potential security issues: `mythril <contract_path> --json <output_file>`
3. **Run dynamic analysis tools**:
   - Use `echidna` to fuzz test the contract: `echidna <contract_path> --config <config_file>`
   - Use `foundry` to test the contract: `forge test --match-path <contract_path> --json <output_file>`
4. **Analyze results**: Review the output from each tool to identify potential security vulnerabilities.
5. **Verify findings**: Use `base_rpc` and `market_data` to verify the findings and gather additional information about the contract.
6. **Document findings**: Document all findings, including potential vulnerabilities and recommendations for remediation.

#### Quality Gates:
- All tools must be run successfully without errors.
- All potential vulnerabilities must be reviewed and documented.
- Recommendations for remediation must be provided for all identified vulnerabilities.

#### Limitations:
- This playbook is designed for use with smart contracts written in Solidity.
- The effectiveness of this playbook depends on the quality of the tools used and the expertise of the person performing the audit.
- This playbook may not identify all potential security vulnerabilities, and additional testing and analysis may be necessary. 

#### Tools Used:
- `slither`: A static analysis tool for smart contracts.
- `aderyn`: A tool for identifying potential reentrancy attacks.
- `mythril`: A security analysis tool for smart contracts.
- `echidna`: A fuzz testing tool for smart contracts.
- `foundry`: A testing framework for smart contracts.
- `base_rpc`: A tool for interacting with the blockchain.
- `market_data`: A tool for gathering market data.

_Distilled 2026-06-27T08:42:07Z from real SKILLFORGE memory._
