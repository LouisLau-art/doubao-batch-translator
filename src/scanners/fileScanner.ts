import * as fs from 'fs/promises';
import * as path from 'path';
import * as iconv from 'iconv-lite';
import { logger } from '../utils/logger';

// Custom type for supported encodings
export type SupportedEncoding = 'utf8' | 'gbk';

export interface FileInfo {
  path: string;
  relativePath: string;
  content: string;
  encoding: SupportedEncoding;
}

export class FileScanner {
  private supportedExtensions = new Set(['.html', '.htm', '.md', '.markdown']);
  private supportedEncodings = new Set(['utf8', 'gbk']);

  /**
   * 检查文件是否为支持的类型
   * @param filePath 文件路径
   * @returns 是否为支持的类型
   */
  private isSupportedFile(filePath: string): boolean {
    const ext = path.extname(filePath).toLowerCase();
    return this.supportedExtensions.has(ext);
  }

  /**
   * 检查文件是否为隐藏文件/目录
   * @param fileName 文件名
   * @returns 是否为隐藏文件
   */
  private isHiddenFile(fileName: string): boolean {
    return fileName.startsWith('.') || fileName.startsWith('_');
  }

  /**
   * 尝试检测文件编码
   * @param filePath 文件路径
   * @returns 编码类型
   */
  private async detectEncoding(filePath: string): Promise<SupportedEncoding> {
    try {
      const buffer = await fs.readFile(filePath);
      
      // 尝试UTF-8
      const utf8Text = iconv.decode(buffer, 'utf8');
      // 检查是否包含无效字符
      if (!/�/.test(utf8Text)) {
        return 'utf8';
      }
      
      // 尝试GBK
      const gbkText = iconv.decode(buffer, 'gbk');
      if (!/�/.test(gbkText)) {
        return 'gbk' as SupportedEncoding;
      }
      
      throw new Error(`无法识别的文件编码：${filePath}`);
    } catch (err) {
      throw new Error(`检测文件编码失败：${(err as Error).message}`);
    }
  }

  /**
   * 读取文件内容（支持UTF-8和GBK）
   * @param filePath 文件路径
   * @param encoding 编码类型
   * @returns 文件内容
   */
  private async readFileContent(filePath: string, encoding: SupportedEncoding): Promise<string> {
    const buffer = await fs.readFile(filePath);
    return iconv.decode(buffer, encoding);
  }

  /**
   * 递归扫描目录
   * @param dirPath 目录路径
   * @param basePath 基准路径（用于计算相对路径）
   * @returns 文件信息列表
   */
  private async scanDirectory(dirPath: string, basePath: string): Promise<FileInfo[]> {
    const files: FileInfo[] = [];
    const entries = await fs.readdir(dirPath, { withFileTypes: true });

    for (const entry of entries) {
      const entryPath = path.join(dirPath, entry.name);
      const relativePath = path.relative(basePath, entryPath);

      // 跳过隐藏文件/目录
      if (this.isHiddenFile(entry.name)) {
        continue;
      }

      if (entry.isDirectory()) {
        // 递归扫描子目录
        const subFiles = await this.scanDirectory(entryPath, basePath);
        files.push(...subFiles);
      } else if (entry.isFile() && this.isSupportedFile(entryPath)) {
        // 处理文件
        try {
          const encoding = await this.detectEncoding(entryPath);
          const content = await this.readFileContent(entryPath, encoding);
          files.push({
            path: entryPath,
            relativePath,
            content,
            encoding,
          });
          logger.info(`扫描到文件：${relativePath}（${encoding}）`);
        } catch (err) {
          logger.error(`读取文件失败：${entryPath}，错误：${(err as Error).message}`);
        }
      }
    }

    return files;
  }

  /**
   * 扫描输入路径（支持文件或目录）
   * @param inputPath 输入路径
   * @returns 文件信息列表
   */
  async scan(inputPath: string): Promise<FileInfo[]> {
    try {
      const stats = await fs.stat(inputPath);

      if (stats.isFile()) {
        // 处理单个文件
        if (!this.isSupportedFile(inputPath)) {
          throw new Error(`不支持的文件类型：${inputPath}`);
        }

        const encoding = await this.detectEncoding(inputPath);
        const content = await this.readFileContent(inputPath, encoding);
        return [{
          path: inputPath,
          relativePath: path.basename(inputPath),
          content,
          encoding,
        }];
      } else if (stats.isDirectory()) {
        // 处理目录
        return this.scanDirectory(inputPath, inputPath);
      } else {
        throw new Error(`无效的输入路径：${inputPath}`);
      }
    } catch (err) {
      logger.error(`扫描失败：${(err as Error).message}`);
      throw err;
    }
  }
}