import { logger } from '../utils/logger';

// Mock translation responses for testing
const MOCK_TRANSLATIONS: Record<string, string> = {
  'Welcome to the Translation Test': '欢迎来到翻译测试',
  'This is a sample HTML file for testing the batch translation functionality.': '这是一个用于测试批量翻译功能的示例HTML文件。',
  'It contains various elements that should be translated:': '它包含各种应该被翻译的元素：',
  'Paragraphs with text content': '带有文本内容的段落',
  'List items like this one': '像这样的列表项',
  'An image with alt text': '带有alt文本的图像',
  'Company Logo': '公司标志',
  'Code blocks should be preserved without translation': '代码块应该被保留而不进行翻译',
  'Footer content with contact information': '带有联系信息的页脚内容',
  'Sample Markdown for Translation': '示例Markdown用于翻译',
  'Text Elements to Translate': '要翻译的文本元素',
  'Headers at various levels': '各种级别的标题',
  'Blockquotes:': '块引用：',
  'This is a blockquote that should be translated': '这是一个应该被翻译的块引用',
  'Code Preservation': '代码保留',
  'Inline Elements': '内联元素',
  'Language-Specific Features': '语言特定功能',
  'HTML within Markdown should be handled correctly': 'Markdown中的HTML应该被正确处理',
  'This is an HTML div within Markdown that should be translated.': '这是Markdown中的一个HTML div，应该被翻译。'
};

export class MockDoubaoClient {
  private delay = 100; // Simulate API delay in ms

  /**
   * Mock translation function that returns pre-defined translations
   * @param text Text to translate
   * @param sourceLang Source language (ignored in mock)
   * @param targetLang Target language (ignored in mock)
   * @returns Mock translated text
   */
  async translate(text: string, sourceLang?: string, targetLang: string = 'en'): Promise<string> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, this.delay));
    
    // Return mock translation if available, otherwise return original text with marker
    const mockTranslation = MOCK_TRANSLATIONS[text] || `[MOCK TRANSLATED] ${text}`;
    
    logger.info(`Mock translation: "${text.slice(0, 50)}..." -> "${mockTranslation.slice(0, 50)}..."`);
    return mockTranslation;
  }

  /**
   * Set mock API delay for testing
   * @param delay Delay in milliseconds
   */
  setDelay(delay: number): void {
    this.delay = delay;
  }

  /**
   * Clear the mock cache (no-op for mock client)
   */
  clearCache(): void {
    logger.info('Mock cache cleared (no-op)');
  }
}