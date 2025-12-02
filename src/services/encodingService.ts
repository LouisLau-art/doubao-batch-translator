import fs from 'fs/promises';
import iconv from 'iconv-lite';
import { encodingCache } from './encodingCache';

/**
 * Encoding service for handling different character encodings (UTF-8, GBK)
 */
export class EncodingService {
  private textDecoder = new TextDecoder('utf-8');
  private gbkDecoder = new TextDecoder('gbk');

  /**
   * Read file with specified encoding and convert to UTF-8
   * @param filePath Path to file
   * @param encoding File encoding (default: utf-8)
   * @returns File content in UTF-8
   */
  async readFile(filePath: string, encoding: string = 'utf-8'): Promise<string> {
    // Check cache first
    const cached = encodingCache.get(filePath);
    if (cached && cached.encoding === encoding) {
      return cached.content;
    }

    const buffer = await fs.readFile(filePath);
    const encodingLower = encoding.toLowerCase();
    
    if (encodingLower === 'utf-8') {
      const content = this.textDecoder.decode(buffer);
      encodingCache.set(filePath, {encoding, content});
      return content;
    }
    
    if (encodingLower === 'gbk') {
      try {
        const content = this.gbkDecoder.decode(buffer);
        encodingCache.set(filePath, {encoding, content});
        return content;
      } catch {
        // Fallback to iconv-lite if TextDecoder fails
        const content = iconv.decode(buffer, 'gbk');
        encodingCache.set(filePath, {encoding, content});
        return content;
      }
    }
    
    if (iconv.encodingExists(encoding)) {
      const content = iconv.decode(buffer, encoding);
      encodingCache.set(filePath, {encoding, content});
      return content;
    }
    
    throw new Error(`Unsupported encoding: ${encoding}`);
  }

  /**
   * Write file with specified encoding
   * @param filePath Path to file
   * @param content Content to write (UTF-8)
   * @param encoding Target encoding (default: utf-8)
   */
  async writeFile(filePath: string, content: string, encoding: string = 'utf-8'): Promise<void> {
    let buffer: Buffer;
    const encodingLower = encoding.toLowerCase();
    
    if (encodingLower === 'utf-8') {
      buffer = Buffer.from(content, 'utf-8');
    } else if (encodingLower === 'gbk') {
      buffer = Buffer.from(new TextEncoder().encode(content));
    } else if (iconv.encodingExists(encoding)) {
      buffer = iconv.encode(content, encoding);
    } else {
      throw new Error(`Unsupported encoding: ${encoding}`);
    }
    
    await fs.writeFile(filePath, buffer);
  }

  /**
   * Convert text between encodings
   * @param text Input text
   * @param fromEncoding Source encoding
   * @param toEncoding Target encoding
   * @returns Converted text
   */
  convertEncoding(text: string, fromEncoding: string, toEncoding: string): string {
    const fromLower = fromEncoding.toLowerCase();
    const toLower = toEncoding.toLowerCase();
    
    if (fromLower === 'utf-8' && toLower === 'gbk') {
      return Buffer.from(new TextEncoder().encode(text)).toString('binary');
    } else if (fromLower === 'gbk' && toLower === 'utf-8') {
      return this.gbkDecoder.decode(Buffer.from(text, 'binary'));
    }
    
    if (!iconv.encodingExists(fromEncoding) || !iconv.encodingExists(toEncoding)) {
      throw new Error(`Unsupported encoding: ${fromEncoding} or ${toEncoding}`);
    }
    
    const buffer = iconv.encode(text, fromEncoding);
    return iconv.decode(buffer, toEncoding);
  }
}

// Singleton instance
export const encodingService = new EncodingService();