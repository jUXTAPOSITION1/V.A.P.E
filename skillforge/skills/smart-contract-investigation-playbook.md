### Smart Contract Investigation Playbook
#### When to Use
This playbook is used when investigating smart contracts for potential security vulnerabilities or anomalies. It is particularly useful when dealing with newly deployed contracts or those that have been flagged for review.

#### Step-by-Step Procedure
1. **Gather Contract Information**: Collect the contract address and ABI (if available) from sources like Etherscan, BscScan, or the project's official documentation.
2. **Run Static Analysis Tools**:
   - Use `slither` to analyze the contract for potential security vulnerabilities and code quality issues.
   - Utilize `mythril` to identify vulnerabilities and generate a report.
   - Employ `echidna` to fuzz test the contract and uncover potential issues.
3. **Dynamic Analysis and Simulation**:
   - Use `foundry` to deploy and test the contract in a controlled environment.
   - Utilize `garak` to simulate various scenarios and identify potential weaknesses.
4. **Investigation and Due Diligence**:
   - Run `contract_recon` to gather information about the contract's interactions, transactions, and related entities.
   - Use `token_safety` to assess the contract's tokenomics and potential risks.
5. **Sentiment Analysis and Market Pulse**:
   - Monitor `fear_greed` to gauge market sentiment and potential impact on the contract's performance.
   - Utilize `market_data` to stay informed about market trends and potential correlations with the contract's behavior.
6. **Review and Verification**:
   - Review the results from the previous steps and verify the findings.
   - Use `base_rpc` to fetch additional data and confirm the contract's status.
7. **Reporting and Documentation**:
   - Document all findings, including any potential vulnerabilities or anomalies.
   - Use `hack_feed` to report the findings and track the contract's performance over time.

#### Quality Gates
- All contracts must pass static analysis checks with no critical vulnerabilities.
- Dynamic analysis and simulation must not reveal any significant weaknesses.
- Investigation and due diligence must confirm the contract's legitimacy and safety.
- Sentiment analysis and market pulse must indicate a stable and favorable market environment.

#### Limitations
- This playbook is not foolproof and may not detect all potential vulnerabilities or anomalies.
- The effectiveness of the playbook depends on the quality of the tools and data used.
- Market sentiment and trends can be unpredictable and may impact the contract's performance despite thorough investigation and analysis.

#### Example Use Case
Investigating a newly deployed DeFi protocol contract using this playbook can help identify potential security vulnerabilities, assess market sentiment, and inform investment decisions. By following this structured approach, investigators can ensure a thorough and comprehensive evaluation of the contract's safety and legitimacy.

_Distilled 2026-07-10T09:42:38Z from real SKILLFORGE memory._
