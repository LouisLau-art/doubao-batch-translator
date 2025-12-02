import dotenv from 'dotenv';

dotenv.config();

export const config = {
  DEFAULT_MODEL: process.env.DEFAULT_MODEL || 'doubao-seed-translation-250915',
  DOUBAO_API_KEY: process.env.DOUBAO_API_KEY || '',
  CACHE_DIR: process.env.CACHE_DIR || './.cache',
  VERBOSE: process.env.VERBOSE === 'true',
};