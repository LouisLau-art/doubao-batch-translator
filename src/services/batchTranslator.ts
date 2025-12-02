import path from 'path';
import { FileScanner, FileInfo } from '../scanners/fileScanner';
import { HTMLProcessor } from '../processors/htmlProcessor';
import { MarkdownProcessor } from '../processors/markdownProcessor';
import { cacheService } from './cache';
import { textSegmentationService } from './textSegmentation';
import { encodingService } from './encodingService';
import { OutputManager } from '../managers/outputManager';
import { DoubaoClient } from '../clients/doubaoClient';
import { MockDoubaoClient } from '../clients/mockDoubaoClient';
import { logger } from '../utils/logger';

/**
 * Batch translation service that ties together all components
 */
export class BatchTranslator {
  private fileScanner: FileScanner;
  private htmlProcessor: HTMLProcessor;
  private markdownProcessor: MarkdownProcessor;
  private outputManager: OutputManager;
  private doubaoClient: DoubaoClient;
  private dryRun: boolean;
  private sourceLang: string;
  private targetLang: string;
  private encoding: string;
  private inputDir: string;
  private outputDir: string;

  constructor(options: {
    inputPath: string;
    outputPath: string;
    sourceLang?: string;
    targetLang: string;
    dryRun?: boolean;
    encoding?: string;
  }) {
    this.fileScanner = new FileScanner();
    
    // Use mock client if no API key is provided
    if (process.env.ARK_API_KEY && process.env.ARK_API_KEY !== 'test_api_key_placeholder') {
      this.doubaoClient = new DoubaoClient();
    } else {
      logger.warn('Using mock Doubao client for testing. Set ARK_API_KEY for real translations.');
      this.doubaoClient = new MockDoubaoClient() as any;
    }
    
    this.htmlProcessor = new HTMLProcessor(this.doubaoClient);
    this.markdownProcessor = new MarkdownProcessor(this.doubaoClient);
    this.inputDir = options.inputPath;
    this.outputDir = options.outputPath;
    this.outputManager = new OutputManager(this.outputDir, options.dryRun);
    this.dryRun = options.dryRun ?? false;
    this.sourceLang = options.sourceLang ?? 'en';
    this.targetLang = options.targetLang;
    this.encoding = options.encoding ?? 'utf-8';
  }

  /**
   * Run the batch translation process
   */
  async run(): Promise<void> {
    logger.info(`Starting batch translation from ${this.inputDir} to ${this.outputDir}`);
    logger.info(`Source language: ${this.sourceLang}, Target language: ${this.targetLang}`);
    logger.info(`Dry run: ${this.dryRun ? 'Enabled' : 'Disabled'}`);
    logger.info(`Encoding: ${this.encoding}`);

    const files = await this.fileScanner.scan(this.inputDir);
    logger.info(`Found ${files.length} files to process`);

    for (const file of files) {
      await this.processFile(file);
    }

    logger.info('Batch translation completed successfully');
  }

  /**
   * Process a single file
   * @param file FileInfo object containing file details
   */
  private async processFile(file: FileInfo): Promise<void> {
    logger.verbose(`Processing file: ${file.relativePath}`);

    try {
      let translatedContent: string;
      
      if (file.path.endsWith('.html') || file.path.endsWith('.htm')) {
        translatedContent = await this.htmlProcessor.process(
          file.content,
          this.sourceLang,
          this.targetLang
        );
      } else if (file.path.endsWith('.md') || file.path.endsWith('.markdown')) {
        translatedContent = await this.markdownProcessor.process(
          file.content,
          this.sourceLang,
          this.targetLang
        );
      } else {
        logger.warn(`Skipping unsupported file type: ${file.path}`);
        return;
      }

      // Handle dry run or save file
      if (this.dryRun) {
        logger.info(`Dry run: Would write translated content to ${file.relativePath}`);
        logger.debug(`Original content:\n${file.content.slice(0, 100)}...\nTranslated content:\n${translatedContent.slice(0, 100)}...`);
      } else {
        await this.outputManager.writeFile({
          relativePath: file.relativePath,
          content: translatedContent,
          encoding: file.encoding
        });
        logger.info(`Saved translated file: ${file.relativePath}`);
      }
    } catch (error) {
      logger.error(`Error processing file ${file.relativePath}: ${(error as Error).message}`);
    }
  }
}