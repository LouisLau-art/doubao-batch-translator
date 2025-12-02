import { HTMLProcessor } from '../htmlProcessor';
import { JSDOM } from 'jsdom';
import { DoubaoClient } from '../../clients/doubaoClient';

// Mock DoubaoClient
jest.mock('../../clients/doubaoClient');
const MockDoubaoClient = DoubaoClient as jest.MockedClass<typeof DoubaoClient>;

describe('HTMLProcessor', () => {
  let htmlProcessor: HTMLProcessor;
  let mockDoubaoClient: jest.Mocked<DoubaoClient>;

  beforeEach(() => {
    mockDoubaoClient = new MockDoubaoClient() as jest.Mocked<DoubaoClient>;
    htmlProcessor = new HTMLProcessor(mockDoubaoClient);
  });

  describe('parseHTML', () => {
    it('should parse HTML string into DOM document', () => {
      const html = '<html><body><h1>Test</h1></body></html>';
      const document = htmlProcessor['parseHTML'](html);
      expect(document.querySelector('h1')?.textContent).toBe('Test');
    });
  });

  describe('extractText', () => {
    it('should extract text nodes and attributes', () => {
      const html = `
        <html>
          <body>
            <h1>Hello World</h1>
            <img src="test.jpg" alt="Test Image">
            <div title="Test Title">Content</div>
          </body>
        </html>
      `;
      const document = new JSDOM(html).window.document;
      const segments = htmlProcessor['extractText'](document);
      
      expect(segments.length).toBe(3);
      expect(segments[0].text).toBe('Hello World');
      expect(segments[1].text).toBe('Test Image');
      expect(segments[2].text).toBe('Test Title');
    });
  });

  describe('segmentText', () => {
    it('should split text into chunks within token limit', () => {
      const longText = 'a '.repeat(1000); // Long text exceeding token limit
      const segments = htmlProcessor['segmentText'](longText);
      expect(segments.length).toBeGreaterThan(1);
    });
  });

  describe('translateSegments', () => {
    it('should translate segments using DoubaoClient', async () => {
      const segments = [
        { text: 'Hello', position: { type: 'node', node: {} as Node } },
        { text: 'World', position: { type: 'node', node: {} as Node } }
      ];
      mockDoubaoClient.translate.mockResolvedValueOnce('Hola').mockResolvedValueOnce('Mundo');
      
      const translated = await htmlProcessor['translateSegments'](segments, 'en', 'es');
      
      expect(translated.length).toBe(2);
      expect(translated[0].translated).toBe('Hola');
      expect(translated[1].translated).toBe('Mundo');
    });
  });

  describe('reconstructDOM', () => {
    it('should replace text nodes and attributes with translated content', () => {
      const html = '<html><body><h1>Hello</h1><img alt="Test"></body></html>';
      const document = new JSDOM(html).window.document;
      const translatedSegments = [
        { original: 'Hello', translated: 'Hola', position: { type: 'node', node: document.querySelector('h1')?.firstChild! } },
        { original: 'Test', translated: 'Prueba', position: { type: 'attribute', node: document.querySelector('img')!, attribute: 'alt' } }
      ];
      
      htmlProcessor['reconstructDOM'](document, translatedSegments);
      
      expect(document.querySelector('h1')?.textContent).toBe('Hola');
      expect(document.querySelector('img')?.getAttribute('alt')).toBe('Prueba');
    });
  });

  describe('serializeHTML', () => {
    it('should serialize DOM to HTML string', () => {
      const html = '<html><body><h1>Test</h1></body></html>';
      const document = new JSDOM(html).window.document;
      const serialized = htmlProcessor['serializeHTML'](document);
      expect(serialized).toContain('<h1>Test</h1>');
    });
  });
});