import { BatchTranslator } from '../services/batchTranslator';
import { FileScanner } from '../scanners/fileScanner';
import { HTMLProcessor } from '../processors/htmlProcessor';
import { MarkdownProcessor } from '../processors/markdownProcessor';
import { OutputManager } from '../managers/outputManager';
import { DoubaoClient } from '../clients/doubaoClient';
import { MockDoubaoClient } from '../clients/mockDoubaoClient';
import { logger } from '../utils/logger';

// Mock external dependencies
jest.mock('../scanners/fileScanner');
jest.mock('../processors/htmlProcessor');
jest.mock('../processors/markdownProcessor');
jest.mock('../managers/outputManager');
jest.mock('../clients/doubaoClient');
jest.mock('../clients/mockDoubaoClient');
jest.mock('../utils/logger');

describe('BatchTranslator Unit Tests', () => {
  let batchTranslator: BatchTranslator;
  const MockFileScanner = FileScanner as jest.MockedClass<typeof FileScanner>;
  const MockHTMLProcessor = HTMLProcessor as jest.MockedClass<typeof HTMLProcessor>;
  const MockMarkdownProcessor = MarkdownProcessor as jest.MockedClass<typeof MarkdownProcessor>;
  const MockOutputManager = OutputManager as jest.MockedClass<typeof OutputManager>;
  const MockDoubaoClient = DoubaoClient as jest.MockedClass<typeof DoubaoClient>;
  const MockMockDoubaoClient = MockDoubaoClient as jest.MockedClass<typeof MockDoubaoClient>;

  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();

    // Set environment variables for testing
    process.env.ARK_API_KEY = 'test_api_key';

    // Mock dependencies
    MockFileScanner.mockImplementation(() => ({
      scan: jest.fn().mockResolvedValue([{
        path: 'test.html',
        relativePath: 'test.html',
        content: '<html><body><p>Hello</p></body></html>',
        encoding: 'utf8',
      } as any]),
    }));

    MockHTMLProcessor.mockImplementation(() => ({
      process: jest.fn().mockResolvedValue('<html><body><p>Translated</p></body></html>'),
    }));

    MockMarkdownProcessor.mockImplementation(() => ({
      process: jest.fn().mockResolvedValue('# Translated'),
    }));

    MockOutputManager.mockImplementation(() => ({
      writeFile: jest.fn().mockResolvedValue(undefined),
    }));

    MockDoubaoClient.mockImplementation(() => ({
      translate: jest.fn().mockResolvedValue('Translated'),
    }));

    MockMockDoubaoClient.mockImplementation(() => ({
      translate: jest.fn().mockResolvedValue('Mock Translated'),
    }));

    // Initialize BatchTranslator
    batchTranslator = new BatchTranslator({
      inputPath: 'input',
      outputPath: 'output',
      sourceLang: 'en',
      targetLang: 'zh',
      dryRun: false,
      encoding: 'utf8',
    });
  });

  afterEach(() => {
    // Clear environment variables
    delete process.env.ARK_API_KEY;
  });

  it('should initialize with real Doubao client when API key is present', () => {
    expect(MockDoubaoClient).toHaveBeenCalled();
    expect(MockMockDoubaoClient).not.toHaveBeenCalled();
  });

  it('should initialize with mock Doubao client when API key is not present', () => {
    delete process.env.ARK_API_KEY;
    const mockBatchTranslator = new BatchTranslator({
      inputPath: 'input',
      outputPath: 'output',
      sourceLang: 'en',
      targetLang: 'zh',
      dryRun: false,
      encoding: 'utf8',
    });
    expect(MockMockDoubaoClient).toHaveBeenCalled();
    expect(MockDoubaoClient).not.toHaveBeenCalled();
  });

  it('should process an HTML file', async () => {
    const file = {
      path: 'test.html',
      relativePath: 'test.html',
      content: '<html><body><p>Hello</p></body></html>',
      encoding: 'utf8',
    } as any;

    await batchTranslator['processFile'](file);
    expect(MockHTMLProcessor.prototype.process).toHaveBeenCalledWith(
      file.content,
      'en',
      'zh'
    );
    expect(MockOutputManager.prototype.writeFile).toHaveBeenCalled();
  });

  it('should process a Markdown file', async () => {
    const file = {
      path: 'test.md',
      relativePath: 'test.md',
      content: '# Hello',
      encoding: 'utf8',
    } as any;

    await batchTranslator['processFile'](file);
    expect(MockMarkdownProcessor.prototype.process).toHaveBeenCalledWith(
      file.content,
      'en',
      'zh'
    );
    expect(MockOutputManager.prototype.writeFile).toHaveBeenCalled();
  });

  it('should skip unsupported file type', async () => {
    const file = {
      path: 'test.txt',
      relativePath: 'test.txt',
      content: 'Hello',
      encoding: 'utf8',
    } as any;

    await batchTranslator['processFile'](file);
    expect(MockHTMLProcessor.prototype.process).not.toHaveBeenCalled();
    expect(MockMarkdownProcessor.prototype.process).not.toHaveBeenCalled();
    expect(MockOutputManager.prototype.writeFile).not.toHaveBeenCalled();
    expect(logger.warn).toHaveBeenCalledWith('Skipping unsupported file type: test.txt');
  });

  it('should handle dry run mode', async () => {
    const dryRunBatchTranslator = new BatchTranslator({
      inputPath: 'input',
      outputPath: 'output',
      sourceLang: 'en',
      targetLang: 'zh',
      dryRun: true,
      encoding: 'utf8',
    });

    const file = {
      path: 'test.html',
      relativePath: 'test.html',
      content: '<html><body><p>Hello</p></body></html>',
      encoding: 'utf8',
    } as any;

    await dryRunBatchTranslator['processFile'](file);
    expect(MockHTMLProcessor.prototype.process).toHaveBeenCalled();
    expect(MockOutputManager.prototype.writeFile).not.toHaveBeenCalled();
    expect(logger.info).toHaveBeenCalledWith('Dry run: Would write translated content to test.html');
  });

  it('should handle error during file processing', async () => {
    const file = {
      path: 'test.html',
      relativePath: 'test.html',
      content: '<html><body><p>Hello</p></body></html>',
      encoding: 'utf8',
    } as any;

    MockHTMLProcessor.prototype.process.mockRejectedValue(new Error('Processing error'));

    await batchTranslator['processFile'](file);
    expect(logger.error).toHaveBeenCalledWith('Error processing file test.html: Processing error');
  });
});