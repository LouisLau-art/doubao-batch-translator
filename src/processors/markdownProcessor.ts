import * as marked from 'marked';
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

// 定义文本片段接口（包含位置信息）
interface TextSegment {
  text: string;
  position: {
    type: 'node';
    node: marked.Token;
    key: string; // 需要更新的属性名（如'text'、'alt'）
  };
}

// 定义翻译后的片段接口
interface TranslatedSegment {
  original: string;
  translated: string;
  position: TextSegment['position'];
}

export class MarkdownProcessor {
  private doubaoClient: DoubaoClient;
  private maxTokenPerSegment = 900; // 预留100token上下文

  constructor(doubaoClient: DoubaoClient) {
    this.doubaoClient = doubaoClient;
  }

  /**
   * 解析Markdown字符串为AST
   * @param markdown Markdown字符串
   * @returns Markdown AST
   */
  private parseMarkdown(markdown: string): marked.Token[] {
    const lexer = new marked.Lexer();
    return lexer.lex(markdown);
  }

  /**
   * 提取需要翻译的文本片段
   * @param tokens Markdown AST
   * @returns 文本片段列表
   */
  private extractText(tokens: marked.Token[]): TextSegment[] {
    const segments: TextSegment[] = [];

    // 递归遍历AST节点
    const traverse = (node: marked.Token) => {
      // 跳过代码块和内联代码
      if (node.type === 'code' || node.type === 'codespan') return;

      // 处理文本节点
      if (node.type === 'text') {
        segments.push({
          text: node.text.trim(),
          position: {
            type: 'node',
            node,
            key: 'text',
          },
        });
        return;
      }

      // 处理标题、段落、列表项等包含文本的节点
      // Handle heading tokens
      if (node.type === 'heading') {
        segments.push({
          text: (node as marked.Tokens.Heading).text.trim(),
          position: {
            type: 'node',
            node,
            key: 'text',
          },
        });
      }
      
      // Handle paragraph tokens
      if (node.type === 'paragraph') {
        segments.push({
          text: (node as marked.Tokens.Paragraph).text.trim(),
          position: {
            type: 'node',
            node,
            key: 'text',
          },
        });
      }
      
      // Handle list item tokens
      if (node.type === 'list_item') {
        segments.push({
          text: (node as marked.Tokens.ListItem).text.trim(),
          position: {
            type: 'node',
            node,
            key: 'text',
          },
        });
      }
      
      // Handle blockquote tokens
      if (node.type === 'blockquote') {
        segments.push({
          text: (node as marked.Tokens.Blockquote).text.trim(),
          position: {
            type: 'node',
            node,
            key: 'text',
          },
        });
      }

      // Handle image tokens
      if (node.type === 'image') {
        const imgNode = node as marked.Tokens.Image;
        segments.push({
          text: imgNode.text.trim(), // 'text' contains the alt text
          position: {
            type: 'node',
            node,
            key: 'text',
          },
        });
      }

      // Handle link tokens
      if (node.type === 'link') {
        const linkNode = node as marked.Tokens.Link;
        segments.push({
          text: linkNode.text.trim(),
          position: {
            type: 'node',
            node,
            key: 'text',
          },
        });
      }

      // Recursively process tokens
      if ('tokens' in node && node.tokens) {
        (node.tokens as marked.Token[]).forEach(traverse);
      }
    };

    tokens.forEach(traverse);
    return segments;
  }

  /**
   * 文本分段处理（中文分词+Token分割）
   * @param text 原始文本
   * @returns 分段后的文本列表
   */
  private segmentText(text: string): string[] {
    // 中文分词
    const words = nodejieba.cut(text);
    const wordList = words.filter(word => word.trim() !== '');

    // Token分割
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
        // 单个单词超过限制时强制分割
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
   * 翻译文本片段（带重试机制）
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
    const maxRetries = 3;
    const initialDelay = 1000;

    for (const segment of segments) {
      let translatedText = segment.text;
      let success = false;

      for (let retry = 0; retry < maxRetries; retry++) {
        try {
          const delay = initialDelay * Math.pow(2, retry);
          if (retry > 0) {
            logger.info(`重试翻译Markdown文本：${segment.text.slice(0,50)}...（第${retry+1}次，延迟${delay}ms）`);
            await new Promise(resolve => setTimeout(resolve, delay));
          } else {
            logger.info(`翻译Markdown文本：${segment.text.slice(0,50)}...`);
          }

          translatedText = await this.doubaoClient.translate(
            segment.text,
            sourceLang,
            targetLang
          );
          success = true;
          break;
        } catch (error) {
          const errorMsg = (error as Error).message;
          if (retry === maxRetries -1) {
            logger.error(`Markdown翻译失败（已达最大重试次数）：${segment.text.slice(0,50)}...，错误：${errorMsg}`);
          } else {
            logger.warn(`Markdown翻译失败，将重试：${segment.text.slice(0,50)}...，错误：${errorMsg}`);
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
   * 重构Markdown AST（替换翻译后的文本）
   * @param tokens Markdown AST
   * @param translatedSegments 翻译后的片段列表
   */
  private reconstructMarkdown(
    tokens: marked.Token[],
    translatedSegments: TranslatedSegment[]
  ): void {
    translatedSegments.forEach(segment => {
      const { position, translated } = segment;
      if (position.type === 'node' && position.node[position.key as keyof marked.Token]) {
        (position.node as any)[position.key] = translated;
      }
    });
  }

  /**
   * 序列化AST为Markdown字符串
   * @param tokens Markdown AST
   * @returns Markdown字符串
   */
  private serializeMarkdown(tokens: marked.Token[]): string {
    const parser = new marked.Parser();
    return parser.parse(tokens);
  }

  /**
   * 处理Markdown翻译完整流程
   * @param markdown Markdown字符串
   * @param sourceLang 源语言
   * @param targetLang 目标语言
   * @returns 翻译后的Markdown字符串
   */
  async process(
    markdown: string,
    sourceLang: string,
    targetLang: string
  ): Promise<string> {
    try {
      // 1. 解析Markdown为AST
      const tokens = this.parseMarkdown(markdown);

      // 2. 提取文本片段
      const textSegments = this.extractText(tokens);
      if (textSegments.length === 0) {
        logger.info('Markdown中无需要翻译的文本');
        return markdown;
      }

      // 3. 翻译文本片段
      const translatedSegments = await this.translateSegments(
        textSegments,
        sourceLang,
        targetLang
      );

      // 4. 重构Markdown AST
      this.reconstructMarkdown(tokens, translatedSegments);

      // 5. 序列化AST为Markdown
      const translatedMarkdown = this.serializeMarkdown(tokens);

      logger.info('Markdown翻译完成');
      return translatedMarkdown;
    } catch (error) {
      logger.error(`Markdown处理失败：${(error as Error).message}`);
      throw error;
    }
  }
}