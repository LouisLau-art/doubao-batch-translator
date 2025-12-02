# 豆包翻译模型统一接口

一个高效的Python异步翻译工具，基于"一核多壳"架构设计，支持JSON文件翻译、HTML文件翻译和HTTP API服务。

## 🚀 核心特性

### 架构特点
- **一核多壳设计**: 核心`AsyncTranslator`提供统一翻译能力，外层处理器适配不同场景
- **异步并发**: 基于Python asyncio和httpx，实现高效并发处理
- **智能批处理**: 自动将文本分批，优化API调用效率和Token使用
- **断点续传**: 支持大数据翻译进度保存，中断后可继续

### 功能特性
- **JSON处理器**: 专为RenPy游戏翻译设计，支持断点续传和进度保存
- **HTML处理器**: 智能识别URL、代码块等不翻译内容
- **HTTP服务器**: 适配OpenAI格式，为"沉浸式翻译"插件提供服务
- **频率控制**: 内置频率限制和并发控制，避免触发API限制

## 📋 环境要求

- **Python**: 3.13+
- **操作系统**: Linux, macOS, Windows
- **API**: 豆包翻译API (doubao-seed-translation-250915)

## 📦 安装使用

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd doubao-batch-translator

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置API密钥

```bash
# 设置环境变量
export ARK_API_KEY=your_api_key_here

# 或者在命令行直接指定
python main.py json --file data.json --api-key your_api_key_here
```

### 3. 基本使用

#### JSON文件翻译 (RenPy翻译专用)

```bash
# 基本用法
python main.py json --file translation_work.json

# 指定输出文件和语言
python main.py json --file input.json --output output.json --target-lang zh

# 使用命令行参数指定API密钥
python main.py json --file data.json --api-key YOUR_KEY --concurrent 3
```

#### HTML文件翻译

```bash
# 基本用法
python main.py html --file sample.html

# 指定输出文件和语言
python main.py html --file input.html --output translated.html --target-lang zh
```

#### 启动HTTP API服务器

```bash
# 基本启动
python main.py server --port 8000

# 自定义配置
python main.py server --host 0.0.0.0 --port 8080 --debug
```

## 🔧 详细配置

### 命令行参数

#### 通用参数
- `--api-key`: API密钥（可选，默认从环境变量读取）
- `--verbose, -v`: 启用详细日志
- `--config-file`: 配置文件路径（待实现）

#### JSON翻译参数
- `--file, -f`: 输入JSON文件路径（必需）
- `--output, -o`: 输出JSON文件路径（可选，默认覆盖原文件）
- `--source-lang`: 源语言代码（可选）
- `--target-lang, -t`: 目标语言代码（默认：zh）

#### HTML翻译参数
- `--file, -f`: 输入HTML文件路径（必需）
- `--output, -o`: 输出HTML文件路径（可选）
- `--source-lang`: 源语言代码（可选）
- `--target-lang, -t`: 目标语言代码（默认：zh）

#### 服务器参数
- `--host`: 绑定地址（默认：0.0.0.0）
- `--port, -p`: 监听端口（默认：8000）
- `--debug`: 启用调试模式
- `--max-concurrent`: 最大并发数
- `--max-rps`: 每秒最大请求数

### 环境变量配置

```bash
# API配置
export ARK_API_KEY=your_api_key
export DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/responses
export DOUBAO_MODEL=doubao-seed-translation-250915

# 性能配置
export MAX_CONCURRENT=5
export MAX_REQUESTS_PER_SECOND=50.0
export REQUEST_TIMEOUT=30.0
export MAX_RETRIES=3
```

### 支持的语言

| 代码 | 语言名称 | 代码 | 语言名称 |
|------|----------|------|----------|
| zh | 中文（简体） | zh-Hant | 中文（繁体） |
| en | 英语 | de | 德语 |
| fr | 法语 | es | 西班牙语 |
| it | 意大利语 | pt | 葡萄牙语 |
| ja | 日语 | ko | 韩语 |
| th | 泰语 | vi | 越南语 |
| ru | 俄语 | ar | 阿拉伯语 |

## 📊 API文档

### HTTP API端点

#### 健康检查
```
GET /
```

#### 获取模型列表
```
GET /v1/models
```

#### 翻译服务 (OpenAI兼容)
```
POST /v1/chat/completions
```

请求体示例:
```json
{
  "model": "doubao-seed-translation-250915",
  "messages": [
    {
      "role": "user", 
      "content": "Hello, world! This is a test message."
    }
  ],
  "source_language": "en",
  "target_language": "zh",
  "temperature": 0.3,
  "max_tokens": 1000,
  "stream": false
}
```

#### 服务状态
```
GET /v1/status
```

### Python API使用

```python
import asyncio
from core import AsyncTranslator, TranslatorConfig
from processors import JSONProcessor, HTMLProcessor

async def main():
    # 创建配置
    config = TranslatorConfig(api_key="your_api_key")
    
    # 创建翻译器
    async with AsyncTranslator(config) as translator:
        # 翻译单个文本
        result = await translator.translate_single(
            text="Hello, world!",
            source_lang="en", 
            target_lang="zh"
        )
        print(result)  # "你好，世界！"
        
        # 批量翻译
        results = await translator.translate_batch(
            texts=["Hello", "How are you?", "Goodbye"],
            source_lang="en",
            target_lang="zh"
        )
        
        # 处理JSON文件
        processor = JSONProcessor(translator)
        result = await processor.translate_file(
            input_file="data.json",
            target_lang="zh"
        )
        
        # 处理HTML文件
        html_processor = HTMLProcessor(translator)
        result = await html_processor.process_file(
            input_file="sample.html",
            target_lang="zh"
        )

asyncio.run(main())
```

## 🔄 断点续传机制

### JSON处理器
- 自动检测未翻译条目
- 每批翻译完成后立即保存结果
- 创建时间戳备份文件
- 支持中断后继续翻译

### 进度保存策略
```python
# 自动备份和进度保存
{
  "total": 100,        # 总条目数
  "translated": 65,    # 已翻译数量
  "untranslated": 35,  # 未翻译数量
  "progress": 65.0,    # 完成百分比
  "success": true      # 是否成功
}
```

## 🛠️ 架构设计

### 目录结构

```
doubao-batch-translator/
├── core/                   # 核心模块
│   ├── __init__.py
│   ├── config.py           # 配置管理
│   ├── exceptions.py       # 异常定义
│   └── translator.py       # AsyncTranslator核心类
├── processors/             # 处理器模块
│   ├── __init__.py
│   ├── json_worker.py      # JSON翻译处理器
│   └── html_worker.py      # HTML翻译处理器
├── server/                 # HTTP服务器
│   ├── __init__.py
│   └── api.py              # FastAPI服务器
├── examples/               # 示例文件
│   ├── translation_work.json
│   └── sample.html
├── main.py                 # 主入口文件
├── requirements.txt        # 依赖文件
└── README.md              # 说明文档
```

### 核心组件

#### AsyncTranslator
- **职责**: 统一翻译能力
- **特性**: 异步并发、批处理、频率控制、重试机制
- **输入**: 文本列表
- **输出**: 翻译结果

#### JSONProcessor
- **职责**: JSON文件翻译
- **特性**: 断点续传、进度保存、状态检查
- **输入**: JSON文件路径
- **输出**: 翻译后的JSON文件

#### HTMLProcessor  
- **职责**: HTML文件翻译
- **特性**: 智能识别、属性处理、代码保护
- **输入**: HTML文件路径
- **输出**: 翻译后的HTML文件

#### DoubaoServer
- **职责**: HTTP API服务
- **特性**: OpenAI兼容、错误处理、健康检查
- **输入**: HTTP请求
- **输出**: HTTP响应

## 🔧 故障排除

### 常见问题

#### 1. API密钥错误
```bash
错误: 未找到API密钥
解决: export ARK_API_KEY=your_api_key
```

#### 2. 频率限制
```bash
错误: RateLimitError: 请求过于频繁
解决: 增加延迟时间，降低并发数
```

#### 3. JSON格式错误
```bash
错误: ValidationError: JSON数据必须是数组格式
解决: 确保JSON文件包含数组格式的数据
```

#### 4. 网络连接问题
```bash
错误: NetworkError: 网络连接失败
解决: 检查网络连接和代理设置
```

### 调试模式

```bash
# 启用详细日志
python main.py json --file data.json --verbose

# 服务器调试模式
python main.py server --debug
```

### 日志文件

```bash
# 查看日志
tail -f doubao-translator.log

# 清理日志
rm doubao-translator.log
```

## 📈 性能优化

### 并发控制
- **默认并发数**: 5
- **最大并发数**: 建议不超过10
- **频率限制**: 默认50请求/秒

### 批处理策略
- **批大小**: 默认15个项目/批
- **字符限制**: 默认500字符/批
- **优化目标**: 减少API调用次数

### 缓存机制
- **文件缓存**: 自动备份原始文件
- **进度缓存**: 实时保存翻译进度
- **错误恢复**: 自动重试失败请求

## 🛡️ 安全考虑

### API密钥安全
- 建议使用环境变量而非硬编码
- 服务器模式注意密钥暴露风险
- 定期轮换API密钥

### 文件处理安全
- JSON文件自动备份
- 路径遍历攻击防护
- 文件权限检查

### 网络安全
- HTTPS连接
- 请求频率限制
- 错误信息脱敏

## 🤝 贡献指南

### 开发环境设置
```bash
# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-asyncio black isort mypy

# 代码格式化和检查
black . 
isort .
mypy .
```

### 测试
```bash
# 运行测试
pytest

# 异步测试
pytest --asyncio-mode=auto
```

## 📄 许可证

本项目遵循MIT许可证。详情请参阅LICENSE文件。

## 🔗 相关链接

- [豆包API文档](https://bytedance.com/)
- [Python asyncio文档](https://docs.python.org/3/library/asyncio.html)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [httpx文档](https://www.python-httpx.org/)

---

**注意**: 本工具专为高效利用豆包API的免费额度而设计，强烈建议在处理大型文件时监控翻译进度，确保符合每日额度限制。