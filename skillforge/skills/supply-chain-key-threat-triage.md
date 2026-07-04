### Supply-Chain-Key-Threat-Triage
#### When to use:
Use this playbook when identifying potential supply-chain key threats in the DeFi ecosystem, particularly after a bounty cycle analysis or when encountering incidents involving key compromises or npm supply-chain campaigns.

#### Step-by-Step Procedure:
1. **Gather Intelligence**: Utilize `market_data` and `hack_feed` tools to gather information on recent exploits, especially those related to supply-chain key threats.
2. **Analyze Incidents**: Review incidents reported by `hack_feed` and analyze them for patterns or common vulnerabilities, such as front-end vulnerabilities or key compromises.
3. **Corroborate Information**: Cross-check findings with external sources like DeFiLlama, Halborn, or SlowMist to validate the incidents and identify potential supply-chain key threats.
4. **Assess Risk**: Evaluate the risk posture based on the gathered intelligence, considering factors such as the number of incidents, affected protocols, and potential impact on the Base chain.
5. **Implement Mitigations**: Based on the assessment, implement mitigations such as prioritizing front-end security, implementing robust validation mechanisms, and monitoring for suspicious activity.
6. **Document Findings**: Document the findings and mitigations in a report, such as `reports/bounty_report_20260701_221813.md`, and broadcast the written report.

#### Quality Gates:
- Verify that all tools used, such as `market_data` and `hack_feed`, are functioning correctly before proceeding with the analysis.
- Ensure that the intelligence gathered is up-to-date and relevant to the current bounty cycle.
- Validate the findings by cross-checking with external sources.

#### Limitations:
- This playbook relies on the accuracy and timeliness of the intelligence gathered from `market_data` and `hack_feed`.
- The effectiveness of the mitigations implemented depends on the severity of the identified supply-chain key threats and the protocols' ability to respond to them.
- The playbook may not cover all possible supply-chain key threats, and continuous monitoring and analysis are necessary to stay ahead of emerging threats.

_Distilled 2026-07-04T08:43:18Z from real SKILLFORGE memory._
