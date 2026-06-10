/**
 * Data Fetcher Module
 * Aggregates market data, liquidity metrics, and blockchain metrics
 * 
 * Responsibilities:
 * - Fetch DeFi market data
 * - Retrieve liquidity pool metrics
 * - Aggregate blockchain statistics
 * - Monitor TVL and trading volumes
 */

import axios from 'axios';
import logger from '../config/logger.js';
import { ethers } from 'ethers';

class DataFetcher {
  constructor(provider) {
    this.provider = provider;
    this.name = 'DataFetcher';
    
    // External API endpoints
    this.coingeckoApi = 'https://api.coingecko.com/api/v3';
    this.defilllamaApi = 'https://api.llama.fi';
    
    // Data cache
    this.cache = new Map();
    this.cacheExpiry = 5 * 60 * 1000; // 5 minutes
    
    // HTTP clients
    this.coingeckoClient = axios.create({
      baseURL: this.coingeckoApi,
      timeout: 10000,
    });
    
    this.defllamaClient = axios.create({
      baseURL: this.defilllamaApi,
      timeout: 10000,
    });
    
    logger.info('DataFetcher initialized');
  }

  /**
   * Get comprehensive market metrics
   */
  async getMarketMetrics() {
    try {
      logger.info('📊 Fetching market metrics...');
      
      const metrics = {
        timestamp: new Date(),
        ethereum: {},
        base: {},
        defi: {},
      };
      
      // Get Ethereum network metrics
      metrics.ethereum = await this.getEthereumMetrics();
      
      // Get Base chain metrics
      metrics.base = await this.getBaseMetrics();
      
      // Get DeFi metrics
      metrics.defi = await this.getDeFiMetrics();
      
      logger.info('✅ Market metrics fetched successfully');
      return metrics;
    } catch (error) {
      logger.error('Failed to fetch market metrics:', error.message);
      return {
        timestamp: new Date(),
        error: error.message,
      };
    }
  }

  /**
   * Get Ethereum network metrics
   */
  async getEthereumMetrics() {
    try {
      const cached = this.getFromCache('ethereum_metrics');
      if (cached) return cached;
      
      const metrics = {
        network: 'ethereum',
        blockHeight: await this.provider.getBlockNumber(),
        gasPrice: await this.getGasPrice(),
        ethPrice: await this.getTokenPrice('ethereum'),
      };
      
      this.setCache('ethereum_metrics', metrics);
      return metrics;
    } catch (error) {
      logger.debug('Failed to get Ethereum metrics:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get Base chain metrics
   */
  async getBaseMetrics() {
    try {
      const cached = this.getFromCache('base_metrics');
      if (cached) return cached;
      
      const metrics = {
        network: 'base',
        blockHeight: await this.provider.getBlockNumber(),
        activeAddresses: await this.estimateActiveAddresses(),
        topTokens: await this.getTopTokensOnBase(),
      };
      
      this.setCache('base_metrics', metrics);
      return metrics;
    } catch (error) {
      logger.debug('Failed to get Base metrics:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get DeFi metrics from DefiLlama
   */
  async getDeFiMetrics() {
    try {
      const cached = this.getFromCache('defi_metrics');
      if (cached) return cached;
      
      const metrics = {
        totalTVL: await this.getTotalTVL(),
        baseChainTVL: await this.getChainTVL('base'),
        topProtocols: await this.getTopProtocols(),
        liquidityPools: await this.getLiquidityPoolMetrics(),
      };
      
      this.setCache('defi_metrics', metrics);
      return metrics;
    } catch (error) {
      logger.debug('Failed to get DeFi metrics:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get current gas prices
   */
  async getGasPrice() {
    try {
      const gasPrice = await this.provider.getGasPrice();
      const gasPriceGwei = ethers.formatUnits(gasPrice, 'gwei');
      
      return {
        gasPrice: gasPriceGwei,
        unit: 'gwei',
      };
    } catch (error) {
      logger.debug('Failed to get gas price:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get token price from CoinGecko
   */
  async getTokenPrice(tokenId) {
    try {
      const cached = this.getFromCache(`price_${tokenId}`);
      if (cached) return cached;
      
      const response = await this.coingeckoClient.get('/simple/price', {
        params: {
          ids: tokenId,
          vs_currencies: 'usd',
          include_market_cap: true,
          include_24hr_vol: true,
        },
      });
      
      const data = response.data[tokenId];
      
      const result = {
        token: tokenId,
        price: data.usd,
        marketCap: data.usd_market_cap,
        volume24h: data.usd_24h_vol,
        timestamp: new Date(),
      };
      
      this.setCache(`price_${tokenId}`, result);
      return result;
    } catch (error) {
      logger.debug(`Failed to get price for ${tokenId}:`, error.message);
      return { error: error.message };
    }
  }

  /**
   * Get total DeFi TVL
   */
  async getTotalTVL() {
    try {
      const cached = this.getFromCache('total_tvl');
      if (cached) return cached;
      
      const response = await this.defllamaClient.get('/tv');
      
      const result = {
        totalTVL: response.data,
        unit: 'USD',
        timestamp: new Date(),
      };
      
      this.setCache('total_tvl', result);
      return result;
    } catch (error) {
      logger.debug('Failed to get total TVL:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get TVL for a specific chain
   */
  async getChainTVL(chain) {
    try {
      const cached = this.getFromCache(`tvl_${chain}`);
      if (cached) return cached;
      
      const response = await this.defllamaClient.get(`/tvl/${chain}`);
      
      const result = {
        chain,
        tvl: response.data,
        unit: 'USD',
        timestamp: new Date(),
      };
      
      this.setCache(`tvl_${chain}`, result);
      return result;
    } catch (error) {
      logger.debug(`Failed to get TVL for ${chain}:`, error.message);
      return { error: error.message };
    }
  }

  /**
   * Get top DeFi protocols
   */
  async getTopProtocols(limit = 10) {
    try {
      const cached = this.getFromCache('top_protocols');
      if (cached) return cached;
      
      const response = await this.defllamaClient.get('/protocols');
      
      const topProtocols = response.data
        .sort((a, b) => (b.tvl || 0) - (a.tvl || 0))
        .slice(0, limit)
        .map(p => ({
          name: p.name,
          tvl: p.tvl,
          chain: p.chain,
          category: p.category,
        }));
      
      this.setCache('top_protocols', topProtocols);
      return topProtocols;
    } catch (error) {
      logger.debug('Failed to get top protocols:', error.message);
      return [];
    }
  }

  /**
   * Get liquidity pool metrics
   */
  async getLiquidityPoolMetrics() {
    try {
      const cached = this.getFromCache('liquidity_pools');
      if (cached) return cached;
      
      // This would integrate with pool data from various sources
      // Uniswap, Curve, Balancer, etc.
      
      const pools = {
        count: 0,
        totalLiquidity: 0,
        topPools: [],
        timestamp: new Date(),
      };
      
      this.setCache('liquidity_pools', pools);
      return pools;
    } catch (error) {
      logger.debug('Failed to get liquidity pool metrics:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get top tokens on Base chain
   */
  async getTopTokensOnBase(limit = 20) {
    try {
      const cached = this.getFromCache('top_tokens_base');
      if (cached) return cached;
      
      // In production, this would fetch from on-chain data or DEX aggregators
      const topTokens = [
        {
          address: '0x4200000000000000000000000000000000000006', // WETH
          symbol: 'WETH',
          name: 'Wrapped Ether',
          liquidity: 0,
        },
        {
          address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', // USDC
          symbol: 'USDC',
          name: 'USD Coin',
          liquidity: 0,
        },
      ];
      
      this.setCache('top_tokens_base', topTokens);
      return topTokens;
    } catch (error) {
      logger.debug('Failed to get top tokens on Base:', error.message);
      return [];
    }
  }

  /**
   * Estimate active addresses on Base (simplified)
   */
  async estimateActiveAddresses() {
    try {
      const currentBlock = await this.provider.getBlockNumber();
      const pastBlock = Math.max(currentBlock - 5760, 0); // ~24 hours
      
      return {
        estimated: true,
        blockRange: { current: currentBlock, past: pastBlock },
        note: 'Accurate count requires indexed blockchain data',
      };
    } catch (error) {
      logger.debug('Failed to estimate active addresses:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Monitor specific token metrics
   */
  async monitorToken(tokenAddress, tokenSymbol) {
    try {
      logger.info(`Monitoring token ${tokenSymbol} at ${tokenAddress}`);
      
      const monitoring = {
        token: tokenSymbol,
        address: tokenAddress,
        timestamp: new Date(),
        holders: await this.estimateTokenHolders(tokenAddress),
        transfers24h: await this.getTransfers24h(tokenAddress),
        price: await this.getTokenPrice(tokenSymbol.toLowerCase()),
      };
      
      return monitoring;
    } catch (error) {
      logger.error(`Failed to monitor token ${tokenSymbol}:`, error.message);
      return { error: error.message };
    }
  }

  /**
   * Estimate token holders (simplified)
   */
  async estimateTokenHolders(tokenAddress) {
    try {
      // In production, query transfer events and maintain holder set
      return {
        estimated: true,
        approximateCount: 0,
        note: 'Requires indexed transfer event data',
      };
    } catch (error) {
      logger.debug('Failed to estimate token holders:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get transfers in last 24 hours
   */
  async getTransfers24h(tokenAddress) {
    try {
      const currentBlock = await this.provider.getBlockNumber();
      const blockRange = 5760; // ~24 hours
      const startBlock = Math.max(currentBlock - blockRange, 0);
      
      // ERC20 Transfer event signature
      const transferTopic = '0xddf252ad1be2c89b69c2b068fc378daf4362f72c8e8a27dcbf20f27455c1a7d1';
      
      const logs = await this.provider.getLogs({
        address: tokenAddress,
        topics: [transferTopic],
        fromBlock: startBlock,
        toBlock: currentBlock,
      });
      
      return {
        transferCount: logs.length,
        blockRange: { start: startBlock, end: currentBlock },
        period: '24h',
      };
    } catch (error) {
      logger.debug('Failed to get transfers:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get DeFi yield opportunities
   */
  async getYieldOpportunities() {
    try {
      const cached = this.getFromCache('yield_opportunities');
      if (cached) return cached;
      
      const opportunities = {
        staking: [],
        lending: [],
        liquidity_mining: [],
        timestamp: new Date(),
      };
      
      // In production, integrate with yield aggregators
      // Yearn, Curve, Aave, Compound, etc.
      
      this.setCache('yield_opportunities', opportunities);
      return opportunities;
    } catch (error) {
      logger.debug('Failed to get yield opportunities:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Cache utility - get from cache
   */
  getFromCache(key) {
    const cached = this.cache.get(key);
    
    if (cached) {
      if (Date.now() - cached.timestamp < this.cacheExpiry) {
        return cached.data;
      } else {
        this.cache.delete(key);
      }
    }
    
    return null;
  }

  /**
   * Cache utility - set in cache
   */
  setCache(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  /**
   * Clear expired cache entries
   */
  clearExpiredCache() {
    const now = Date.now();
    let cleared = 0;
    
    for (const [key, value] of this.cache) {
      if (now - value.timestamp > this.cacheExpiry) {
        this.cache.delete(key);
        cleared++;
      }
    }
    
    if (cleared > 0) {
      logger.debug(`Cleared ${cleared} expired cache entries`);
    }
  }

  /**
   * Get data fetcher status
   */
  getStatus() {
    return {
      name: this.name,
      cacheSize: this.cache.size,
      cacheExpiry: this.cacheExpiry,
      externalApis: {
        coingecko: this.coingeckoApi,
        defillama: this.defilllamaApi,
      },
    };
  }

  /**
   * Close connections
   */
  async close() {
    logger.info('DataFetcher closing');
    this.cache.clear();
  }
}

export default DataFetcher;
