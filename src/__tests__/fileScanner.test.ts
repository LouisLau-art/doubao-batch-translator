import { FileScanner, SupportedEncoding } from '../scanners/fileScanner';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

describe('FileScanner Unit Tests', () => {
  let fileScanner: FileScanner;
  let tempDir: string;

  beforeEach(async () => {
    // Create a temporary directory for testing
    tempDir = path.join(os.tmpdir(), `file-scanner-test-${Date.now()}`);
    await fs.mkdir(tempDir, { recursive: true });
    // Set current working directory to the temporary directory
    process.chdir(tempDir);
    // Initialize FileScanner
    fileScanner = new FileScanner();
  });

  afterEach(async () => {
    // Clean up the temporary directory
    await fs.rm(tempDir, { recursive: true, force: true });
    // Reset current working directory
    process.chdir(os.homedir());
  });

  // Helper function to create test files
  async function createTestFile(
    fileName: string,
    content: string,
    encoding: SupportedEncoding = 'utf8'
  ): Promise<string> {
    const filePath = path.join(tempDir, fileName);
    const buffer = iconv.encode(content, encoding);
    await fs.writeFile(filePath, buffer);
    return filePath;
  }

  it('should identify supported file types', () => {
    expect(fileScanner.isSupportedFile('test.html')).toBe(true);
    expect(fileScanner.isSupportedFile('test.md')).toBe(true);
    expect(fileScanner.isSupportedFile('test.txt')).toBe(false);
    expect(fileScanner.isSupportedFile('test.js')).toBe(false);
  });

  it('should detect hidden files', () => {
    expect(fileScanner.isHiddenFile('.hidden')).toBe(true);
    expect(fileScanner.isHiddenFile('_hidden')).toBe(true);
    expect(fileScanner.isHiddenFile('visible')).toBe(false);
  });

  it('should detect UTF-8 encoding', async () => {
    const content = 'Hello, World!';
    const filePath = await createTestFile('test-utf8.html', content, 'utf8');
    const encoding = await fileScanner.detectEncoding(filePath);
    expect(encoding).toBe('utf8');
  });

  it('should detect GBK encoding', async () => {
    const content = '你好，世界！';
    const filePath = await createTestFile('test-gbk.html', content, 'gbk');
    const encoding = await fileScanner.detectEncoding(filePath);
    expect(encoding).toBe('gbk');
  });

  it('should read file content with correct encoding', async () => {
    const content = 'Hello, World!';
    const filePath = await createTestFile('test-read.html', content, 'utf8');
    const fileInfo = (await fileScanner.scan(filePath))[0];
    expect(fileInfo.content).toBe(content);
    expect(fileInfo.encoding).toBe('utf8');
  });

  it('should scan a single file', async () => {
    const content = 'Hello, World!';
    const filePath = await createTestFile('test-file.html', content, 'utf8');
    const files = await fileScanner.scan(filePath);
    expect(files.length).toBe(1);
    expect(files[0].path).toBe(filePath);
    expect(files[0].content).toBe(content);
  });

  it('should scan a directory recursively', async () => {
    // Create a directory structure
    const subDir = path.join(tempDir, 'subdir');
    await fs.mkdir(subDir, { recursive: true });
    await createTestFile('file1.html', 'Content 1', 'utf8');
    await createTestFile(path.join('subdir', 'file2.md'), 'Content 2', 'gbk');
    await createTestFile(path.join('subdir', 'file3.txt'), 'Content 3', 'utf8'); // Should be ignored

    const files = await fileScanner.scan(tempDir);
    expect(files.length).toBe(2); // file3.txt is not supported
    expect(files.some(f => f.path.includes('file1.html'))).toBe(true);
    expect(files.some(f => f.path.includes('file2.md'))).toBe(true);
  });

  it('should skip hidden files', async () => {
    await createTestFile('.hidden.html', 'Hidden Content', 'utf8');
    await createTestFile('_hidden.md', 'Hidden Content', 'gbk');
    const files = await fileScanner.scan(tempDir);
    expect(files.length).toBe(0);
  });
});