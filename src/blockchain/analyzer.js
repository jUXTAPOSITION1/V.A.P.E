/**
 * Blockchain Analyzer Module
 * Forensics and on-chain activity analysis for Base blockchain
 * 
 * Responsibilities:
 * - Track token flows across Base
 * - Identify suspicious transaction patterns
 * - Analyze smart contract interactions
 * - Monitor liquidity pools and trading anomalies
 */

import logger from '../config/logger.js';
import { ethers } from 'ethers';

class BlockchainAnalyzer {
  constructor(provider) {
    this.provider = provider;
    this.name = 'BlockchainAnalyzer';
    this.networkState = null;
    this.transactionCache = new Map();
    this.watchedAddresses = new Set();
    
    logger.info('BlockchainAnalyzer initialized');
  }

  /**
   * Get current network state and metrics
   */
  async getNetworkState() {
    try {
      const blockNumber = await this.provider.getBlockNumber();
      const block = await this.provider.getBlock(blockNumber);
      const gasPrice = await this.provider.getGasPrice();
      
      this.networkState = {
        blockNumber,
        blockTimestamp: block.timestamp,
        gasPrice: ethers.formatUnits(gasPrice, 'gwei'),
        blockTime: block.timestamp,
        minedAt: new Date(block.timestamp * 1000),
      };
      
      logger.info('Network state updated:', this.networkState);
      return this.networkState;
    } catch (error) {
      logger.error('Failed to get network state:', error.message);
      throw error;
    }
  }

  /**
   * Analyze recent blockchain activity for anomalies
   */
  async analyzeRecentActivity(blockRange = 10) {
    try {
      const currentBlock = await this.provider.getBlockNumber();
      const startBlock = Math.max(currentBlock - blockRange, 0);
      
      logger.info(`Analyzing blocks ${startBlock} to ${currentBlock}`);
      
      const analysis = {
        blockRange: { start: startBlock, end: currentBlock },
        totalTransactions: 0,
        suspiciousPatterns: [],
        anomalies: [],
        largeTransfers: [],
        contractInteractions: [],
        timestamp: new Date(),
      };
      
      // Analyze each block in range
      for (let i = startBlock; i <= currentBlock; i++) {
        const block = await this.provider.getBlock(i);
        analysis.totalTransactions += block.transactions.length;
        
        // Fetch transaction details
        for (const txHash of block.transactions) {
          const tx = await this.provider.getTransaction(txHash);
          const receipt = await this.provider.getTransactionReceipt(txHash);
          
          // Analyze individual transaction
          await this.analyzeTransaction(tx, receipt, analysis);
        }
      }
      
      logger.info(`Analysis complete: ${analysis.totalTransactions} transactions reviewed`);
      return analysis;
    } catch (error) {
      logger.error('Failed to analyze recent activity:', error.message);
      return {
        blockRange: {},
        totalTransactions: 0,
        suspiciousPatterns: [],
        anomalies: [],
        largeTransfers: [],
        contractInteractions: [],
        error: error.message,
      };
    }
  }

  /**
   * Analyze individual transaction for suspicious patterns
   */
  async analyzeTransaction(tx, receipt, analysis) {
    try {
      // Check for large value transfers
      if (tx.value && ethers.toNumber(tx.value) > 0) {
        const valueInEth = ethers.formatEther(tx.value);
        
        // Flag large transfers (> 100 ETH equivalent)
        if (ethers.toNumber(tx.value) > ethers.parseEther('100')) {
          analysis.largeTransfers.push({
            hash: tx.hash,
            from: tx.from,
            to: tx.to,
            value: valueInEth,
            gasPrice: ethers.formatUnits(tx.gasPrice, 'gwei'),
            severity: 'medium',
          });
        }
      }
      
      // Check for contract interactions
      if (tx.to && tx.data && tx.data !== '0x') {
        analysis.contractInteractions.push({
          hash: tx.hash,
          from: tx.from,
          to: tx.to,
          dataLength: tx.data.length,
          gasUsed: receipt?.gasUsed?.toString(),
        });
      }
      
      // Check for failed transactions with high gas spent
      if (receipt && !receipt.status) {
        analysis.anomalies.push({
          type: 'failed_transaction',
          hash: tx.hash,
          reason: 'Transaction reverted',
          severity: 'low',
          gasWasted: ethers.formatEther(receipt.gasUsed * tx.gasPrice),
        });
      }
      
      // Check for suspicious patterns (rapid nonce increment, etc.)
      await this.detectSuspiciousPatterns(tx, analysis);
      
    } catch (error) {
      logger.debug(`Error analyzing transaction ${tx?.hash}:`, error.message);
    }
  }

  /**
   * Detect suspicious transaction patterns
   */
  async detectSuspiciousPatterns(tx, analysis) {
    // Pattern 1: Flash loan-like behavior (large value in, large value out in same block)
    if (tx.value && ethers.toNumber(tx.value) > ethers.parseEther('1000')) {
      analysis.suspiciousPatterns.push({
        type: 'high_value_transfer',
        tx: tx.hash,
        from: tx.from,
        to: tx.to,
        amount: ethers.formatEther(tx.value),
        severity: 'medium',
      });
    }
    
    // Pattern 2: Interaction with known suspicious addresses (extensible list)
    const suspiciousAddresses = this.getSuspiciousAddressList();
    if (suspiciousAddresses.has(tx.to?.toLowerCase())) {
      analysis.suspiciousPatterns.push({
        type: 'suspicious_address_interaction',
        tx: tx.hash,
        from: tx.from,
        to: tx.to,
        severity: 'high',
      });
    }
    
    // Pattern 3: Zero-to-code address interaction (contract creation)
    if (tx.to === null || tx.to === '0x' || tx.to === '0x0000000000000000000000000000000000000000') {
      analysis.suspiciousPatterns.push({
        type: 'contract_creation',
        tx: tx.hash,
        from: tx.from,
        data_length: tx.data?.length || 0,
        severity: 'low',
      });
    }
  }

  /**
   * Get list of known suspicious addresses
   * In production, this would connect to threat intelligence APIs
   */
  getSuspiciousAddressList() {
    const suspiciousAddresses = new Set([
      // Placeholder: Known phishing contracts, exploiters, etc.
      // Example format: '0x...' (lowercase)
    ]);
    return suspiciousAddresses;
  }

  /**
   * Track a specific address for continuous monitoring
   */
  watchAddress(address) {
    try {
      const normalizedAddress = ethers.getAddress(address);
      this.watchedAddresses.add(normalizedAddress);
      logger.info(`Now watching address: ${normalizedAddress}`);
      return true;
    } catch (error) {
      logger.error(`Invalid address to watch: ${error.message}`);
      return false;
    }
  }

  /**
   * Get balance of an address
   */
  async getAddressBalance(address) {
    try {
      const balance = await this.provider.getBalance(address);
      return {
        address,
        balance: ethers.formatEther(balance),
        balanceWei: balance.toString(),
      };
    } catch (error) {
      logger.error(`Failed to get balance for ${address}:`, error.message);
      throw error;
    }
  }

  /**
   * Get transaction history for an address
   */
  async getAddressTransactionHistory(address, blockRange = 1000) {
    try {
      const currentBlock = await this.provider.getBlockNumber();
      const startBlock = Math.max(currentBlock - blockRange, 0);
      
      const filter = {
        address: address,
        fromBlock: startBlock,
        toBlock: currentBlock,
      };
      
      const logs = await this.provider.getLogs(filter);
      
      logger.info(`Found ${logs.length} logs for address ${address}`);
      
      return {
        address,
        blockRange: { start: startBlock, end: currentBlock },
        logCount: logs.length,
        logs: logs.slice(0, 100), // Return first 100 logs
      };
    } catch (error) {
      logger.error(`Failed to get transaction history for ${address}:`, error.message);
      return {
        address,
        error: error.message,
        logs: [],
      };
    }
  }

  /**
   * Analyze a specific smart contract
   */
  async analyzeSmartContract(contractAddress) {
    try {
      // Get contract code
      const code = await this.provider.getCode(contractAddress);
      const codeSize = code.length;
      
      // Get creation details
      const creationData = await this.getContractCreation(contractAddress);
      
      const analysis = {
        address: contractAddress,
        codeSize: (codeSize - 2) / 2, // Remove '0x' and convert hex chars to bytes
        hasCode: codeSize !== '0x',
        isContract: codeSize !== '0x',
        createdAt: creationData?.blockNumber,
        creator: creationData?.from,
      };
      
      logger.info(`Contract analysis for ${contractAddress}:`, analysis);
      return analysis;
    } catch (error) {
      logger.error(`Failed to analyze contract ${contractAddress}:`, error.message);
      throw error;
    }
  }

  /**
   * Get contract creation information
   */
  async getContractCreation(contractAddress) {
    try {
      // This is a simplified version - in production, you'd query indexed data
      const balance = await this.provider.getBalance(contractAddress);
      
      return {
        address: contractAddress,
        balance: ethers.formatEther(balance),
      };
    } catch (error) {
      logger.debug(`Could not get creation info for ${contractAddress}`);
      return null;
    }
  }

  /**
   * Monitor token transfer events
   */
  async monitorTokenTransfers(tokenAddress, blockRange = 10) {
    try {
      const currentBlock = await this.provider.getBlockNumber();
      const startBlock = Math.max(currentBlock - blockRange, 0);
      
      // ERC20 Transfer event signature
      const transferTopic = '0xddf252ad1be2c89b69c2b068fc378daf4362f72c8e8a27dcbf20f27455c1a7d1';
      
      const logs = await this.provider.getLogs({
        address: tokenAddress,
        topics: [transferTopic],
        fromBlock: startBlock,
        toBlock: currentBlock,
      });
      
      const transfers = logs.map(log => ({
        transactionHash: log.transactionHash,
        from: '0x' + log.topics[1].slice(26),
        to: '0x' + log.topics[2].slice(26),
        blockNumber: log.blockNumber,
      }));
      
      logger.info(`Found ${transfers.length} token transfers`);
      return transfers;
    } catch (error) {
      logger.error(`Failed to monitor token transfers for ${tokenAddress}:`, error.message);
      return [];
    }
  }

  /**
   * Get gas price trends
   */
  async getGasPriceTrends(blockSamples = 5) {
    try {
      const currentBlock = await this.provider.getBlockNumber();
      const gasPrices = [];
      
      for (let i = 0; i < blockSamples; i++) {
        const blockNum = currentBlock - (blockSamples - 1 - i);
        const block = await this.provider.getBlock(blockNum);
        
        // Note: Base doesn't use traditional gas price, but we can still track it
        gasPrices.push({
          blockNumber: blockNum,
          baseFee: block.baseFeePerGas ? ethers.formatUnits(block.baseFeePerGas, 'gwei') : null,
        });
      }
      
      return {
        samples: blockSamples,
        gasPrices,
        timestamp: new Date(),
      };
    } catch (error) {
      logger.error('Failed to get gas price trends:', error.message);
      return { samples: 0, gasPrices: [], error: error.message };
    }
  }

  /**
   * Close connections (cleanup)
   */
  async close() {
    logger.info('BlockchainAnalyzer closing connections');
    this.transactionCache.clear();
    this.watchedAddresses.clear();
  }
}

export default BlockchainAnalyzer;
