import { processHtml } from '../processors/htmlProcessor';

describe('HTML Processor Unit Tests', () => {
  // Test text content translation
  it('should translate text content of elements', () => {
    const html = '<div>Hello World</div>';
    const translate = (text: string) => text.replace('Hello', 'Bonjour');
    const result = processHtml(html, translate);
    expect(result).toContain('<div>Bonjour World</div>');
  });

  // Test alt attribute translation
  it('should translate alt attribute of img elements', () => {
    const html = '<img src="image.jpg" alt="Hello" />';
    const translate = (text: string) => text.replace('Hello', 'Bonjour');
    const result = processHtml(html, translate);
    expect(result).toContain('alt="Bonjour"');
  });

  // Test title attribute translation
  it('should translate title attribute of elements', () => {
    const html = '<span title="Hello">Content</span>';
    const translate = (text: string) => text.replace('Hello', 'Bonjour');
    const result = processHtml(html, translate);
    expect(result).toContain('title="Bonjour"');
  });

  // Test aria-label attribute translation
  it('should translate aria-label attribute', () => {
    const html = '<button aria-label="Hello">Click Me</button>';
    const translate = (text: string) => text.replace('Hello', 'Bonjour');
    const result = processHtml(html, translate);
    expect(result).toContain('aria-label="Bonjour"');
  });

  // Test preserving non-text elements (like code blocks in HTML)
  it('should preserve non-text elements', () => {
    const html = '<div><code><div>Code</div></code> Text</div>';
    const translate = (text: string) => text.replace('Text', 'Translated');
    const result = processHtml(html, translate);
    expect(result).toContain('<code><div>Code</div></code>');
    expect(result).toContain('Translated');
  });

  // Test nested elements
  it('should handle nested elements', () => {
    const html = '<div><p>Hello <strong>World</strong></p></div>';
    const translate = (text: string) => text.replace('Hello', 'Bonjour').replace('World', 'Monde');
    const result = processHtml(html, translate);
    expect(result).toContain('<div><p>Bonjour <strong>Monde</strong></p></div>');
  });
});