### Smart Contract Security Audit Playbook
#### When to Use
This playbook is designed to be used when performing a security audit on a smart contract. It leverages the power of multiple verified tools to ensure the contract is thoroughly vetted for potential vulnerabilities.

#### Step-by-Step Procedure
1. **Initialize the Environment**:
   - Ensure all necessary tools are installed and up-to-date. This includes `slither`, `aderyn`, `mythril`, `echidna`, and `foundry`.
   - Verify the versions of these tools to ensure they are the latest releases.

2. **Static Analysis with Slither**:
   - Navigate to the directory containing the smart contract code.
   - Run `slither .` to perform static analysis. This will help identify potential issues such as reentrancy vulnerabilities, uninitialized variables, and more.

3. **Static Analysis with Aderyn**:
   - Run `aderyn analyze .` to perform additional static analysis. Aderyn can detect different types of vulnerabilities and provide insights into the contract's security.

4. **Fuzz Testing with Echidna**:
   - Prepare a test suite for the smart contract using Echidna.
   - Run `echidna test .` to perform fuzz testing. This step is crucial for identifying potential issues that might not be caught by static analysis.

5. **Dynamic Analysis with Mythril**:
   - Run `mythril analyze .` to perform dynamic analysis. Mythril can simulate attacks on the contract and help identify vulnerabilities that might be missed by static tools.

6. **Compile and Deploy with Foundry**:
   - Use Foundry to compile and deploy the smart contract to a test network.
   - Perform functional testing to ensure the contract behaves as expected.

7. **Manual Review**:
   - Perform a manual review of the contract code, focusing on areas that automated tools might miss, such as the logic of complex functions or the handling of edge cases.

8. **Iterate and Refine**:
   - Based on the findings from the above steps, refine the contract code to address any identified vulnerabilities or issues.
   - Repeat the analysis process until all vulnerabilities have been addressed.

#### Quality Gates
- All identified vulnerabilities must be addressed before the contract is considered secure.
- The contract must pass all static and dynamic analyses without any critical issues.
- Manual review must confirm that the contract logic is sound and secure.

#### Limitations
- This playbook focuses on smart contract security and does not cover the security of the surrounding infrastructure or applications.
- The effectiveness of this playbook depends on the quality of the tools used and the thoroughness of the manual review.
- New vulnerabilities or attack vectors might not be covered by the tools used in this playbook, highlighting the need for continuous monitoring and updating of security practices.

_Distilled 2026-06-30T09:47:25Z from real SKILLFORGE memory._
