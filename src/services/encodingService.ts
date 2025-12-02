import fs from 'fs/promises';
import iconv from 'iconv-lite';

/**
 * Encoding service for handling different character encodings (UTF-8, GBK)
 */
export class EncodingService {
  /**
   * Read file with specified encoding and convert to UTF-8
   * @param filePath Path to file
   * @param encoding File encoding (default: utf-8)
   * @returns File content in UTF-8
   */
  async readFile(filePath: string, encoding: string = 'utf-8'): Promise<string> {
    const buffer = await fs.readFile(filePath);
    
    if (encoding.toLowerCase() === 'utf-8') {
      return buffer.toString('utf-8');
    }
    
    if (iconv.encodingExists(encoding)) {
      return iconv.decode(buffer, encoding);
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
    
    if (encoding.toLowerCase() === 'utf-8') {
      buffer = Buffer.from(content, 'utf-8');
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
    if (!iconv.encodingExists(fromEncoding) || !iconv.encodingExists(toEncoding)) {
      throw new Error(`Unsupported encoding: ${fromEncoding} or ${toEncoding}`);
    }
    
    const buffer = iconv.encode(text, fromEncoding);
    return iconv.decode(buffer, toEncoding);
  }
}

// Singleton instance
export const encodingService = new EncodingService();