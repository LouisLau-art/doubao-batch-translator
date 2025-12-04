# 豆包批量翻译器 - 项目结构

## 项目概述
豆包批量翻译器是一个高效的Python异步命令行翻译工具，支持JSON文件翻译、HTML文件翻译和HTTP API服务。

## 目录结构

```
doubao-batch-translator/
├── main.py                    # 主入口文件
├── requirements.txt           # 项目依赖
├── README.md                  # 项目说明文档
├── .env.example               # 环境变量示例
├── .gitignore                 # Git忽略文件
├── PROJECT_STRUCTURE.md       # 项目结构说明 (本文件)
│
├── core/                      # 核心模块
│   ├── __init__.py
│   ├── client.py              # 异步翻译客户端
│   ├── config.py              # 配置管理
│   ├── exceptions.py          # 自定义异常
│   └── token_tracker.py       # Token配额跟踪
│
├── processors/                # 处理器模块
│   ├── __init__.py
│   ├── json_worker.py         # JSON文件处理器
│   ├── html_worker.py         # HTML文件处理器
│   └── epub_worker.py         # ePub电子书处理器
│
├── server/                    # HTTP服务器模块
│   ├── __init__.py
│   └── api.py                 # API服务实现
│
├── docs/                      # 文档目录
│   └── EPUB_TRANSLATION_ISSUE_ANALYSIS.md
│
├── examples/                  # 示例文件
│   ├── sample.html
│   ├── sample.md
│   └── translation_work.json
│
└── epubs/                     # ePub文件存储
    └── original/
        └── en/                # 英文原版ePub文件
            ├── content.opf
            ├── cover.jpeg
            ├── mimetype
            ├── page_styles.css
            ├── stylesheet.css
            ├── titlepage.xhtml
            ├── toc.ncx
            ├── META-INF/
            │   └── container.xml
            └── OEBPS/
                ├── images/    # 图片资源
                └── xhtml/     # 章节内容
```

## 文件说明

### 核心文件
- **main.py**: 命令行工具主入口，支持JSON、HTML、ePub翻译和HTTP服务器
- **requirements.txt**: Python依赖包列表
- **README.md**: 详细的使用说明和配置指南

### 核心模块 (core/)
- **client.py**: 异步翻译客户端，处理API请求和并发控制
- **config.py**: 配置管理，包括API密钥和并发设置
- **exceptions.py**: 自定义异常类
- **token_tracker.py**: Token使用量跟踪和配额管理

### 处理器模块 (processors/)
- **json_worker.py**: 处理JSON格式的翻译文件
- **html_worker.py**: 处理HTML文件翻译
- **epub_worker.py**: 处理ePub电子书翻译

### 服务器模块 (server/)
- **api.py**: HTTP API服务器实现，提供RESTful接口

### 资源目录
- **examples/**: 示例文件，用于测试和演示
- **epubs/**: 存储ePub原文件，用于翻译处理
- **docs/**: 项目相关文档

## 使用方式

### 命令行使用
```bash
# JSON翻译
python main.py json --file examples/translation_work.json

# HTML翻译
python main.py html --file examples/sample.html --output translated.html

# ePub翻译
python main.py epub --file epubs/original/en/book.epub --output translated.epub

# 启动HTTP服务器
python main.py server --port 8000
```

### 环境配置
复制 `.env.example` 为 `.env` 并设置API密钥：
```bash
cp .env.example .env
# 编辑 .env 文件，设置 ARK_API_KEY=your_api_key_here
```

## 架构设计
项目采用"一核多壳"架构：
- **核心**: AsyncTranslator 提供统一翻译能力
- **外壳**: 各种处理器适配不同文件格式和场景
- **异步**: 基于asyncio的异步并发处理
- **模块化**: 各功能模块独立，便于维护和扩展