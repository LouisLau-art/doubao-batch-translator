# Doubao HTML+Markdown Batch Translator Project Plan  
**Version**: 1.0 | **Date**: 2025-12-02 | **Status**: Active  

## Project Description  
A TypeScript-based CLI tool to batch translate HTML/Markdown files while preserving original structure, adapting to Doubao's model limits, and supporting Chinese text processing.  

### Core Goals  
1. **Format Preservation**: Retain HTML DOM/Markdown markup; skip code blocks and translate relevant text nodes/attributes.  
2. **Model Adaptation**: Comply with Doubao's limits (1k input tokens, 4k context window, rate limits).  
3. **Batch Efficiency**: Process multiple files recursively with caching for repeated segments.  
4. **Chinese Support**: Accurate text segmentation using jieba; handle GBK/UTF-8 encodings.  

### Key Features  
✅ HTML: Preserve DOM, translate `alt`/`title`/`aria-label` attributes  
✅ Markdown: Preserve markup, skip code blocks  
✅ Batch: Recursive directory scan, output structure preservation  
✅ Config: dotenv for API keys/model settings  
✅ Tools: Verbose logging, dry-run mode  
✅ Encoding: UTF-8 + GBK support  

## Current Progress  
### Completed Tasks  
- Project initialization (npm + TypeScript)  
- Dependency installation (core + dev tools)  
- Config files creation (.gitignore, .env.example)  
- CLI implementation (commander setup)  
- Config loader (dotenv integration)  
- Logger utility (verbose mode)  
- LLM Client (Doubao API adapter)
- File Scanner (recursive directory scan)
- HTML Processor (DOM parsing/extraction)
- Markdown Processor (marked lexer/extraction)
- Cache module (file-based caching)
- Text Segmentation module (jieba + tiktoken)
- Encoding Support (iconv-lite)
- Output Manager (directory structure preservation)
- Batch Workflow (scan → process → translate → save)
- Dry Run Mode (show changes without saving)

## Todo List  
### Phase 1: Foundation Setup (Completed)  
- [x] Initialize npm + TypeScript  
- [x] Install dependencies  
- [x] Create config files (.gitignore, .env.example)  
- [x] Implement CLI (commander setup)  
- [x] Implement config loader (dotenv)  
- [x] Create logger (verbose mode)  

### Phase 2: Core Components (In Progress)  
- [x] Implement LLM Client (Doubao API adapter)  
- [x] Implement Cache (file-based caching for translated segments)
- [x] Implement File Scanner (recursive scan)
- [x] Implement HTML Processor (DOM parsing/extraction)
- [x] Implement Markdown Processor (marked lexer/extraction)
- [x] Implement Text Segmentation (reusable module with jieba + tiktoken)

### Phase3: Batch Workflow & Integration (Pending)
- [x] Implement Encoding Support (iconv-lite for GBK/UTF-8)
- [x] Implement Output Manager (directory structure preservation)  
- [x] Build Batch Workflow (end-to-end flow: scan → process → translate → save)
- [x] Add Dry Run Mode (show changes without saving files)

### Phase4: Testing & Documentation (Pending)  
- [x] Write unit tests (HTML/Markdown processors, LLM client, file scanner)
- [x] Write integration tests (full translation flow)
- [x] Create comprehensive documentation (README.md)
- [x] Add example files for testing

## 项目进展更新 (2025-12-02)

### ✅ 已完成的重要改进

#### 配置管理完善
- 创建了 `.env.example` 配置文件模板，包含完整的配置选项
- 完善了 `src/config.ts` TypeScript配置模块
- 支持环境变量和CLI参数的多层配置

#### 技术问题修复
- **TypeScript编译错误**: 修复了logger、tiktoken API、文件扫描器等模块的类型错误
- **HTML处理器兼容性**: 将XPath替换为DOM遍历方法，解决Node.js环境兼容性问题
- **API认证处理**: 创建了mock客户端，支持无API密钥的测试验证

#### 测试验证完成
- 创建了完整的示例文件 (`examples/sample.html`, `examples/sample.md`)
- 通过mock客户端验证了端到端翻译流程
- 确认以下功能正常工作：
  - 文件扫描和编码检测 (UTF-8/GBK)
  - HTML文本提取和属性翻译
  - Markdown AST解析和代码块保留
  - Dry-run模式预览功能

### 📊 配置文件说明

#### 环境变量配置 (`.env`)
```env
# API配置
ARK_API_KEY=your_api_key
API_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3/responses
DEFAULT_MODEL=doubao-seed-translation-250915

# 翻译配置
DEFAULT_SOURCE_LANG=en
DEFAULT_TARGET_LANG=zh
MAX_INPUT_TOKENS=1000

# 文件处理
SUPPORTED_EXTENSIONS=.html,.htm,.md,.markdown
SUPPORTED_ENCODINGS=utf8,gbk

# 缓存配置
CACHE_DIR=./.cache
CACHE_TTL_HOURS=24

# 日志配置
LOG_LEVEL=info
VERBOSE=false

# 性能配置
MAX_CONCURRENT_FILES=5
MAX_CONCURRENT_REQUESTS=10
```

## Next Steps

### Phase 4: 测试与文档完善 (1-2周)
- [ ] 编写单元测试 (HTML/Markdown处理器、LLM客户端、文件扫描器)
- [ ] 编写集成测试 (完整翻译流程)
- [ ] 创建性能基准测试
- [ ] 完善用户文档和API文档

### Phase 5: 性能优化 (2-3周)
- [ ] 分析大规模批处理的性能瓶颈
- [ ] 实现文件处理的并行执行
- [ ] 优化缓存策略和内存使用
- [ ] 添加请求限流和错误重试机制

### Phase 6: 生产环境准备 (1-2周)
- [ ] 创建Docker容器化部署
- [ ] 设置GitHub Actions CI/CD流水线
- [ ] 添加健康检查和监控
- [ ] 编写部署和运维文档

### Phase 7: 功能扩展 (后续)
- [ ] 支持更多文件格式 (PDF, Word, Excel)
- [ ] 添加更多翻译服务提供商支持
- [ ] 实现增量翻译和差异检测
- [ ] 开发Web界面和API服务