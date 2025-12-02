interface CacheEntry {
  encoding: string;
  content: string;
}

/**
 * Cache for storing encoding detection results to avoid repeated detection
 */
export const encodingCache = {
  _cache: new Map<string, CacheEntry>(),

  get(filePath: string): CacheEntry | undefined {
    return this._cache.get(filePath);
  },

  set(filePath: string, value: CacheEntry): void {
    this._cache.set(filePath, value);
  },

  clear(): void {
    this._cache.clear();
  }
};