import { DoubaoClient } from '../clients/doubaoClient';
import axios from 'axios';
import tiktoken from 'tiktoken';

// Mock external dependencies
jest.mock('axios');
jest.mock('tiktoken');

describe('DoubaoClient Unit Tests', () => {
  let client: DoubaoClient;
  const mockAxios = axios as jest.Mocked<typeof axios>;
  const mockTiktoken = tiktoken as jest.Mocked<typeof tiktoken>;

  beforeEach(() => {
    // Set environment variables for testing
    process.env.ARK_API_KEY = 'test_api_key';
    process.env.API_ENDPOINT = 'https://test.api';
    process.env.DEFAULT_MODEL = 'test_model';

    // Mock tiktoken encoder to control token counting
    const mockEncoder = {
      encode: jest.fn((text: string) => {
        // Simulate token count: 1 token per 4 characters
        return Array(Math.ceil(text.length / 4)).fill(0);
      }),
    };
    mockTiktoken.get_encoding.mockReturnValue(mockEncoder as any);

    // Mock API response
    mockAxios.post.mockResolvedValue({
      data: {
        output: [
          {
            role: 'assistant',
            content: [
              {
                type: 'text',
                text: 'Translated text',
              },
            ],
          },
        ],
      },
    });

    // Initialize client
    client = new DoubaoClient();
  });

  afterEach(() => {
    // Clear mocks and environment variables
    jest.clearAllMocks();
    delete process.env.ARK_API_KEY;
    delete process.env.API_ENDPOINT;
    delete process.env.DEFAULT_MODEL;
  });

  it('should translate text and use cache for subsequent requests', async () => {
    const text = 'Hello World';
    const sourceLang = 'en';
    const targetLang = 'zh';

    // First translation (should call API)
    const result1 = await client.translate(text, sourceLang, targetLang);
    expect(result1).toBe('Translated text');
    expect(mockAxios.post).toHaveBeenCalledTimes(1);

    // Second translation (should use cache)
    const result2 = await client.translate(text, sourceLang, targetLang);
    expect(result2).toBe('Translated text');
    expect(mockAxios.post).toHaveBeenCalledTimes(1); // No additional API call
    expect(client['cache'].has(`${sourceLang}-${targetLang}-${text}`)).toBe(true);
  });

  it('should split large text into chunks and translate', async () => {
    // Mock token count to exceed limit (1000 tokens)
    const mockEncoder = {
      encode: jest.fn(() => Array(1001).fill(0)), // Exceeds maxInputTokens (1000)
    };
    mockTiktoken.get_encoding.mockReturnValue(mockEncoder as any);

    // Create a text that will be split into 2 chunks
    const longText = 'a '.repeat(2000); // 4000 characters (2000 "a ")
    const sourceLang = 'en';
    const targetLang = 'zh';

    const result = await client.translate(longText, sourceLang, targetLang);
    expect(result).toBe('Translated text Translated text'); // Two chunks translated
    expect(mockAxios.post).toHaveBeenCalledTimes(2); // Two API calls
  });

  it('should throw error for invalid target language', async () => {
    const text = 'Hello';
    const sourceLang = 'en';
    const targetLang = 'invalid';

    await expect(client.translate(text, sourceLang, targetLang)).rejects.toThrow(
      'Invalid target language: invalid'
    );
  });

  it('should throw error for invalid source language', async () => {
    const text = 'Hello';
    const sourceLang = 'invalid';
    const targetLang = 'zh';

    await expect(client.translate(text, sourceLang, targetLang)).rejects.toThrow(
      'Invalid source language: invalid'
    );
  });
});