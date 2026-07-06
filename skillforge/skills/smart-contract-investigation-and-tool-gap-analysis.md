### Smart Contract Investigation and Tool Gap Analysis
#### When to use:
This playbook is used when investigating smart contracts for potential security vulnerabilities and identifying gaps in the current toolkit.

#### Step-by-Step Procedure:
1. **Run `slither` and `mythril` to analyze the smart contract for security vulnerabilities**:
   - Use `slither` to detect potential security issues such as reentrancy, uninitialized variables, and incorrect usage of modifiers.
   - Use `mythril` to identify potential security vulnerabilities such as buffer overflows, use of uninitialized variables, and incorrect usage of cryptographic functions.
2. **Use `echidna` and `foundry` for fuzzing (if available)**:
   - If `echidna` and `foundry` are available, use them to perform fuzzing on the smart contract to identify potential security vulnerabilities.
   - If `echidna` and `foundry` are not available, consider alternative fuzzing tools or develop a plan to repair or replace them.
3. **Analyze the contract's permission structure and identify potential vulnerabilities**:
   - Use `contract_recon` to analyze the contract's permission structure and identify potential vulnerabilities such as access control issues.
4. **Monitor the security incidents feed for recent incidents**:
   - Use `hack_feed` to monitor the security incidents feed for recent incidents and identify potential security threats.
5. **Perform a tool gap analysis**:
   - Use `toolcheck` to perform a tool gap analysis and identify any gaps in the current toolkit.
   - Consider developing or acquiring alternative tools to address any gaps identified.

#### Quality Gates:
- The investigation should identify potential security vulnerabilities in the smart contract.
- The tool gap analysis should identify any gaps in the current toolkit.
- Alternative tools or plans to repair/replace broken tools should be developed.

#### Limitations:
- The availability of `echidna` and `foundry` may impact the effectiveness of the fuzzing step.
- The quality of the investigation and tool gap analysis is dependent on the quality of the tools used and the expertise of the investigator.
- The playbook may not identify all potential security vulnerabilities or gaps in the current toolkit.

_Distilled 2026-07-06T10:45:48Z from real SKILLFORGE memory._
