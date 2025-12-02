import { FileScanner } from './scanners/fileScanner';
import { BatchTranslator } from './services/batchTranslator';
import { EncodingService } from './services/encodingService';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

async function runPerformanceAnalysis() {
  // Helper function to measure memory usage
  const measureMemory = () => {
    const memory = process.memoryUsage();
    return {
      rss: memory.rss / (1024 * 1024), // MB
      heapTotal: memory.heapTotal / (1024 * 1024),
      heapUsed: memory.heapUsed / (1024 * 1024),
    };
  };

  // Helper function to measure CPU load
  const measureCpu = () => {
    const loadAvg = os.loadavg();
    return {
      '1m': loadAvg[0],
      '5m': loadAvg[1],
      '15m': loadAvg[2],
    };
  };

  // 1. File Scanning Performance (HTML vs Markdown)
  const scanDir = path.join(os.tmpdir(), 'scan-test');
  await fs.mkdir(scanDir, { recursive: true });

  // Create HTML files
  const htmlCount = 50;
  for (let i = 0; i < htmlCount; i++) {
    await fs.writeFile(
      path.join(scanDir, `html-${i}.html`),
      `<html><body><p>Test ${i}</p></body></html>`
    );
  }

  // Create Markdown files
  const mdCount = 50;
  for (let i = 0; i < mdCount; i++) {
    await fs.writeFile(
      path.join(scanDir, `md-${i}.md`),
      `# Test ${i}\n\nText to translate`
    );
  }

  const fileScanner = new FileScanner();
  console.log('=== File Scanning Performance ===');
  const scanStartMem = measureMemory();
  const scanStartCpu = measureCpu();
  console.time('file-scanning');
  const files = await fileScanner.scan(scanDir);
  console.timeEnd('file-scanning');
  const scanEndMem = measureMemory();
  const scanEndCpu = measureCpu();
  console.log(`Scanned ${files.length} files (${htmlCount} HTML, ${mdCount} Markdown)`);
  console.log('Memory Usage (MB):');
  console.log(`- Before: RSS=${scanStartMem.rss.toFixed(2)}, Heap=${scanStartMem.heapUsed.toFixed(2)}`);
  console.log(`- After: RSS=${scanEndMem.rss.toFixed(2)}, Heap=${scanEndMem.heapUsed.toFixed(2)}`);
  console.log('CPU Load:');
  console.log(`- Before: 1m=${scanStartCpu['1m'].toFixed(2)}, 5m=${scanStartCpu['5m'].toFixed(2)}`);
  console.log(`- After: 1m=${scanEndCpu['1m'].toFixed(2)}, 5m=${scanEndCpu['5m'].toFixed(2)}`);

  // 2. Translation Performance (Different Segment Lengths)
  const inputDir = path.join(os.tmpdir(), 'input-test');
  const outputDir = path.join(os.tmpdir(), 'output-test');
  await fs.mkdir(inputDir, { recursive: true });
  await fs.mkdir(outputDir, { recursive: true });

  // Create test files with different segment lengths
  const segmentLengths = [10, 100, 1000]; // tokens (approximate)
  const fileTypes = ['html', 'md'];

  console.log('\n=== Translation Performance (Different Segment Lengths) ===');
  for (const length of segmentLengths) {
    for (const type of fileTypes) {
      const content = Array(length).fill('<p>Test</p>').join(''); // Approx length tokens
      const filePath = path.join(inputDir, `test-${type}-${length}.${type}`);
      await fs.writeFile(filePath, type === 'html' ? `<html><body>${content}</body></html>` : `# Test\n\n${content}`);
    }
  }

  const translator = new BatchTranslator({
    inputPath: inputDir,
    outputPath: outputDir,
    sourceLang: 'en',
    targetLang: 'zh',
    dryRun: true,
  });

  // Run batch translation instead of directly calling processFile
  console.log('\nRunning batch translation...');
  const transStartMem = measureMemory();
  const transStartCpu = measureCpu();
  console.time('batch-translation');
  await translator.run();
  console.timeEnd('batch-translation');
  const transEndMem = measureMemory();
  const transEndCpu = measureCpu();
  console.log('Memory Usage (MB):');
  console.log(`- Before: RSS=${transStartMem.rss.toFixed(2)}, Heap=${transStartMem.heapUsed.toFixed(2)}`);
  console.log(`- After: RSS=${transEndMem.rss.toFixed(2)}, Heap=${transEndMem.heapUsed.toFixed(2)}`);
  console.log('CPU Load:');
  console.log(`- Before: 1m=${transStartCpu['1m'].toFixed(2)}, 5m=${transStartCpu['5m'].toFixed(2)}`);
  console.log(`- After: 1m=${transEndCpu['1m'].toFixed(2)}, 5m=${transEndCpu['5m'].toFixed(2)}`);

  // 3. File Writing Performance (Different Encodings and Sizes)
  console.log('\n=== File Writing Performance ===');
  const encodingService = new EncodingService();
  const sizes = [1, 10, 100]; // MB
  const encodings = ['utf8', 'gbk'];

  for (const size of sizes) {
    for (const encoding of encodings) {
      const content = 'a'.repeat(size * 1024 * 1024); // size MB
      const filePath = path.join(os.tmpdir(), `test-write-${size}mb-${encoding}.txt`);
      console.log(`Writing ${size}MB file with ${encoding} encoding`);
      const writeStartMem = measureMemory();
      const writeStartCpu = measureCpu();
      console.time(`write-${encoding}-${size}mb`);
      await encodingService.writeFile(filePath, content, encoding);
      console.timeEnd(`write-${encoding}-${size}mb`);
      const writeEndMem = measureMemory();
      const writeEndCpu = measureCpu();
      console.log('Memory Usage (MB):');
      console.log(`- Before: RSS=${writeStartMem.rss.toFixed(2)}, Heap=${writeStartMem.heapUsed.toFixed(2)}`);
      console.log(`- After: RSS=${writeEndMem.rss.toFixed(2)}, Heap=${writeEndMem.heapUsed.toFixed(2)}`);
      console.log('CPU Load:');
      console.log(`- Before: 1m=${writeStartCpu['1m'].toFixed(2)}, 5m=${writeStartCpu['5m'].toFixed(2)}`);
      console.log(`- After: 1m=${writeEndCpu['1m'].toFixed(2)}, 5m=${writeEndCpu['5m'].toFixed(2)}`);
      await fs.rm(filePath, { force: true }).catch(() => {});
    }
  }

  // Clean up
  await fs.rm(scanDir, { recursive: true, force: true });
  await fs.rm(inputDir, { recursive: true, force: true });
  await fs.rm(outputDir, { recursive: true, force: true });
}

runPerformanceAnalysis().catch(console.error);