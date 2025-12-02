import fs from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { config } from '../config';

/**
 * File-based cache service for translated segments
 */
export class CacheService {
  private cacheDir: string;

  constructor() {
    this.cacheDir = path.join(process.cwd(), '.cache');
    this.initializeCacheDir();
  }

  /**
   * Initialize cache directory if it doesn't exist
   */
  private async initializeCacheDir(): Promise<void> {
    try {
      await fs.access(this.cacheDir);
    } catch {
      await fs.mkdir(this.cacheDir, { recursive: true });
    }
  }

  /**
   * Generate a unique cache key for a segment
   * @param text Input text to translate
   * @param sourceLang Source language code
   * @param targetLang Target language code
   * @returns Unique cache key
   */
  generateKey(text: string, sourceLang: string, targetLang: string): string {
    const hash = crypto.createHash('md5')
      .update(text)
      .update(sourceLang)
      .update(targetLang)
      .update(config.model)
      .digest('hex');
    return `${hash}.json`;
  }

  /**
   * Get cached translation for a segment
   * @param key Cache key
   * @returns Cached translation or null if not found
   */
  async get(key: string): Promise<string | null> {
    const cachePath = path.join(this.cacheDir, key);
    try {
      const data = await fs.readFile(cachePath, 'utf-8');
      const { translation, timestamp } = JSON.parse(data);
      
      // Optional: Add TTL check here (e.g., 7 days)
      // const ttl = 7 * 24 * 60 * 60 * 1000;
      // if (Date.now() - timestamp > ttl) {
      //   await this.delete(key);
      //   return null;
      // }
      
      return translation;
    } catch {
      return null;
    }
  }

  /**
   * Set cached translation for a segment
   * @param key Cache key
   * @param translation Translated text
   */
  async set(key: string, translation: string): Promise<void> {
    const cachePath = path.join(this.cacheDir, key);
    const data = JSON.stringify({
      translation,
      timestamp: Date.now(),
      model: config.model
    }, null, 2);
    await fs.writeFile(cachePath, data, 'utf-8');
  }

  /**
   * Delete a cached entry
   * @param key Cache key
   */
  async delete(key: string): Promise<void> {
    const cachePath = path.join(this.cacheDir, key);
    try {
      await fs.unlink(cachePath);
    } catch {
      // Ignore if file doesn't exist
    }
  }

  /**
   * Clear all cached entries
   */
  async clear(): Promise<void> {
    const files = await fs.readdir(this.cacheDir);
    for (const file of files) {
      if (file.endsWith('.json')) {
        await this.delete(file);
      }
    }
  }
}

// Singleton instance
export const cacheService = new CacheService();