import { JSDOM } from 'jsdom';
import * as nodejieba from 'nodejieba';
import { get_encoding } from 'tiktoken';
import { DoubaoClient } from '../clients/doubaoClient';
import { logger } from '../utils/logger';

// 加载nodejieba词典
nodejieba.load({
  dict: require.resolve('nodejieba/dict/jieba.dict.utf8'),
  hmmDict: require.resolve('nodejieba/dict/hmm_model.utf8'),
  userDict: require.resolve('nodejieba/dict/user.dict.utf8'),
  idfDict: require.resolve('nodejieba/dict/idf.utf8'),
  stopWordDict: require.resolve('nodejieba/dict/stop_words.utf8'),
});

interface TextSegment {
  text: string;
  position: {
    type: 'node' | 'attribute';
    node: Node | Element;
    attribute?: string;
  };
}

interface TranslatedSegment {
  original: string;
  translated: string;
  position: TextSegment['position'];
}

export class HTMLProcessor {
  private doubaoClient: DoubaoClient;
  private maxTokenPerSegment = 900; // Doubao输入限制1k，预留100token上下文

  constructor(doubaoClient: DoubaoClient) {
    this.doubaoClient = doubaoClient;
  }

  /**
   * 解析HTML字符串为DOM结构
   * @param html HTML字符串
   * @returns DOM文档
   */
  private parseHTML(html: string): Document {
    const dom = new JSDOM(html);
    return dom.window.document;
  }

  /**
   * 提取需要翻译的文本（节点文本 + 属性值）
   * @param document DOM文档
   * @returns 文本片段列表
   */
  private extractText(document: Document): TextSegment[] {
    const segments: TextSegment[] = [];

    // 递归遍历DOM树提取文本节点
    const traverse = (node: Node) => {
      // 跳过不需要翻译的元素
      if (node.nodeType === node.ELEMENT_NODE) {
        const element = node as Element;
        const tagName = element.tagName.toLowerCase();
        
        // 跳过script、style、code、pre元素
        if (['script', 'style', 'code', 'pre'].includes(tagName)) {
          return;
        }

        // 提取需要翻译的属性（alt、title、aria-label）
        const attributeNames = ['alt', 'title', 'aria-label'];
        attributeNames.forEach(attrName => {
          const value = element.getAttribute(attrName)?.trim();
          if (value) {
            segments.push({
              text: value,
              position: {
                type: 'attribute',
                node: element,
                attribute: attrName,
              },
            });
          }
        });
      }

      // 处理文本节点
      if (node.nodeType === node.TEXT_NODE) {
        const text = node.textContent?.trim();
        if (text && text.length > 0) {
          segments.push({
            text: text,
            position: {
              type: 'node',
              node,
            },
          });
        }
        return;
      }

      // 递归处理子节点
      node.childNodes.forEach(traverse);
    };

    traverse(document.body || document.documentElement);
    return segments;
  }

  /**
   * 中文分词 + token分割（控制在maxTokenPerSegment以内）
   * @param text 原始文本
   * @returns 分割后的文本片段
   */
  private segmentText(text: string): string[] {
    // 中文分词
    const words = nodejieba.cut(text);
    const wordList = words.filter(word => word.trim() !== '');

    // 使用tiktoken计算token数并分割
    const encoder = get_encoding('cl100k_base');
    const segments: string[] = [];
    let currentSegment = '';
    let currentTokenCount = 0;

    for (const word of wordList) {
      const wordTokens = encoder.encode(word);
      const wordTokenCount = wordTokens.length;
      
      if (currentTokenCount + wordTokenCount > this.maxTokenPerSegment) {
        if (currentSegment) {
          segments.push(currentSegment);
          currentSegment = '';
          currentTokenCount = 0;
        }
        // 单个单词超过限制，强制分割（极端情况）
        segments.push(word);
        currentTokenCount = wordTokenCount;
      } else {
        currentSegment += word;
        currentTokenCount += wordTokenCount;
      }
    }

    if (currentSegment) {
      segments.push(currentSegment);
    }

    return segments;
  }

  /**
   * 翻译文本片段
   * @param segments 文本片段列表
   * @param sourceLang 源语言
   * @param targetLang 目标语言
   * @returns 翻译后的片段列表
   */
  private async translateSegments(
    segments: TextSegment[],
    sourceLang: string,
    targetLang: string
  ): Promise<TranslatedSegment[]> {
    const translated: TranslatedSegment[] = [];
    const maxRetries = 3; // 最大重试次数
    const initialDelay = 1000; // 初始重试延迟（毫秒）

    for (const segment of segments) {
      let translatedText = segment.text;
      let success = false;

      for (let retry = 0; retry < maxRetries; retry++) {
        try {
          const delay = initialDelay * Math.pow(2, retry); // 指数退避
          if (retry > 0) {
            logger.info(`正在重试翻译文本：${segment.text.slice(0,50)}...（第${retry+1}次，延迟${delay}ms）`);
            await new Promise(resolve => setTimeout(resolve, delay));
          } else {
            logger.info(`正在翻译文本：${segment.text.slice(0,50)}...`);
          }

          translatedText = await this.doubaoClient.translate(
            segment.text,
            sourceLang,
            targetLang
          );
          success = true;
          break; // 成功则退出重试循环
        } catch (error) {
          const errorMsg = (error as Error).message;
          if (retry === maxRetries -1) {
            logger.error(`翻译失败（已达最大重试次数）：${segment.text.slice(0,50)}...，错误：${errorMsg}`);
          } else {
            logger.warn(`翻译失败，将重试：${segment.text.slice(0,50)}...，错误：${errorMsg}`);
          }
        }
      }

      translated.push({
        original: segment.text,
        translated: translatedText,
        position: segment.position,
      });
    }

    return translated;
  }

  /**
   * 重构DOM结构（替换翻译后的文本）
   * @param document DOM文档
   * @param translatedSegments 翻译后的片段列表
   */
  private reconstructDOM(
    document: Document,
    translatedSegments: TranslatedSegment[]
  ): void {
    translatedSegments.forEach(segment => {
      const { position, translated } = segment;
      if (position.type === 'node') {
        (position.node as Text).textContent = translated;
      } else if (position.type === 'attribute' && position.attribute) {
        (position.node as Element).setAttribute(position.attribute, translated);
      }
    });
  }

  /**
   * 序列化DOM为HTML字符串
   * @param document DOM文档
   * @returns HTML字符串
   */
  private serializeHTML(document: Document): string {
    return document.documentElement.outerHTML;
  }

  /**
   * 处理HTML翻译（完整流程）
   * @param html HTML字符串
   * @param sourceLang 源语言
   * @param targetLang 目标语言
   * @returns 翻译后的HTML字符串
   */
  async process(
    html: string,
    sourceLang: string,
    targetLang: string
  ): Promise<string> {
    try {
      // 1. 解析HTML
      const document = this.parseHTML(html);

      // 2. 提取文本
      const textSegments = this.extractText(document);
      if (textSegments.length === 0) {
        logger.info('HTML中无需要翻译的文本');
        return html;
      }

      // 3. 翻译文本
      const translatedSegments = await this.translateSegments(
        textSegments,
        sourceLang,
        targetLang
      );

      // 4. 重构DOM
      this.reconstructDOM(document, translatedSegments);

      // 5. 序列化HTML
      const translatedHTML = this.serializeHTML(document);

      logger.info('HTML翻译完成');
      return translatedHTML;
    } catch (error) {
      logger.error(`HTML处理失败：${(error as Error).message}`);
      throw error;
    }
  }
}