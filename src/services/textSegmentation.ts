import jieba from 'nodejieba';
import { encoding_for_model } from 'tiktoken';
import { config } from '../config';

/**
 * Text segmentation service for handling token limits and context management
 */
export class TextSegmentationService {
  private tokenizer;
  private maxSegmentTokens: number;
  private contextTokens: number;

  constructor() {
    this.tokenizer = encoding_for_model(config.model);
    this.maxSegmentTokens = 900; // Reserve 100 tokens for context
    this.contextTokens = 100; // Number of tokens to carry over as context
  }

  /**
   * Count tokens in text
   * @param text Input text
   * @returns Token count
   */
  countTokens(text: string): number {
    return this.tokenizer.encode(text).length;
  }

  /**
   * Split Chinese text into words using jieba
   * @param text Chinese text
   * @returns Array of words
   */
  splitChineseText(text: string): string[] {
    return jieba.cut(text, true); // True for HMM-based segmentation
  }

  /**
   * Split text into segments with context preservation
   * @param text Input text
   * @param sourceLang Source language code
   * @returns Array of segments with context
   */
  splitTextIntoSegments(text: string, sourceLang: string): string[] {
    const segments: string[] = [];
    let remainingText = text;
    let previousContext = '';

    while (remainingText.length > 0) {
      // For Chinese, split into words first to ensure proper segmentation
      let processedText = sourceLang === 'zh' ? this.splitChineseText(remainingText).join(' ') : remainingText;
      
      // Combine with previous context
      const textWithContext = previousContext + processedText;
      
      // Split into tokens
      const tokens = this.tokenizer.encode(textWithContext);
      
      if (tokens.length <= this.maxSegmentTokens) {
        // Take entire remaining text
        segments.push(textWithContext);
        break;
      } else {
        // Find the split point within max tokens
        const splitIndex = this.findSplitPoint(tokens, this.maxSegmentTokens);
        const segmentTokens = tokens.slice(0, splitIndex);
        const segmentText = this.tokenizer.decode(segmentTokens);
        
        // Extract context from the end of the segment
        const contextTokens = tokens.slice(splitIndex - this.contextTokens, splitIndex);
        previousContext = this.tokenizer.decode(contextTokens);
        
        // Add segment to list
        segments.push(segmentText);
        
        // Update remaining text
        const remainingTokens = tokens.slice(splitIndex);
        remainingText = this.tokenizer.decode(remainingTokens);
      }
    }

    return segments;
  }

  /**
   * Find the optimal split point within token limit
   * @param tokens Array of tokens
   * @param maxTokens Maximum tokens per segment
   * @returns Split index
   */
  private findSplitPoint(tokens: number[], maxTokens: number): number {
    // Try to split at sentence boundaries first for better context
    const splitPoints = ['.', '!', '?', '。', '！', '？', '\n', ' '];
    
    for (let i = maxTokens; i > maxTokens - 100; i--) {
      const tokenText = this.tokenizer.decode([tokens[i]]);
      if (splitPoints.includes(tokenText)) {
        return i + 1; // Include the split character
      }
    }
    
    // If no sentence boundary found, split at max tokens
    return maxTokens;
  }
}

// Singleton instance
export const textSegmentationService = new TextSegmentationService();