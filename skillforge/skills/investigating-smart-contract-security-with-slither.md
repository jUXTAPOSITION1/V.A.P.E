### Investigating Smart Contract Security with Slither and Echidna
#### When to use:
This playbook is used when investigating the security of a smart contract, particularly when a potential vulnerability has been identified.

#### Step-by-Step Procedure:
1. **Identify the contract**: Determine the smart contract address and chain ID that needs to be investigated.
2. **Run Slither**: Use Slither to analyze the contract for potential vulnerabilities.
   ```bash
   slither <contract_address> --chain-id <chain_id>
   ```
3. **Run Echidna**: Use Echidna to fuzz test the contract and identify potential vulnerabilities.
   ```bash
   echidna --contract <contract_address> --chain-id <chain_id>
   ```
4. **Analyze results**: Review the results from Slither and Echidna to identify potential vulnerabilities.
5. **Investigate further**: Use tools like `agents/investigate.py` to investigate the contract and its deployer.
   ```bash
   python agents/investigate.py --target <contract_address> --chain <chain_id>
   ```
6. **Verify findings**: Verify the findings using other tools and techniques, such as manual code review.

#### Quality Gates:
* The contract must be identified and verified before investigation.
* The investigation must be thorough and include multiple tools and techniques.
* The findings must be verified and documented.

#### Limitations:
* This playbook is limited to investigating smart contract security and may not identify all potential vulnerabilities.
* The effectiveness of this playbook depends on the quality of the tools and techniques used.

#### Example Use Case:
This playbook can be used to investigate a smart contract that has been identified as potentially vulnerable to a known exploit. By following the steps outlined in this playbook, an investigator can identify potential vulnerabilities and verify the findings using multiple tools and techniques.

_Distilled 2026-07-12T08:23:46Z from real SKILLFORGE memory._
