import * as fs from 'fs/promises';
import * as path from 'path';
import * as iconv from 'iconv-lite';
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';
import { logger } from '../utils/logger';
import { encodingCache } from '../services/encodingCache';

export type SupportedEncoding = 'utf8' | 'gbk';

export interface FileInfo {
  path: string;
  relativePath: string;
  content: string;
  encoding: SupportedEncoding;
}

const MAX_WORKERS = 4;

export class FileScanner {
  private supportedExtensions = new Set(['.html', '.htm', '.md', '.markdown']);
  private workerPool: Worker[] = [];

  private isSupportedFile(filePath: string): boolean {
    const ext = path.extname(filePath).toLowerCase();
    return this.supportedExtensions.has(ext);
  }

  private isHiddenFile(fileName: string): boolean {
    return fileName.startsWith('.') || fileName.startsWith('_');
  }

  private async detectEncoding(filePath: string): Promise<SupportedEncoding> {
    try {
      const cached = encodingCache.get(filePath);
      if (cached) {
        return cached.encoding as SupportedEncoding;
      }

      const buffer = await fs.readFile(filePath);
      
      // Try UTF-8 first
      const utf8Text = iconv.decode(buffer, 'utf8');
      if (!/�/.test(utf8Text)) {
        encodingCache.set(filePath, {encoding: 'utf8', content: utf8Text});
        return 'utf8';
      }
      
      // Fallback to GBK
      const gbkText = iconv.decode(buffer, 'gbk');
      if (!/�/.test(gbkText)) {
        encodingCache.set(filePath, {encoding: 'gbk', content: gbkText});
        return 'gbk';
      }
      
      throw new Error(`Unrecognized file encoding: ${filePath}`);
    } catch (err) {
      throw new Error(`Failed to detect encoding: ${(err as Error).message}`);
    }
  }

  private async readFileContent(filePath: string, encoding: SupportedEncoding): Promise<string> {
    const cached = encodingCache.get(filePath);
    if (cached && cached.encoding === encoding) {
      return cached.content;
    }

    const buffer = await fs.readFile(filePath);
    const content = iconv.decode(buffer, encoding);
    encodingCache.set(filePath, {encoding, content});
    return content;
  }

  private async processFile(entryPath: string, relativePath: string): Promise<FileInfo | null> {
    if (!this.isSupportedFile(entryPath)) {
      return null;
    }

    try {
      const encoding = await this.detectEncoding(entryPath);
      const content = await this.readFileContent(entryPath, encoding);
      return {
        path: entryPath,
        relativePath,
        content,
        encoding,
      };
    } catch (err) {
      logger.error(`Failed to process file ${entryPath}: ${(err as Error).message}`);
      return null;
    }
  }

  private async scanDirectory(dirPath: string, basePath: string): Promise<FileInfo[]> {
    const entries = await fs.readdir(dirPath, { withFileTypes: true });
    const fileTasks: Promise<FileInfo | null>[] = [];

    for (const entry of entries) {
      const entryPath = path.join(dirPath, entry.name);
      const relativePath = path.relative(basePath, entryPath);

      if (this.isHiddenFile(entry.name)) {
        continue;
      }

      if (entry.isDirectory()) {
        fileTasks.push(
          this.scanDirectory(entryPath, basePath)
            .then(files => files[0] || null)
        );
      } else if (entry.isFile()) {
        fileTasks.push(this.processFile(entryPath, relativePath));
      }
    }

    const results = await Promise.all(fileTasks);
    return results.filter(Boolean) as FileInfo[];
  }

  async scan(inputPath: string): Promise<FileInfo[]> {
    try {
      const stats = await fs.stat(inputPath);

      if (stats.isFile()) {
        if (!this.isSupportedFile(inputPath)) {
          throw new Error(`Unsupported file type: ${inputPath}`);
        }
        const file = await this.processFile(inputPath, path.basename(inputPath));
        return file ? [file] : [];
      } else if (stats.isDirectory()) {
        return this.scanDirectory(inputPath, inputPath);
      } else {
        throw new Error(`Invalid input path: ${inputPath}`);
      }
    } catch (err) {
      logger.error(`Scan failed: ${(err as Error).message}`);
      throw err;
    }
  }
}