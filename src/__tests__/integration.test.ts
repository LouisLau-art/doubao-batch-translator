import { FileScanner } from '../scanners/fileScanner';
import { processHtml } from '../processors/htmlProcessor';
import { processMarkdown } from '../processors/markdownProcessor';
import { CacheService } from '../services/cache';
import { DoubaoClient } from '../clients/doubaoClient';
import { BatchTranslator } from '../services/batchTranslator';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

describe('End-to-End Translation Flow', () => {
  let tempDir: string;
  let inputDir: string;
  let outputDir: string;
  let fileScanner: FileScanner;
  let batchTranslator: BatchTranslator;

  beforeEach(async () => {
    // Create temporary directories
    tempDir = path.join(os.tmpdir(), `integration-test-${Date.now()}`);
    inputDir = path.join(tempDir, 'input');
    outputDir = path.join(tempDir, 'output');
    await fs.mkdir(inputDir, { recursive: true });
    await fs.mkdir(outputDir, { recursive: true });

    // Create sample files
    await fs.writeFile(
      path.join(inputDir, 'test.html'),
      '<html><body><p>Hello World</p><img src="img.png" alt="Alt Text" /></body></html>'
    );
    await fs.writeFile(
      path.join(inputDir, 'test.md'),
      '# Hello World\n\n```\nconsole.log("Code Block");\n```\n\nText to translate'
    );

    // Initialize services
    fileScanner = new FileScanner();
    batchTranslator = new BatchTranslator();
  });

  afterEach(async () => {
    // Clean up temporary directories
    await fs.rm(tempDir, { recursive: true, force: true });
  });

  it('should translate a single HTML file end-to-end', async () => {
    // Mock translation function to control output
    const mockTranslate = jest.spyOn(batchTranslator, 'translateSegment');
    mockTranslate.mockResolvedValue('Bonjour Monde');

    // Scan input file
    const files = await fileScanner.scan(path.join(inputDir, 'test.html'));
    expect(files.length).toBe(1);

    // Process and translate
    const translatedFiles = await batchTranslator.translateFiles(
      files,
      'en',
      'fr',
      outputDir
    );

    // Verify output
    expect(translatedFiles.length).toBe(1);
    const outputPath = path.join(outputDir, 'test.html');
    const outputContent = await fs.readFile(outputPath, 'utf8');
    expect(outputContent).toContain('<p>Bonjour Monde</p>');
    expect(outputContent).toContain('alt="Bonjour Monde"'); // Translated alt text
  });

  it('should translate a single Markdown file end-to-end', async () => {
    // Mock translation function
    const mockTranslate = jest.spyOn(batchTranslator, 'translateSegment');
    mockTranslate.mockResolvedValue('Bonjour Monde');

    // Scan input file
    const files = await fileScanner.scan(path.join(inputDir, 'test.md'));
    expect(files.length).toBe(1);

    // Process and translate
    const translatedFiles = await batchTranslator.translateFiles(
      files,
      'en',
      'fr',
      outputDir
    );

    // Verify output
    expect(translatedFiles.length).toBe(1);
    const outputPath = path.join(outputDir, 'test.md');
    const outputContent = await fs.readFile(outputPath, 'utf8');
    expect(outputContent).toContain('# Bonjour Monde');
    expect(outputContent).toContain('```\nconsole.log("Code Block");\n```'); // Preserved code block
    expect(outputContent).toContain('Bonjour Monde'); // Translated text
  });

  it('should handle batch translation of multiple files', async () => {
    // Create additional test files
    await fs.writeFile(
      path.join(inputDir, 'test2.html'),
      '<html><body><p>Another File</p></body></html>'
    );
    await fs.writeFile(
      path.join(inputDir, 'test2.md'),
      '# Another File\n\nText to translate'
    );

    // Mock translation function
    const mockTranslate = jest.spyOn(batchTranslator, 'translateSegment');
    mockTranslate.mockResolvedValue('Translated Text');

    // Scan input directory
    const files = await fileScanner.scan(inputDir);
    expect(files.length).toBe(4); // 2 HTML, 2 Markdown? Wait, no, inputDir has test.html, test.md, test2.html, test2.md? Wait, no, in beforeEach, we created test.html, test.md, then test2.html and test2.md. So 4 files. Wait, FileScanner supports .html, .htm, .md, .markdown. So yes, 4 files.

    // Process batch translation
    const translatedFiles = await batchTranslator.translateFiles(
      files,
      'en',
      'fr',
      outputDir
    );

    // Verify output files
    const outputFiles = await fs.readdir(outputDir);
    expect(outputFiles.length).toBe(4); // 4 files translated

    // Verify content of one file
    const outputPath = path.join(outputDir, 'test.html');
    const outputContent = await fs.readFile(outputPath, 'utf8');
    expect(outputContent).toContain('<p>Translated Text</p>');
  });

  it('should handle error scenarios', async () => {
    // Create a file with invalid content (non-HTML/Markdown)
    await fs.writeFile(
      path.join(inputDir, 'invalid.txt'),
      'This is a text file'
    );

    // Scan input directory (should skip invalid file)
    const files = await fileScanner.scan(inputDir);
    expect(files.length).toBe(2); // Only test.html and test.md

    // Attempt to translate with invalid API key (mock error)
    const mockTranslate = jest.spyOn(batchTranslator, 'translateSegment');
    mockTranslate.mockRejectedValue(new Error('API key error'));

    // Expect error but still process files (with error handling)
    await expect(batchTranslator.translateFiles(
      files,
      'en',
      'fr',
      outputDir
    )).rejects.toThrow('API key error');
  });
});