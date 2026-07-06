### DeFi Protocol Security Audit Playbook
#### When to use:
This playbook is designed to be used when performing a security audit on DeFi protocols, particularly those built on the Base chain. It is essential to use this playbook when:
* A new protocol is being deployed
* An existing protocol is being updated
* A security incident has occurred

#### Step-by-Step Procedure:
1. **Gather Information**: Collect data on the protocol's TVL, dominance, and concentration risk using tools like `market_data` and `token_safety`.
2. **Identify Potential Vulnerabilities**: Use tools like `slither`, `mythril`, and `echidna` to identify potential vulnerabilities in the protocol's smart contracts.
3. **Analyze Security Incidents**: Review the `hack_feed` to identify repeatable attack patterns and defensive takeaways for holders and protocols.
4. **Assess Concentration Risk**: Evaluate the concentration risk of the protocol using data from `base_rpc` and `contract_recon`.
5. **Implement Robust Security Measures**: Based on the findings, implement robust security measures such as multi-sig wallets and regular smart contract audits using tools like `foundry` and `garak`.
6. **Monitor and Update**: Continuously monitor the protocol's security and update the playbook as needed to ensure the protocol remains secure.

#### Quality Gates:
* All smart contracts must be audited using at least two different tools (e.g., `slither` and `mythril`)
* All potential vulnerabilities must be addressed and fixed before deployment
* The protocol's concentration risk must be evaluated and mitigated

#### Limitations:
* This playbook is specific to DeFi protocols built on the Base chain and may not be applicable to other blockchain platforms
* The playbook relies on the accuracy and completeness of the data collected from various tools and sources
* The playbook is not a substitute for human judgment and expertise in security auditing and protocol development

#### Tools Used:
* `slither`
* `mythril`
* `echidna`
* `foundry`
* `garak`
* `market_data`
* `token_safety`
* `base_rpc`
* `contract_recon`
* `hack_feed`

_Distilled 2026-07-05T09:12:01Z from real SKILLFORGE memory._
