import dotenv from 'dotenv';
dotenv.config();

export class Logger {
  private level: string;

  constructor() {
    this.level = process.env.LOG_LEVEL || 'info';
  }

  setLevel(level: string): void {
    this.level = level;
  }

  info(message: string): void {
    if (['info', 'debug', 'verbose'].includes(this.level)) {
      console.log(`[INFO] ${new Date().toISOString()}: ${message}`);
    }
  }

  error(message: string, error?: Error): void {
    console.error(`[ERROR] ${new Date().toISOString()}: ${message}`);
    if (error && ['debug', 'verbose'].includes(this.level)) {
      console.error(error.stack);
    }
  }

  debug(message: string): void {
    if (['debug', 'verbose'].includes(this.level)) {
      console.debug(`[DEBUG] ${new Date().toISOString()}: ${message}`);
    }
  }

  verbose(message: string): void {
    if (this.level === 'verbose') {
      console.debug(`[VERBOSE] ${new Date().toISOString()}: ${message}`);
    }
  }

  warn(message: string): void {
    if (['warn', 'info', 'debug', 'verbose'].includes(this.level)) {
      console.warn(`[WARN] ${new Date().toISOString()}: ${message}`);
    }
  }
}

export const logger = new Logger();