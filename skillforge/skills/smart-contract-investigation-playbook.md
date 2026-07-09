### Smart Contract Investigation Playbook
#### When to use:
This playbook is used when investigating a smart contract to determine its legitimacy and potential risks. It is particularly useful when dealing with newly deployed contracts or those with suspicious activity.

#### Step-by-Step Procedure:
1. **Gather Contract Information**: Use `contract_recon` to gather basic information about the contract, such as its address, name, and symbol.
2. **Run Security Sweep**: Utilize `security_sweep.py` to identify any potential security risks associated with the contract, such as recent incidents or vulnerabilities.
3. **Analyze Sentiment**: Employ `sentiment_sweep.py` to assess the market sentiment surrounding the contract, including fear and greed indices.
4. **Investigate On-Chain Activity**: Leverage `agents/investigate.py` to investigate the contract's on-chain activity, including its deployment history and interactions with other contracts.
5. **Check for Red Flags**: Use `token_safety` to check for red flags, such as suspicious tokenomics or potential rug pull indicators.
6. **Verify Team Identity and Audit**: Utilize `foundry` and `market_data` to verify the contract's team identity and check for any known audits or security assessments.
7. **Assess Virtuals Health**: Employ `virtuals_sweep.py` to assess the health of the contract's virtual assets, if applicable.

#### Quality Gates:
* Contract information gathering: Verify that the contract address, name, and symbol are correctly identified.
* Security sweep: Confirm that the security sweep report is up-to-date and accurately reflects the contract's security posture.
* Sentiment analysis: Validate that the sentiment analysis is based on recent and relevant data.
* On-chain activity investigation: Ensure that the investigation covers all relevant on-chain activity, including recent transactions and interactions.
* Red flag checking: Verify that all potential red flags are thoroughly investigated and addressed.
* Team identity and audit verification: Confirm that the contract's team identity is verified and that any known audits or security assessments are taken into account.
* Virtuals health assessment: Validate that the virtuals health assessment is accurate and up-to-date.

#### Limitations:
* This playbook relies on the accuracy and completeness of the data gathered from various tools and sources.
* The investigation may not uncover all potential risks or issues associated with the contract.
* The playbook's effectiveness depends on the investigator's expertise and judgment in interpreting the results of the various tools and analyses.

#### Tools Used:
* `contract_recon`
* `security_sweep.py`
* `sentiment_sweep.py`
* `agents/investigate.py`
* `token_safety`
* `foundry`
* `market_data`
* `virtuals_sweep.py`

_Distilled 2026-07-09T09:48:03Z from real SKILLFORGE memory._
