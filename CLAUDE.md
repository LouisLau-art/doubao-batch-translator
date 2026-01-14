```
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
```

## 项目概述

豆包批量翻译器 (Doubao Batch Translator) 是一个高效的 Python 异步命令行翻译工具，基于"一核多壳"架构设计，支持 JSON 文件翻译、HTML 文件翻译、ePub 电子书翻译、Markdown 文件翻译和 HTTP API 服务。

## 常用命令

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行翻译任务

#### JSON 文件翻译 (RenPy翻译专用)
```bash
python main.py json --file <your_json_file_path>
```

#### HTML 文件翻译
```bash
python main.py html --file <your_html_file_path> --output translated.html
```

#### ePub 电子书翻译
```bash
# 单本翻译
python main.py epub --file <your_epub_file_path> --output translated.epub

# 批量翻译整个目录
python main.py epub --file /path/to/epub/folder/ --output /path/to/output/ --auto-approve
```

#### Markdown 文件翻译
```bash
# 基本用法
python main.py md --file README.md --output README_zh.md

# 递归翻译目录
python main.py md --file /path/to/md/folder --output /path/to/output/folder --recursive
```

#### 启动 HTTP API 服务器
```bash
python main.py server --port 8000

# 调试模式
python main.py server --port 8000 --debug
```

### 运行测试

#### 并发性能测试
```bash
# 先启动服务器
python main.py server --port 8000

# 在另一个终端运行测试
python tests/test_concurrency.py
```

#### 使用 pytest 运行所有测试
```bash
pytest tests/
```

#### 运行单个测试文件
```bash
pytest tests/test_concurrency.py -v
```

## 项目架构

### 核心组件

#### `core/` - 核心翻译引擎
- `client.py`: 异步翻译客户端 `AsyncTranslator`，提供统一翻译接口
- `config.py`: 配置管理
- `exceptions.py`: 自定义异常
- `token_tracker.py`: Token 配额跟踪

#### `processors/` - 文件格式处理器
- `json_worker.py`: JSON 文件翻译处理器（RenPy 专用）
- `html_worker.py`: HTML 文件翻译处理器
- `epub_worker.py`: ePub 电子书翻译处理器
- `md_worker.py`: Markdown 文件翻译处理器

#### `server/` - HTTP API 服务
- `api.py`: FastAPI 服务器实现，提供 OpenAI 兼容接口和自定义翻译接口

#### `tools/` - 辅助工具
- `check_untranslated.py`: EPUB 漏译检测
- `patch_leaks.py`: 漏译精准修复
- `clean_xml.py`: XML 清理工具
- `manual_fix_epub.py`: EPUB 手动精修助手

#### `tests/` - 测试脚本
- `test_concurrency.py`: 并发性能测试

## 架构特点

### 一核多壳设计
- 核心 `AsyncTranslator` 提供统一翻译能力
- 外层处理器适配不同文件格式和场景

### 快慢双车道并发
- 慢车道（80并发）：`doubao-seed-translation-250915` (RPM=5000, 免费额度)
- 快车道（500并发）：`DeepSeek`, `Doubao Pro` 等 (RPM=30000, 高性能)

### 智能降级策略
- 采用"乐观尝试 + 优雅降级"策略
- Seed 模型失败自动切换到快车道模型

## 配置

### 环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，设置 ARK_API_KEY
```

### 模型配置
编辑 `models.json` 文件，按优先级排列需要使用的模型：
```json
[
  "doubao-seed-translation-250915",
  "deepseek-v3-250324",
  "doubao-seed-1-6-251015"
]
```

## 主要依赖

- **异步网络请求**: httpx
- **API 服务器**: fastapi, uvicorn, pydantic
- **HTML/XML 解析**: beautifulsoup4, lxml
- **Markdown 解析**: mistune, pyyaml
- **开发工具**: pytest, pytest-asyncio, black, isort
