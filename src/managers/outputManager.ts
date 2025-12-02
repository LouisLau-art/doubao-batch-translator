import * as fs from 'fs/promises';
import * as path from 'path';
import * as iconv from 'iconv-lite';
import { logger } from '../utils/logger';
import { SupportedEncoding } from '../scanners/fileScanner';

interface OutputFile {
  relativePath: string;
  content: string;
  encoding: SupportedEncoding;
}

export class OutputManager {
  private outputDir: string;
  private dryRun: boolean;

  constructor(outputDir: string, dryRun: boolean = false) {
    this.outputDir = outputDir;
    this.dryRun = dryRun;
  }

  /**
   * 创建输出目录（如果不存在）
   */
  private async createOutputDir(): Promise<void> {
    try {
      await fs.access(this.outputDir);
    } catch (err) {
      await fs.mkdir(this.outputDir, { recursive: true });
      logger.info(`创建输出目录：${this.outputDir}`);
    }
  }

  /**
   * 获取输出文件的绝对路径
   * @param relativePath 相对路径
   * @returns 绝对路径
   */
  private getOutputPath(relativePath: string): string {
    return path.join(this.outputDir, relativePath);
  }

  /**
   * 写入文件（支持dry-run模式）
   * @param file 输出文件信息
   */
  async writeFile(file: OutputFile): Promise<void> {
    const outputPath = this.getOutputPath(file.relativePath);
    const outputDir = path.dirname(outputPath);

    // 创建输出目录
    await this.createOutputDir();

    if (this.dryRun) {
      // dry-run模式：只显示变化
      logger.info(`[DRY RUN] 翻译文件：${file.relativePath}`);
      logger.info(`[DRY RUN] 输出内容（前50字符）：${file.content.slice(0, 50)}...`);
      return;
    }

    // 实际写入文件
    try {
      const buffer = iconv.encode(file.content, file.encoding);
      await fs.writeFile(outputPath, buffer);
      logger.info(`写入文件成功：${file.relativePath}（${file.encoding}）`);
    } catch (err) {
      logger.error(`写入文件失败：${file.relativePath}，错误：${(err as Error).message}`);
      throw err;
    }
  }

  /**
   * 批量写入文件
   * @param files 输出文件列表
   */
  async writeFiles(files: OutputFile[]): Promise<void> {
    for (const file of files) {
      await this.writeFile(file);
    }
  }
}