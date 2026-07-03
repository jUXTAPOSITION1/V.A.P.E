### DeFi Protocol Anomaly Detection and Analysis
#### When to use:
This playbook is used to identify potential anomalies, exploit signals, TVL outflows, and threats in DeFi protocols, and to provide actionable recommendations for further investigation.

#### Step-by-Step Procedure:
1. **Gather Data**: Use `market_data` and `base_rpc` to collect live market and chain data.
2. **Run Anomaly Detection**: Utilize `agents/run.py` to analyze the collected data and identify potential anomalies, exploit signals, TVL outflows, and threats.
3. **Investigate Anomalies**: Investigate the identified anomalies, such as Morpho Blue's significant 1-day gain, Aerodrome V1's high 1-day gain, and AFI Protocol's negligible 1-day change.
4. **Assess TVL Outflows**: Evaluate the cause of TVL decreases, such as Grove Finance's 1-day TVL decrease.
5. **Monitor Protocols**: Keep a close eye on protocols with potential exploits or liquidity surges, such as Morpho Blue and Aerodrome V1.
6. **Corroborate Findings**: Corroborate findings against external sources, such as DeFiLlama and The Defiant Q2 recap.

#### Quality Gates:
* **Data Quality**: Ensure that the collected data is accurate and up-to-date.
* **Anomaly Detection**: Verify that the anomaly detection tool is functioning correctly and identifying relevant anomalies.
* **Investigation**: Ensure that investigations are thorough and provide actionable recommendations.

#### Limitations:
* **Data Availability**: The playbook is limited by the availability of live market and chain data.
* **Anomaly Detection Tool**: The playbook is dependent on the accuracy and effectiveness of the anomaly detection tool.
* **Investigation**: The playbook requires thorough investigation and analysis to provide actionable recommendations.

#### Example Use Case:
The playbook can be used to identify potential anomalies in DeFi protocols, such as Morpho Blue's significant 1-day gain, and provide actionable recommendations for further investigation. For example, the investigation may reveal that the gain is due to a surge in liquidity, and the recommendation may be to monitor the protocol's TVL and on-chain activity closely.

_Distilled 2026-07-03T09:25:34Z from real SKILLFORGE memory._
