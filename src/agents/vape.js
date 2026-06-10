/**
 * V.A.P.E. - Virtual Ape Private Eye
 * Main Agent File: Core autonomous detective engine
 * 
 * Responsibilities:
 * - Initialize the detective agent
 * - Coordinate blockchain forensics operations
 * - Manage case investigations
 * - Deliver security intelligence
 */

import dotenv from 'dotenv';
import { ethers } from 'ethers';
import logger from '../config/logger.js';
import BlockchainAnalyzer from '../blockchain/analyzer.js';
import ACPProtocol from '../acp/protocol.js';
import SecurityScanner from '../security/scanner.js';
import DataFetcher from '../data-fetchers/fetcher.js';

// Load environment variables
dotenv.config();

/**
 * V.A.P.E Detective Agent
 * Orchestrates all investigation modules and threat detection
 */
class VAPEAgent {
  constructor() {
    this.name = 'V.A.P.E.';
    this.title = 'Virtual Ape Private Eye';
    this.isActive = false;
    this.casesInvestigated = 0;
    
    // Initialize core modules
    this.blockchain = null;
    this.acp = null;
    this.security = null;
    this.dataFetcher = null;
    
    // Configuration
    this.config = {
      baseRpc: process.env.BASE_RPC_URL || 'https://mainnet.base.org',
      virtualsApiKey: process.env.VIRTUALS_API_KEY,
      checkInterval: parseInt(process.env.CHECK_INTERVAL || '60000', 10), // ms between scans
      maxCasesPerRun: parseInt(process.env.MAX_CASES_PER_RUN || '10', 10),
    };
    
    logger.info(`${this.name} initialized with config:`, {
      baseRpc: this.config.baseRpc,
      hasVirualsKey: !!this.config.virtualsApiKey,
      checkInterval: this.config.checkInterval,
    });
  }

  /**
   * Startup procedure - Initialize all modules and establish connections
   */
  async initialize() {
    try {
      logger.info('🔍 V.A.P.E starting investigation...');
      
      // Validate environment
      this.validateEnvironment();
      
      // Initialize blockchain provider
      const provider = new ethers.JsonRpcProvider(this.config.baseRpc);
      await this.verifyConnection(provider);
      
      // Initialize modules
      this.blockchain = new BlockchainAnalyzer(provider);
      this.acp = new ACPProtocol(this.config.virtualsApiKey);
      this.security = new SecurityScanner(provider);
      this.dataFetcher = new DataFetcher(provider);
      
      logger.info('✅ All modules initialized successfully');
      
      // Load initial data
      await this.loadInitialData();
      
      this.isActive = true;
      logger.info('🦍 V.A.P.E is now ACTIVE and ready to investigate');
      
      return true;
    } catch (error) {
      logger.error('❌ Initialization failed:', error.message);
      this.isActive = false;
      throw error;
    }
  }

  /**
   * Validate required environment variables
   */
  validateEnvironment() {
    const required = ['BASE_RPC_URL'];
    const missing = required.filter(key => !process.env[key]);
    
    if (missing.length > 0) {
      throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
    }
    
    logger.info('✓ Environment variables validated');
  }

  /**
   * Verify connection to Base blockchain
   */
  async verifyConnection(provider) {
    try {
      const blockNumber = await provider.getBlockNumber();
      logger.info(`Connected to Base at block ${blockNumber}`);
    } catch (error) {
      throw new Error(`Failed to connect to Base RPC: ${error.message}`);
    }
  }

  /**
   * Load initial blockchain data and state
   */
  async loadInitialData() {
    try {
      logger.info('📊 Loading initial blockchain data...');
      
      // Get current network state
      const networkState = await this.blockchain.getNetworkState();
      logger.info('Network state loaded:', networkState);
      
      // Initialize security watch lists
      await this.security.initializeWatchLists();
      logger.info('Security watch lists initialized');
      
    } catch (error) {
      logger.warn('Failed to load initial data:', error.message);
      // Non-fatal - continue operation
    }
  }

  /**
   * Start continuous investigation loop
   */
  async startInvestigation() {
    if (!this.isActive) {
      logger.error('Cannot start investigation: agent not initialized');
      return;
    }
    
    logger.info('🔎 Beginning continuous investigations...');
    
    // Investigation loop
    setInterval(async () => {
      await this.runInvestigationCycle();
    }, this.config.checkInterval);
    
    // Run initial cycle immediately
    await this.runInvestigationCycle();
  }

  /**
   * Single investigation cycle - scans for threats and anomalies
   */
  async runInvestigationCycle() {
    const cycleId = this.generateCaseId();
    
    try {
      logger.info(`[${cycleId}] Starting investigation cycle`);
      
      // Phase 1: Blockchain Forensics
      const forensics = await this.blockchain.analyzeRecentActivity();
      
      // Phase 2: Smart Contract Security Scan
      const securityThreats = await this.security.scanForThreats();
      
      // Phase 3: Market Intelligence
      const marketData = await this.dataFetcher.getMarketMetrics();
      
      // Phase 4: ACP Protocol Coordination
      if (this.acp) {
        await this.acp.reportFindings({
          caseId: cycleId,
          forensics,
          threats: securityThreats,
          marketData,
        });
      }
      
      // Phase 5: Analyze findings
      const findings = this.synthesizeFindings(forensics, securityThreats, marketData);
      
      // Log critical findings
      if (findings.critical.length > 0) {
        logger.warn(`[${cycleId}] 🚨 CRITICAL findings detected:`, findings.critical);
        await this.escalateAlert(findings.critical);
      }
      
      if (findings.warnings.length > 0) {
        logger.info(`[${cycleId}] ⚠️ Warnings identified:`, findings.warnings);
      }
      
      this.casesInvestigated++;
      logger.info(`[${cycleId}] Investigation cycle complete. Cases total: ${this.casesInvestigated}`);
      
    } catch (error) {
      logger.error(`[${cycleId}] Investigation cycle failed:`, error.message);
    }
  }

  /**
   * Synthesize findings from all investigation phases
   */
  synthesizeFindings(forensics, threats, marketData) {
    const findings = {
      critical: [],
      warnings: [],
      insights: [],
    };
    
    // Check for critical security threats
    if (threats && threats.length > 0) {
      const criticalThreats = threats.filter(t => t.severity === 'critical');
      findings.critical.push(...criticalThreats);
    }
    
    // Check for forensic anomalies
    if (forensics && forensics.anomalies) {
      findings.warnings.push(...forensics.anomalies.filter(a => a.severity === 'high'));
      findings.insights.push(...forensics.anomalies.filter(a => a.severity !== 'high'));
    }
    
    return findings;
  }

  /**
   * Escalate critical alerts to external systems
   */
  async escalateAlert(criticalFindings) {
    try {
      // This would integrate with notification systems, Discord webhooks, etc.
      logger.warn('ALERT ESCALATION:', criticalFindings);
      
      if (this.acp) {
        await this.acp.sendAlert({
          severity: 'critical',
          findings: criticalFindings,
          timestamp: new Date(),
        });
      }
    } catch (error) {
      logger.error('Failed to escalate alert:', error.message);
    }
  }

  /**
   * Generate unique case ID
   */
  generateCaseId() {
    return `CASE_${Date.now()}_${Math.random().toString(36).substring(7)}`;
  }

  /**
   * Get agent status report
   */
  getStatus() {
    return {
      name: this.name,
      title: this.title,
      isActive: this.isActive,
      casesInvestigated: this.casesInvestigated,
      uptime: process.uptime(),
      memoryUsage: process.memoryUsage(),
      config: {
        checkInterval: this.config.checkInterval,
        maxCasesPerRun: this.config.maxCasesPerRun,
      },
      modules: {
        blockchain: !!this.blockchain,
        acp: !!this.acp,
        security: !!this.security,
        dataFetcher: !!this.dataFetcher,
      },
    };
  }

  /**
   * Graceful shutdown
   */
  async shutdown() {
    try {
      logger.info('🛑 V.A.P.E shutting down...');
      this.isActive = false;
      
      // Close connections gracefully
      if (this.blockchain) await this.blockchain.close?.();
      if (this.acp) await this.acp.close?.();
      if (this.security) await this.security.close?.();
      if (this.dataFetcher) await this.dataFetcher.close?.();
      
      logger.info('✅ V.A.P.E shutdown complete');
      process.exit(0);
    } catch (error) {
      logger.error('Error during shutdown:', error);
      process.exit(1);
    }
  }
}

/**
 * Application Entry Point
 */
async function main() {
  const vape = new VAPEAgent();
  
  // Handle graceful shutdown
  process.on('SIGINT', () => vape.shutdown());
  process.on('SIGTERM', () => vape.shutdown());
  
  try {
    // Initialize and start
    await vape.initialize();
    await vape.startInvestigation();
    
    // Keep process alive
    logger.info('🔍 V.A.P.E is running. Press Ctrl+C to stop.');
    
  } catch (error) {
    logger.error('Fatal error:', error);
    process.exit(1);
  }
}

// Start the agent
main().catch(error => {
  console.error('Uncaught error:', error);
  process.exit(1);
});

export default VAPEAgent;
