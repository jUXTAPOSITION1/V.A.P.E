# VAPE SKILLFORGE Build — DeFiLlama TVL and Price Data Scraper

**Justification:** The signal "market_data (recon) is BROKEN: Free crypto market data via CoinGecko + DeFiLlama: price/chg/vol/mcap, dominance, chain TVL" indicates that the current market data tool is broken and needs to be replaced or fixed. This is a high-priority issue as it affects VAPE's ability to gather important market data. By building a DeFiLlama TVL and price data scraper, VAPE can restore its market data capabilities and improve its on-chain investigation and forensics capabilities.

**Spec:** The DeFiLlama TVL and price data scraper will be a Python script that uses the DeFiLlama API to fetch TVL and price data for various chains and protocols. The script will take no inputs and will output the fetched data in a JSON format. The script will be built using the Python stdlib and will be integrated into the VAPE's tools registry. The approach to building this script will involve researching the DeFiLlama API, writing the API calls to fetch the required data, and parsing the response data into a usable format. The script will be designed to be flexible and scalable, allowing for easy addition of new chains and protocols in the future. The output data will be used to update VAPE's market data capabilities, enabling better on-chain investigation and forensics.

## Files generated
- `agents/defillama_scraper.py`

PR opened: https://github.com/jUXTAPOSITION1/V.A.P.E/pull/249
