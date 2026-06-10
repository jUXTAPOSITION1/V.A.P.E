/**
 * Logger configuration
 * Simple logger for development
 */

const LOG_LEVELS = {
  error: 0,
  warn: 1,
  info: 2,
  debug: 3
};

const currentLevel = LOG_LEVELS[process.env.LOG_LEVEL || 'info'];

const logger = {
  error: (message, error = '') => {
    if (currentLevel >= LOG_LEVELS.error) {
      console.error(`[ERROR] ${new Date().toISOString()} ${message}`, error);
    }
  },
  warn: (message) => {
    if (currentLevel >= LOG_LEVELS.warn) {
      console.warn(`[WARN] ${new Date().toISOString()} ${message}`);
    }
  },
  info: (message) => {
    if (currentLevel >= LOG_LEVELS.info) {
      console.log(`[INFO] ${new Date().toISOString()} ${message}`);
    }
  },
  debug: (message) => {
    if (currentLevel >= LOG_LEVELS.debug) {
      console.debug(`[DEBUG] ${new Date().toISOString()} ${message}`);
    }
  }
};

export default logger;
