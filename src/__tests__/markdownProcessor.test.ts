import { processMarkdown } from '../processors/markdownProcessor';

describe('Markdown Processor Unit Tests', () => {
  // Test text content translation
  it('should translate text content of paragraphs', () => {
    const markdown = 'Hello World';
    const translate = (text: string) => text.replace('Hello', 'Bonjour');
    const result = processMarkdown(markdown, translate);
    expect(result).toContain('Bonjour World');
  });

  // Test preserving code blocks
  it('should preserve code blocks', () => {
    const markdown = '```\nconsole.log("Hello");\n```\nText';
    const translate = (text: string) => text.replace('Text', 'Translated');
    const result = processMarkdown(markdown, translate);
    expect(result).toContain('```\nconsole.log("Hello");\n```');
    expect(result).toContain('Translated');
  });

  // Test header translation
  it('should translate header content', () => {
    const markdown = '# Hello World';
    const translate = (text: string) => text.replace('Hello', 'Bonjour');
    const result = processMarkdown(markdown, translate);
    expect(result).toContain('# Bonjour World');
  });

  // Test list item translation
  it('should translate list item content', () => {
    const markdown = '- Hello\n- World';
    const translate = (text: string) => text.replace('Hello', 'Bonjour').replace('World', 'Monde');
    const result = processMarkdown(markdown, translate);
    expect(result).toContain('- Bonjour\n- Monde');
  });

  // Test nested lists
  it('should handle nested lists', () => {
    const markdown = '- Hello\n  - World';
    const translate = (text: string) => text.replace('Hello', 'Bonjour').replace('World', 'Monde');
    const result = processMarkdown(markdown, translate);
    expect(result).toContain('- Bonjour\n  - Monde');
  });

  // Test blockquote translation
  it('should translate blockquote content', () => {
    const markdown = '> Hello World';
    const translate = (text: string) => text.replace('Hello', 'Bonjour');
    const result = processMarkdown(markdown, translate);
    expect(result).toContain('> Bonjour World');
  });
});