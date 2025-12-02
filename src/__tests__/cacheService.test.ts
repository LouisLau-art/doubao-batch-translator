import { CacheService } from '../services/cache';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

describe('CacheService Unit Tests', () => {
  let cacheService: CacheService;
  let tempDir: string;

  beforeEach(async () => {
    // Create a temporary directory for testing
    tempDir = path.join(os.tmpdir(), `cache-test-${Date.now()}`);
    // Set current working directory to the temporary directory
    process.chdir(tempDir);
    // Initialize CacheService with the temporary directory
    cacheService = new CacheService();
  });

  afterEach(async () => {
    // Clean up the temporary directory
    await fs.rm(tempDir, { recursive: true, force: true });
    // Reset current working directory
    process.chdir(os.homedir());
  });

  it('should generate a unique cache key', () => {
    const key = cacheService.generateKey('test text', 'en', 'zh');
    expect(key).toMatch(/^[a-f0-9]{32}\.json$/);
  });

  it('should store and retrieve a cached translation', async () => {
    const text = 'Hello World';
    const sourceLang = 'en';
    const targetLang = 'zh';
    const translation = '你好，世界';
    const key = cacheService.generateKey(text, sourceLang, targetLang);

    await cacheService.set(key, translation);
    const result = await cacheService.get(key);

    expect(result).toBe(translation);
  });

  it('should delete a cached translation', async () => {
    const text = 'Hello World';
    const sourceLang = 'en';
    const targetLang = 'zh';
    const translation = '你好，世界';
    const key = cacheService.generateKey(text, sourceLang, targetLang);

    await cacheService.set(key, translation);
    await cacheService.delete(key);
    const result = await cacheService.get(key);

    expect(result).toBeNull();
  });

  it('should clear all cached translations', async () => {
    const key1 = cacheService.generateKey('Text 1', 'en', 'zh');
    const key2 = cacheService.generateKey('Text 2', 'en', 'zh');
    const translation1 = 'Translation 1';
    const translation2 = 'Translation 2';

    await cacheService.set(key1, translation1);
    await cacheService.set(key2, translation2);

    await cacheService.clear();

    const result1 = await cacheService.get(key1);
    const result2 = await cacheService.get(key2);

    expect(result1).toBeNull();
    expect(result2).toBeNull();
  });
});