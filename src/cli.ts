#!/usr/bin/env node
import * as commander from 'commander';
import dotenv from 'dotenv';
import { BatchTranslator } from './services/batchTranslator';
import { logger } from './utils/logger';

// Load environment variables
dotenv.config();

// Initialize CLI program
const program = new commander.Command();

program
  .name('doubao-translator')
  .description('Batch translate HTML/Markdown files using Doubao API')
  .version('1.0.0');

// Define CLI options
program
  .requiredOption('-i, --input <path>', 'Input file or directory path')
  .requiredOption('-o, --output <path>', 'Output directory path')
  .requiredOption('-t, --target-lang <lang>', 'Target language code (e.g., en, zh)')
  .option('-s, --source-lang <lang>', 'Source language code (auto-detected if not provided)')
  .option('-m, --model <model>', 'Doubao model ID (default: doubao-seed-translation-250915)')
  .option('-v, --verbose', 'Enable verbose logging')
  .option('-d, --dry-run', 'Dry run (show changes without writing files)')
  .option('-e, --encoding <encoding>', 'File encoding (default: utf8)');

// Parse command line arguments
program.parse(process.argv);
const options = program.opts();

// Configure logger
if (options.verbose) {
  logger.setLevel('debug');
}

// Update environment variables with CLI options
if (options.model) {
  process.env.DEFAULT_MODEL = options.model;
}

// Run batch translation
async function run() {
  try {
    const translator = new BatchTranslator({
      inputPath: options.input,
      outputPath: options.output,
      sourceLang: options.sourceLang,
      targetLang: options.targetLang,
      dryRun: options.dryRun,
      encoding: options.encoding as BufferEncoding || 'utf8',
    });

    await translator.run();
  } catch (error) {
    logger.error(`Translation failed: ${(error as Error).message}`);
    process.exit(1);
  }
}

run();