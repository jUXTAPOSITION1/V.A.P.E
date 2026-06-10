/**
 * Security Scanner Module
 * Smart contract vulnerability detection and security threat identification
 * 
 * Responsibilities:
 * - Scan contracts for common vulnerabilities
 * - Identify malicious patterns
 * - Monitor for known exploits
 * - Track suspicious addresses
 */

import logger from '../config/logger.js';
import { ethers } from 'ethers';

class SecurityScanner {
  constructor(provider) {
    this.provider = provider;
    this.name = 'SecurityScanner';
    
    // Watch lists
    this.knownMaliciousAddresses = new Set();
    this.suspiciousPatterns = [];
    this.vulnerabilitySignatures = new Map();
    
    // Threat cache
    this.threatCache = new Map();
    this.lastScanTime = null;
    
    this.initializeVulnerabilitySignatures();
    logger.info('SecurityScanner initialized');
  }

  /**
   * Initialize known vulnerability signatures and patterns
   */
  initializeVulnerabilitySignatures() {
    // Reentrancy vulnerability function signatures
    this.vulnerabilitySignatures.set('reentrancy', {
      patterns: [
        'call\\.value',
        'send\\(\\)',
        'transfer\\(\\)',
      ],
      severity: 'critical',
      description: 'Potential reentrancy vulnerability',
    });
    
    // Unchecked external calls
    this.vulnerabilitySignatures.set('unchecked_call', {
      patterns: [
        'low_level_call',
        'delegatecall',
      ],
      severity: 'high',
      description: 'Unchecked external call detected',
    });
    
    // Integer overflow/underflow (pre-Solidity 0.8)
    this.vulnerabilitySignatures.set('integer_overflow', {
      patterns: [
        'SafeMath',
        'checked_arithmetic',
      ],
      severity: 'high',
      description: 'Potential integer overflow/underflow',
    });
    
    // Access control issues
    this.vulnerabilitySignatures.set('access_control', {
      patterns: [
        'public.*dangerous',
        'msg.sender.*not.*checked',
      ],
      severity: 'high',
      description: 'Inadequate access control',
    });
    
    logger.info(`Initialized ${this.vulnerabilitySignatures.size} vulnerability signatures`);
  }

  /**
   * Initialize security watch lists from external sources
   */
  async initializeWatchLists() {
    try {
      logger.info('Initializing security watch lists...');
      
      // In production, these would be fetched from threat intelligence APIs:
      // - OpenZeppelin security reports
      // - Certora threat intelligence
      // - Internal honeypots and contracts
      
      // Example: Add known problematic contracts/addresses
      const knownExploiters = [
        // Placeholder for known exploiter addresses
      ];
      
      knownExploiters.forEach(addr => {
        try {
          this.knownMaliciousAddresses.add(ethers.getAddress(addr));
        } catch (error) {
          logger.debug(`Invalid address in watch list: ${addr}`);
        }
      });
      
      logger.info(`Watch lists initialized with ${this.knownMaliciousAddresses.size} known malicious addresses`);
      return true;
    } catch (error) {
      logger.error('Failed to initialize watch lists:', error.message);
      return false;
    }
  }

  /**
   * Scan for security threats in recent blockchain activity
   */
  async scanForThreats(blockRange = 10) {
    try {
      logger.info(`🔒 Scanning for security threats (last ${blockRange} blocks)...`);
      
      const currentBlock = await this.provider.getBlockNumber();
      const startBlock = Math.max(currentBlock - blockRange, 0);
      
      const threats = [];
      
      // Scan for various threat categories
      const addressThreats = await this.scanForMaliciousAddresses(startBlock, currentBlock);
      threats.push(...addressThreats);
      
      const contractThreats = await this.scanForVulnerableContracts(startBlock, currentBlock);
      threats.push(...contractThreats);
      
      const patternThreats = await this.scanForSuspiciousPatterns(startBlock, currentBlock);
      threats.push(...patternThreats);
      
      const exploitThreats = await this.scanForKnownExploits(startBlock, currentBlock);
      threats.push(...exploitThreats);
      
      this.lastScanTime = new Date();
      
      logger.info(`🔍 Threat scan complete: ${threats.length} threats detected`);
      return threats;
    } catch (error) {
      logger.error('Failed to scan for threats:', error.message);
      return [];
    }
  }

  /**
   * Scan for interactions with known malicious addresses
   */
  async scanForMaliciousAddresses(startBlock, endBlock) {
    try {
      const threats = [];
      
      for (const maliciousAddr of this.knownMaliciousAddresses) {
        // Get all transactions to/from malicious address
        const filter = {
          address: maliciousAddr,
          fromBlock: startBlock,
          toBlock: endBlock,
        };
        
        try {
          const logs = await this.provider.getLogs(filter);
          
          if (logs.length > 0) {
            threats.push({
              type: 'malicious_address_interaction',
              address: maliciousAddr,
              interactionCount: logs.length,
              severity: 'high',
              blockRange: { start: startBlock, end: endBlock },
              timestamp: new Date(),
            });
          }
        } catch (error) {
          logger.debug(`Error scanning address ${maliciousAddr}:`, error.message);
        }
      }
      
      return threats;
    } catch (error) {
      logger.error('Failed to scan for malicious addresses:', error.message);
      return [];
    }
  }

  /**
   * Scan for vulnerable smart contracts
   */
  async scanForVulnerableContracts(startBlock, endBlock) {
    try {
      const threats = [];
      
      // Get all contract creation events in range
      const deployments = await this.getContractDeployments(startBlock, endBlock);
      
      for (const deployment of deployments) {
        const vulnerabilities = await this.analyzeContractCode(deployment.address);
        
        if (vulnerabilities.length > 0) {
          threats.push({
            type: 'vulnerable_contract',
            address: deployment.address,
            creator: deployment.creator,
            vulnerabilities: vulnerabilities.slice(0, 5), // First 5
            severity: Math.max(...vulnerabilities.map(v => this.severityToScore(v.severity))),
            blockDeployed: deployment.blockNumber,
            timestamp: new Date(),
          });
        }
      }
      
      return threats;
    } catch (error) {
      logger.error('Failed to scan for vulnerable contracts:', error.message);
      return [];
    }
  }

  /**
   * Get contract deployments in a block range
   */
  async getContractDeployments(startBlock, endBlock) {
    try {
      const deployments = [];
      
      // Query for contract creation transactions
      for (let blockNum = startBlock; blockNum <= endBlock; blockNum++) {
        try {
          const block = await this.provider.getBlock(blockNum);
          
          for (const txHash of block.transactions) {
            const tx = await this.provider.getTransaction(txHash);
            
            // Contract creation transactions have tx.to === null
            if (tx.to === null) {
              const receipt = await this.provider.getTransactionReceipt(txHash);
              
              if (receipt && receipt.contractAddress) {
                deployments.push({
                  address: receipt.contractAddress,
                  creator: tx.from,
                  txHash: txHash,
                  blockNumber: blockNum,
                  codeSize: (tx.data?.length || 0) / 2,
                });
              }
            }
          }
        } catch (error) {
          logger.debug(`Error scanning block ${blockNum}:`, error.message);
        }
      }
      
      return deployments;
    } catch (error) {
      logger.error('Failed to get contract deployments:', error.message);
      return [];
    }
  }

  /**
   * Analyze contract code for vulnerabilities
   */
  async analyzeContractCode(contractAddress) {
    try {
      const code = await this.provider.getCode(contractAddress);
      
      if (code === '0x') {
        return []; // Not a contract
      }
      
      const vulnerabilities = [];
      
      // Check for vulnerability signatures
      for (const [vulnType, vulnInfo] of this.vulnerabilitySignatures) {
        // In production, this would use more sophisticated analysis
        // For now, we check for presence of vulnerability indicators
        
        const isVulnerable = this.checkCodeForPatterns(code, vulnInfo.patterns);
        
        if (isVulnerable) {
          vulnerabilities.push({
            type: vulnType,
            severity: vulnInfo.severity,
            description: vulnInfo.description,
          });
        }
      }
      
      return vulnerabilities;
    } catch (error) {
      logger.debug(`Failed to analyze contract ${contractAddress}:`, error.message);
      return [];
    }
  }

  /**
   * Check code for vulnerability patterns
   */
  checkCodeForPatterns(code, patterns) {
    // Simplified check - in production use more robust analysis
    for (const pattern of patterns) {
      try {
        const regex = new RegExp(pattern, 'i');
        if (regex.test(code)) {
          return true;
        }
      } catch (error) {
        logger.debug(`Error testing pattern ${pattern}:`, error.message);
      }
    }
    return false;
  }

  /**
   * Scan for suspicious transaction patterns
   */
  async scanForSuspiciousPatterns(startBlock, endBlock) {
    try {
      const threats = [];
      
      for (let blockNum = startBlock; blockNum <= endBlock; blockNum++) {
        try {
          const block = await this.provider.getBlock(blockNum);
          
          // Check for patterns in this block
          for (const txHash of block.transactions) {
            const tx = await this.provider.getTransaction(txHash);
            const receipt = await this.provider.getTransactionReceipt(txHash);
            
            // Pattern 1: High-value failed transactions (potential attack attempt)
            if (receipt && !receipt.status && tx.value && ethers.toNumber(tx.value) > ethers.parseEther('10')) {
              threats.push({
                type: 'high_value_failed_tx',
                txHash: txHash,
                from: tx.from,
                to: tx.to,
                value: ethers.formatEther(tx.value),
                severity: 'medium',
              });
            }
            
            // Pattern 2: Rapid sequential transactions from same address (flash loan pattern)
            // This would require tracking transaction sequences
            
            // Pattern 3: Large gas spend for contract deployment
            if (tx.to === null && receipt) {
              const gasCost = receipt.gasUsed * tx.gasPrice;
              if (gasCost > ethers.parseEther('1')) {
                threats.push({
                  type: 'expensive_deployment',
                  txHash: txHash,
                  from: tx.from,
                  gasCost: ethers.formatEther(gasCost),
                  severity: 'low',
                });
              }
            }
          }
        } catch (error) {
          logger.debug(`Error scanning block ${blockNum}:`, error.message);
        }
      }
      
      return threats;
    } catch (error) {
      logger.error('Failed to scan for suspicious patterns:', error.message);
      return [];
    }
  }

  /**
   * Scan for known exploit signatures
   */
  async scanForKnownExploits(startBlock, endBlock) {
    try {
      const threats = [];
      
      // This would check against a database of known exploit signatures
      // Examples:
      // - MEV exploit patterns
      // - Flash loan attack patterns
      // - Specific contract exploit signatures
      
      // Placeholder for known exploits
      const knownExploitSignatures = [
        // Would be populated from threat intelligence feeds
      ];
      
      // In production, scan contract interactions for exploit signatures
      logger.debug(`Checking ${knownExploitSignatures.length} known exploit signatures`);
      
      return threats;
    } catch (error) {
      logger.error('Failed to scan for known exploits:', error.message);
      return [];
    }
  }

  /**
   * Monitor a specific address for suspicious activity
   */
  async monitorAddress(address) {
    try {
      const normalizedAddress = ethers.getAddress(address);
      
      // Get address details
      const balance = await this.provider.getBalance(normalizedAddress);
      const code = await this.provider.getCode(normalizedAddress);
      const isContract = code !== '0x';
      
      const monitoringInfo = {
        address: normalizedAddress,
        isContract,
        balance: ethers.formatEther(balance),
        codeSize: (code.length - 2) / 2,
        timestamp: new Date(),
        riskScore: this.calculateAddressRisk(normalizedAddress, isContract),
      };
      
      logger.info('Monitoring address:', monitoringInfo);
      return monitoringInfo;
    } catch (error) {
      logger.error(`Failed to monitor address ${address}:`, error.message);
      throw error;
    }
  }

  /**
   * Calculate risk score for an address
   */
  calculateAddressRisk(address, isContract) {
    let riskScore = 0;
    
    // Check if in malicious list
    if (this.knownMaliciousAddresses.has(address)) {
      riskScore += 50;
    }
    
    // Contracts have inherent risk
    if (isContract) {
      riskScore += 10;
    }
    
    // Random additional factors (in production, use real metrics)
    riskScore += Math.floor(Math.random() * 20);
    
    return Math.min(riskScore, 100);
  }

  /**
   * Add address to watch list
   */
  addToWatchList(address) {
    try {
      const normalizedAddress = ethers.getAddress(address);
      this.knownMaliciousAddresses.add(normalizedAddress);
      logger.info(`Added ${normalizedAddress} to malicious watch list`);
      return true;
    } catch (error) {
      logger.error(`Failed to add address to watch list: ${error.message}`);
      return false;
    }
  }

  /**
   * Remove address from watch list
   */
  removeFromWatchList(address) {
    try {
      const normalizedAddress = ethers.getAddress(address);
      const removed = this.knownMaliciousAddresses.delete(normalizedAddress);
      logger.info(`Removed ${normalizedAddress} from watch list`);
      return removed;
    } catch (error) {
      logger.error(`Failed to remove address from watch list: ${error.message}`);
      return false;
    }
  }

  /**
   * Get current threat level
   */
  getThreatLevel() {
    const threatCountMap = this.threatCache.values();
    let totalThreats = 0;
    let criticalCount = 0;
    
    for (const threats of threatCountMap) {
      totalThreats += threats.length;
      criticalCount += threats.filter(t => t.severity === 'critical').length;
    }
    
    if (criticalCount > 0) return 'critical';
    if (totalThreats > 10) return 'high';
    if (totalThreats > 3) return 'medium';
    return 'low';
  }

  /**
   * Convert severity string to numeric score
   */
  severityToScore(severity) {
    const scoreMap = {
      critical: 100,
      high: 75,
      medium: 50,
      low: 25,
    };
    return scoreMap[severity] || 0;
  }

  /**
   * Get scanner status
   */
  getStatus() {
    return {
      name: this.name,
      watchListSize: this.knownMaliciousAddresses.size,
      vulnerabilitySignatures: this.vulnerabilitySignatures.size,
      lastScanTime: this.lastScanTime,
      threatLevel: this.getThreatLevel(),
      cacheSize: this.threatCache.size,
    };
  }

  /**
   * Close connections
   */
  async close() {
    logger.info('SecurityScanner closing');
    this.threatCache.clear();
    this.knownMaliciousAddresses.clear();
  }
}

export default SecurityScanner;
