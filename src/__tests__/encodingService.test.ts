import { EncodingService } from '../services/encodingService';
import fs from 'fs/promises';
import iconv from 'iconv-lite';

// Mock external dependencies
jest.mock('fs/promises');
jest.mock('iconv-lite');

describe('EncodingService Unit Tests', () => {
  let service: EncodingService;
  const mockFs = fs as jest.Mocked<typeof fs>;
  const mockIconv = iconv as jest.Mocked<typeof iconv>;

  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();

    // Mock iconv functions
    mockIconv.encodingExists.mockReturnValue(true);
    mockIconv.encode.mockReturnValue(Buffer.from('encoded text'));
    mockIconv.decode.mockReturnValue('decoded text');

    // Mock fs functions
    mockFs.readFile.mockResolvedValue(Buffer.from('test content'));
    mockFs.writeFile.mockResolvedValue(undefined);

    // Initialize service
    service = new EncodingService();
  });

  afterEach(() => {
    // Clear mocks
    jest.clearAllMocks();
  });

  it('should read file with UTF-8 encoding', async () => {
    const content = await service.readFile('test.txt', 'utf-8');
    expect(mockFs.readFile).toHaveBeenCalled();
    expect(content).toBe('test content');
    expect(mockIconv.decode).not.toHaveBeenCalled();
  });

  it('should read file with GBK encoding', async () => {
    const content = await service.readFile('test.txt', 'gbk');
    expect(mockFs.readFile).toHaveBeenCalled();
    expect(mockIconv.decode).toHaveBeenCalledWith(Buffer.from('test content'), 'gbk');
    expect(content).toBe('decoded text');
  });

  it('should throw error for unsupported encoding in readFile', async () => {
    mockIconv.encodingExists.mockReturnValue(false);
    await expect(service.readFile('test.txt', 'unsupported')).rejects.toThrow(
      'Unsupported encoding: unsupported'
    );
  });

  it('should write file with UTF-8 encoding', async () => {
    await service.writeFile('test.txt', 'test content', 'utf-8');
    expect(mockFs.writeFile).toHaveBeenCalledWith(
      'test.txt',
      Buffer.from('test content', 'utf-8')
    );
    expect(mockIconv.encode).not.toHaveBeenCalled();
  });

  it('should write file with GBK encoding', async () => {
    await service.writeFile('test.txt', 'test content', 'gbk');
    expect(mockIconv.encode).toHaveBeenCalledWith('test content', 'gbk');
    expect(mockFs.writeFile).toHaveBeenCalledWith(
      'test.txt',
      Buffer.from('encoded text')
    );
  });

  it('should throw error for unsupported encoding in writeFile', async () => {
    mockIconv.encodingExists.mockReturnValue(false);
    await expect(service.writeFile('test.txt', 'test content', 'unsupported')).rejects.toThrow(
      'Unsupported encoding: unsupported'
    );
  });

  it('should convert encoding between UTF-8 and GBK', () => {
    const text = 'test content';
    const converted = service.convertEncoding(text, 'utf-8', 'gbk');
    expect(mockIconv.encode).toHaveBeenCalledWith(text, 'utf-8');
    expect(mockIconv.decode).toHaveBeenCalledWith(Buffer.from('encoded text'), 'gbk');
    expect(converted).toBe('decoded text');
  });

  it('should throw error for unsupported encoding in convertEncoding', () => {
    mockIconv.encodingExists.mockReturnValueOnce(true).mockReturnValueOnce(false);
    expect(() => service.convertEncoding('test', 'utf-8', 'unsupported')).toThrow(
      'Unsupported encoding: utf-8 or unsupported'
    );
  });
});