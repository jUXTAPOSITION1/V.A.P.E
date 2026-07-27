# VAPE SKILLFORGE Build — LayerZero OFT Bridge Exploit Detector

**Justification:** The Kelp exploit ($293,000,000) on Ethereum and Arbitrum, which involved a LayerZero OFT bridge exploit, highlights the need for a detector that can identify similar vulnerabilities. As stated in the bounty radar opportunities, "Kelp (exploit $293,000,000) (defillama-hack, fit 90, $293,000,000): LayerZero OFT bridge exploit on Ethereum,Arbitrum." This signal motivates the build of a detector that can help prevent or respond to similar exploits in the future.

**Spec:** The LayerZero OFT Bridge Exploit Detector would be a Python script that analyzes smart contract interactions on Ethereum and Arbitrum to identify potential LayerZero OFT bridge exploits. It would take as input a list of contract addresses and transaction hashes, and output a report indicating whether any suspicious activity was detected. The script would utilize the Python stdlib and potentially integrate with existing VAPE tools, such as the arbitrum transaction tracer. The approach to building this detector would involve researching the specifics of the Kelp exploit, identifying key indicators of similar exploits, and implementing a detection algorithm that can identify these indicators in real-time. The detector would be designed to be extensible, allowing for easy integration with other VAPE tools and adaptability to new exploit techniques.

## Files generated
- `layerzero_oft_bridge_exploit_detector.py`

PR opened: https://github.com/jUXTAPOSITION1/V.A.P.E/pull/330
