### Smart Contract Security Audit Playbook
#### When to Use
This playbook is used to perform a comprehensive security audit of smart contracts using a combination of static analysis and dynamic testing tools.

#### Step-by-Step Procedure
1. **Initialize the project**: Create a new directory for the project and navigate to it in the terminal.
2. **Install required tools**:
   * `slither`: `pip install slither`
   * `aderyn`: Follow the installation instructions on the [Adeyrn GitHub page](https://github.com/Cyfrin/aderyn)
   * `mythril`: `pip install mythril`
   * `echidna`: `pip install echidna`
   * `foundry`: Follow the installation instructions on the [Foundry GitHub page](https://github.com/foundry-rs/foundry)
3. **Clone the smart contract repository**: Clone the repository containing the smart contract code using `git clone`.
4. **Run static analysis tools**:
   * `slither`: `slither . --json output.json`
   * `aderyn`: `aderyn analyze .`
   * `mythril`: `myth analyze .`
5. **Run dynamic testing tools**:
   * `echidna`: `echidna test .`
   * `foundry`: `forge test`
6. **Analyze results**: Review the output from each tool to identify potential security vulnerabilities.
7. **Verify findings**: Use tools like `base_rpc` and `market_data` to verify the findings and gather more information about the smart contract.

#### Quality Gates
* All tools must be installed and functioning correctly before proceeding with the audit.
* The smart contract code must be cloned and available in the project directory.
* The output from each tool must be reviewed and analyzed to identify potential security vulnerabilities.

#### Limitations
* This playbook only covers a subset of available tools and may not identify all potential security vulnerabilities.
* The effectiveness of this playbook depends on the quality of the tools used and the expertise of the person performing the audit.
* This playbook may require modifications to work with different smart contract languages or frameworks.

#### Example Use Case
This playbook can be used to perform a security audit of a smart contract written in Solidity. The auditor would clone the repository containing the smart contract code, install and run the required tools, and then analyze the output to identify potential security vulnerabilities.

```markdown
# Example Command
slither ./contracts --json output.json
aderyn analyze ./contracts
mythril analyze ./contracts
echidna test ./contracts
forge test
```

_Distilled 2026-06-28T09:17:26Z from real SKILLFORGE memory._
