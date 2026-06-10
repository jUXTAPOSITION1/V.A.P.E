/**
 * Agent Commerce Protocol (ACP) Module
 * Integration with Virtuals Protocol for autonomous agent coordination
 * 
 * Responsibilities:
 * - Communicate findings to the Virtuals Protocol ecosystem
 * - Register investigation reports
 * - Coordinate with other agents
 * - Handle token incentives and rewards
 */

import axios from 'axios';
import logger from '../config/logger.js';

class ACPProtocol {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = process.env.VIRTUALS_API_URL || 'https://api.virtuals.io/v1';
    this.agentId = process.env.VAPE_AGENT_ID || 'vape_detective_001';
    this.name = 'ACP Protocol Handler';
    
    // HTTP client configuration
    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'V.A.P.E/1.0',
      },
      timeout: 30000,
    });
    
    // Track submitted reports for deduplication
    this.submittedReports = new Map();
    this.reportQueue = [];
    
    logger.info(`${this.name} initialized for agent: ${this.agentId}`);
  }

  /**
   * Register this agent with Virtuals Protocol
   */
  async registerAgent() {
    try {
      logger.info('Registering V.A.P.E with Virtuals Protocol...');
      
      const agentProfile = {
        id: this.agentId,
        name: 'V.A.P.E',
        title: 'Virtual Ape Private Eye',
        description: 'Cutting-edge fully autonomous AI detective engineered for the on-chain ecosystem',
        specializations: [
          'Blockchain Forensics & Asset Tracing',
          'Market Intelligence & Alpha Generation',
          'Protocol Security & Smart Contract Auditing',
          'Digital Asset Protection & Threat Intelligence',
          'Social & Narrative Intelligence',
        ],
        capabilities: [
          'real-time_monitoring',
          'threat_detection',
          'forensic_analysis',
          'market_intelligence',
          'alert_escalation',
        ],
        endpoints: {
          status: '/agent/status',
          reports: '/agent/reports',
          alerts: '/agent/alerts',
        },
        operatesOn: ['base', 'ethereum'],
        protocols: ['ACP', 'virtuals'],
      };
      
      const response = await this.client.post('/agents/register', agentProfile);
      logger.info('✅ Agent registered successfully:', response.data);
      return response.data;
    } catch (error) {
      logger.warn('Failed to register agent with Virtuals:', error.message);
      // Non-fatal - continue operation
      return { registered: false, error: error.message };
    }
  }

  /**
   * Submit investigation findings to Virtuals Protocol
   */
  async reportFindings(findingsReport) {
    try {
      const { caseId, forensics, threats, marketData } = findingsReport;
      
      // Generate report hash to prevent duplicates
      const reportHash = this.generateReportHash(findingsReport);
      
      if (this.submittedReports.has(reportHash)) {
        logger.debug(`Duplicate report detected for case ${caseId}, skipping submission`);
        return { submitted: false, reason: 'duplicate' };
      }
      
      const report = {
        agentId: this.agentId,
        caseId,
        timestamp: new Date().toISOString(),
        type: 'investigation_report',
        findings: {
          forensics: {
            blockRange: forensics?.blockRange,
            totalTransactions: forensics?.totalTransactions,
            suspiciousPatterns: forensics?.suspiciousPatterns?.length || 0,
            anomalies: forensics?.anomalies?.length || 0,
            largeTransfers: forensics?.largeTransfers || [],
            contractInteractions: forensics?.contractInteractions?.length || 0,
          },
          threats: {
            detected: threats?.length || 0,
            critical: threats?.filter(t => t.severity === 'critical').length || 0,
            high: threats?.filter(t => t.severity === 'high').length || 0,
            details: threats?.slice(0, 10) || [], // First 10 threats
          },
          marketData: {
            timestamp: marketData?.timestamp,
            metrics: marketData?.metrics || {},
          },
        },
        severity: this.calculateReportSeverity(forensics, threats, marketData),
        priority: this.calculatePriority(forensics, threats),
        requiresAction: (threats?.length || 0) > 0,
      };
      
      // Queue report for submission
      this.reportQueue.push(report);
      
      // Attempt immediate submission
      const submitted = await this.submitReport(report);
      
      if (submitted) {
        this.submittedReports.set(reportHash, {
          timestamp: Date.now(),
          caseId,
        });
      }
      
      return submitted;
    } catch (error) {
      logger.error('Failed to report findings:', error.message);
      return { submitted: false, error: error.message };
    }
  }

  /**
   * Submit a report to the Virtuals Protocol
   */
  async submitReport(report) {
    try {
      logger.info(`Submitting report for case ${report.caseId}...`);
      
      const response = await this.client.post('/reports/submit', report);
      
      logger.info(`✅ Report submitted successfully: ${response.data.reportId}`);
      
      return {
        submitted: true,
        reportId: response.data.reportId,
        timestamp: new Date(),
      };
    } catch (error) {
      logger.error(`Failed to submit report: ${error.message}`);
      
      // Re-queue for retry
      this.reportQueue.push(report);
      
      return {
        submitted: false,
        error: error.message,
        willRetry: true,
      };
    }
  }

  /**
   * Send critical alert to Virtuals ecosystem
   */
  async sendAlert(alert) {
    try {
      const { severity, findings, timestamp } = alert;
      
      logger.warn(`🚨 Sending ${severity} alert to Virtuals Protocol`);
      
      const acpAlert = {
        agentId: this.agentId,
        timestamp: timestamp || new Date().toISOString(),
        severity,
        type: 'security_alert',
        findings: {
          count: findings.length,
          details: findings.slice(0, 5), // First 5 findings
        },
        actionRequired: severity === 'critical',
        affectedChains: ['base'],
      };
      
      const response = await this.client.post('/alerts/send', acpAlert);
      
      logger.info(`✅ Alert sent with ID: ${response.data.alertId}`);
      
      return {
        sent: true,
        alertId: response.data.alertId,
      };
    } catch (error) {
      logger.error('Failed to send alert:', error.message);
      return {
        sent: false,
        error: error.message,
      };
    }
  }

  /**
   * Get status from Virtuals Protocol
   */
  async getAgentStatus() {
    try {
      const response = await this.client.get(`/agents/${this.agentId}/status`);
      
      return {
        agentId: this.agentId,
        status: response.data?.status,
        isActive: response.data?.isActive,
        lastReportTime: response.data?.lastReportTime,
        reportsSubmitted: response.data?.reportsSubmitted,
        reputation: response.data?.reputation,
      };
    } catch (error) {
      logger.debug('Failed to fetch agent status from Virtuals:', error.message);
      return {
        agentId: this.agentId,
        status: 'unknown',
        error: error.message,
      };
    }
  }

  /**
   * Retrieve agent rewards or incentives
   */
  async checkRewards() {
    try {
      const response = await this.client.get(`/agents/${this.agentId}/rewards`);
      
      const rewards = {
        pending: response.data?.pendingRewards || 0,
        claimed: response.data?.claimedRewards || 0,
        currency: response.data?.currency || 'VIRTUALS',
        lastClaimed: response.data?.lastClaimedAt,
      };
      
      logger.info('Rewards retrieved:', rewards);
      return rewards;
    } catch (error) {
      logger.debug('Failed to retrieve rewards:', error.message);
      return {
        pending: 0,
        claimed: 0,
        error: error.message,
      };
    }
  }

  /**
   * Claim pending rewards
   */
  async claimRewards() {
    try {
      const response = await this.client.post(`/agents/${this.agentId}/rewards/claim`, {
        agentId: this.agentId,
        timestamp: new Date().toISOString(),
      });
      
      logger.info('✅ Rewards claimed:', response.data);
      
      return {
        claimed: true,
        amount: response.data?.claimedAmount,
        txHash: response.data?.txHash,
      };
    } catch (error) {
      logger.error('Failed to claim rewards:', error.message);
      return {
        claimed: false,
        error: error.message,
      };
    }
  }

  /**
   * Coordinate with other agents in the ecosystem
   */
  async coordinateWithAgents(query) {
    try {
      logger.info(`Coordinating with agents on query: ${query}`);
      
      const response = await this.client.post('/agents/coordinate', {
        requesterAgentId: this.agentId,
        query,
        timestamp: new Date().toISOString(),
      });
      
      const agents = response.data?.agents || [];
      logger.info(`Found ${agents.length} agents for coordination`);
      
      return {
        query,
        respondingAgents: agents.length,
        agents: agents.slice(0, 5), // First 5 agents
      };
    } catch (error) {
      logger.debug('Failed to coordinate with agents:', error.message);
      return {
        query,
        respondingAgents: 0,
        agents: [],
        error: error.message,
      };
    }
  }

  /**
   * Submit a proof of work/investigation
   */
  async submitProofOfWork(investigation) {
    try {
      const pow = {
        agentId: this.agentId,
        investigationId: investigation.id,
        type: investigation.type, // e.g., 'fraud_detection', 'vulnerability_disclosure'
        evidence: investigation.evidence,
        timestamp: new Date().toISOString(),
        difficulty: this.calculateDifficulty(investigation),
      };
      
      const response = await this.client.post('/pow/submit', pow);
      
      logger.info('✅ Proof of work submitted:', response.data);
      
      return {
        submitted: true,
        workId: response.data?.workId,
        rewardEligible: response.data?.rewardEligible,
      };
    } catch (error) {
      logger.error('Failed to submit proof of work:', error.message);
      return {
        submitted: false,
        error: error.message,
      };
    }
  }

  /**
   * Calculate report severity based on findings
   */
  calculateReportSeverity(forensics, threats, marketData) {
    if (!threats || threats.length === 0) return 'low';
    
    const criticalCount = threats.filter(t => t.severity === 'critical').length;
    const highCount = threats.filter(t => t.severity === 'high').length;
    
    if (criticalCount > 0) return 'critical';
    if (highCount > 2) return 'high';
    if (highCount > 0) return 'medium';
    return 'low';
  }

  /**
   * Calculate report priority
   */
  calculatePriority(forensics, threats) {
    const threatCount = threats?.length || 0;
    const suspiciousPatterns = forensics?.suspiciousPatterns?.length || 0;
    
    const score = (threatCount * 10) + (suspiciousPatterns * 3);
    
    if (score > 100) return 'critical';
    if (score > 50) return 'high';
    if (score > 10) return 'medium';
    return 'low';
  }

  /**
   * Generate hash for report deduplication
   */
  generateReportHash(report) {
    const key = `${report.caseId}_${report.forensics?.blockRange?.start}_${report.threats?.length}`;
    return Buffer.from(key).toString('base64');
  }

  /**
   * Calculate difficulty score for proof of work
   */
  calculateDifficulty(investigation) {
    // Simplified difficulty calculation
    const evidenceSize = investigation.evidence ? investigation.evidence.length : 0;
    const complexity = investigation.type === 'vulnerability_disclosure' ? 2 : 1;
    
    return (evidenceSize / 1000) * complexity;
  }

  /**
   * Flush queued reports (retry mechanism)
   */
  async flushReportQueue() {
    if (this.reportQueue.length === 0) {
      return { flushed: 0 };
    }
    
    logger.info(`Flushing ${this.reportQueue.length} queued reports...`);
    
    let flushed = 0;
    const failed = [];
    
    while (this.reportQueue.length > 0) {
      const report = this.reportQueue.shift();
      
      try {
        const result = await this.submitReport(report);
        if (result.submitted) {
          flushed++;
        } else {
          failed.push(report);
        }
      } catch (error) {
        logger.error('Error flushing report:', error.message);
        failed.push(report);
      }
    }
    
    // Re-queue failed reports
    this.reportQueue.push(...failed);
    
    logger.info(`Flushed ${flushed} reports, ${failed.length} failed and re-queued`);
    
    return {
      flushed,
      failed: failed.length,
      queueRemaining: this.reportQueue.length,
    };
  }

  /**
   * Get ACP protocol status
   */
  async getStatus() {
    return {
      protocol: 'ACP',
      agentId: this.agentId,
      connected: true,
      baseUrl: this.baseUrl,
      queuedReports: this.reportQueue.length,
      submittedReportsTracked: this.submittedReports.size,
    };
  }

  /**
   * Close connections
   */
  async close() {
    logger.info('Closing ACP Protocol handler');
    
    // Attempt to flush remaining reports
    if (this.reportQueue.length > 0) {
      await this.flushReportQueue();
    }
  }
}

export default ACPProtocol;
