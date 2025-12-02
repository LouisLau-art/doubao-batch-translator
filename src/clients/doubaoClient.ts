import axios from 'axios';
import dotenv from 'dotenv';
import tiktoken from 'tiktoken';
import { logger } from '../utils/logger';

// Load environment variables
dotenv.config();

// Supported languages from user's instructions
const VALID_LANGUAGES = new Set([
  'zh', 'zh-Hant', 'en', 'ja', 'ko', 'de', 'fr', 'es', 'it', 'pt', 'ru',
  'th', 'vi', 'ar', 'cs', 'da', 'fi', 'hr', 'hu', 'id', 'ms', 'nb', 'nl',
  'pl', 'ro', 'sv', 'tr', 'uk'
]);

interface DoubaoRequest {
  model: string;
  input: Array<{
    role: 'user';
    content: Array<{
      type: 'input_text';
      text: string;
      translation_options: {
        source_language?: string;
        target_language: string;
      };
    }>;
  }>;
}

interface DoubaoResponse {
  output: Array<{
    role: 'assistant';
    content: Array<{
      type: 'text';
      text: string;
    }>;
  }>;
}

export class DoubaoClient {
  private apiKey: string;
  private apiEndpoint: string;
  private defaultModel: string;
  private maxInputTokens = 1000; // Doubao input limit
  private maxRetries = 3;
  private retryDelay = 1000; // Initial delay in ms
  private cache = new Map<string, string>(); // In-memory cache for translations

  constructor() {
    this.apiKey = process.env.ARK_API_KEY || '';
    this.apiEndpoint = process.env.API_ENDPOINT || 'https://ark.cn-beijing.volces.com/api/v3/responses';
    this.defaultModel = process.env.DEFAULT_MODEL || 'doubao-seed-translation-250915';

    if (!this.apiKey) {
      throw new Error('ARK_API_KEY not found in environment variables');
    }
  }

  /**
   * Check if text exceeds the maximum input tokens
   * @param text Text to check
   * @returns True if exceeds, false otherwise
   */
  private encoder = tiktoken.get_encoding('cl100k_base');

  private countTokens(text: string): number {
    return this.encoder.encode(text).length;
  }

  private exceedsTokenLimit(text: string): boolean {
    return this.countTokens(text) > this.maxInputTokens;
  }

  /**
   * Split text into chunks that fit within the token limit
   * @param text Text to split
   * @returns Array of text chunks
   */
  private splitTextIntoChunks(text: string): string[] {
    const chunks: string[] = [];
    let currentChunk = '';
    const words = text.split(/\s+/);

    for (const word of words) {
      const tempChunk = currentChunk ? `${currentChunk} ${word}` : word;
      if (this.countTokens(tempChunk) <= this.maxInputTokens) {
        currentChunk = tempChunk;
      } else {
        chunks.push(currentChunk);
        currentChunk = word;
      }
    }

    if (currentChunk) {
      chunks.push(currentChunk);
    }

    return chunks;
  }

  /**
   * Send request to Doubao API with retries
   * @param request Request body
   * @returns Response from API
   */
  private async sendRequest(request: DoubaoRequest): Promise<DoubaoResponse> {
    for (let retry = 0; retry < this.maxRetries; retry++) {
      try {
        const response = await axios.post<DoubaoResponse>(this.apiEndpoint, request, {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json',
          },
        });
        return response.data;
      } catch (error) {
        logger.error(`Request failed (retry ${retry + 1}/${this.maxRetries}): ${(error as Error).message}`);
        if (retry === this.maxRetries - 1) {
          throw error;
        }
        await new Promise(resolve => setTimeout(resolve, this.retryDelay * Math.pow(2, retry)));
      }
    }

    throw new Error('Max retries exceeded');
  }

  /**
   * Translate text using Doubao API
   * @param text Text to translate
   * @param sourceLang Source language (optional)
   * @param targetLang Target language
   * @returns Translated text
   */
  async translate(text: string, sourceLang?: string, targetLang: string = 'en'): Promise<string> {
    // Validate languages
    if (!VALID_LANGUAGES.has(targetLang)) {
      throw new Error(`Invalid target language: ${targetLang}. Supported languages: ${Array.from(VALID_LANGUAGES).join(', ')}`);
    }
    if (sourceLang && !VALID_LANGUAGES.has(sourceLang)) {
      throw new Error(`Invalid source language: ${sourceLang}. Supported languages: ${Array.from(VALID_LANGUAGES).join(', ')}`);
    }

    // Check cache first
    const cacheKey = `${sourceLang || 'auto'}-${targetLang}-${text}`;
    if (this.cache.has(cacheKey)) {
      logger.info('Using cached translation');
      return this.cache.get(cacheKey) || '';
    }

    // Check token limit
    if (this.exceedsTokenLimit(text)) {
      logger.warn('Text exceeds token limit, splitting into chunks');
      const chunks = this.splitTextIntoChunks(text);
      const translatedChunks = await Promise.all(
        chunks.map(chunk => this.translate(chunk, sourceLang, targetLang))
      );
      const translatedText = translatedChunks.join(' ');
      this.cache.set(cacheKey, translatedText);
      return translatedText;
    }

    // Prepare request
    const request: DoubaoRequest = {
      model: this.defaultModel,
      input: [
        {
          role: 'user',
          content: [
            {
              type: 'input_text',
              text: text,
              translation_options: {
                ...(sourceLang && { source_language: sourceLang }),
                target_language: targetLang,
              },
            },
          ],
        },
      ],
    };

    try {
      logger.info(`Sending translation request to Doubao`);
      const response = await this.sendRequest(request);
      const translatedText = response.output[0]?.content[0]?.text || '';
      this.cache.set(cacheKey, translatedText);
      return translatedText;
    } catch (error) {
      logger.error(`Translation failed: ${(error as Error).message}`);
      throw error;
    }
  }

  /**
   * Clear the translation cache
   */
  clearCache(): void {
    this.cache.clear();
    logger.info('Translation cache cleared');
  }
}