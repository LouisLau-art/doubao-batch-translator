# 豆包批量翻译器 (Doubao Batch Translator)

一个高效的Python异步命令行翻译工具，基于"一核多壳"架构设计，支持JSON文件翻译、HTML文件翻译和HTTP API服务。

## 🚀 核心特性

### 架构特点
- **一核多壳设计**: 核心`AsyncTranslator`提供统一翻译能力，外层处理器适配不同场景。

## 📋 环境要求

- **Python**: 3.13+
- **操作系统**: Linux, macOS, Windows

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
```

### 3. 基本使用

#### JSON文件翻译 (RenPy翻译专用)

```bash
# 基本用法
python main.py json --file translation_work.json
```

#### HTML文件翻译

```bash
# 基本用法
python main.py html --file input.html --output translated.html --target-lang zh
```

#### 启动HTTP API服务器

```bash
# 基本启动
python main.py server --port 8000
```

### 4. Token配额管理
- **每日2M免费额度监控**: 实时跟踪token使用量，防止超额
- **断点续传**: 支持翻译进度保存，中断后可继续
```

## 🔧 详细配置

### 命令行参数

#### 通用参数
- `--api-key`: API密钥（可选，默认从环境变量读取）
- `--verbose, -v**: 启用详细日志

### 环境变量配置

```bash
# API配置
export ARK_API_KEY=your_api_key
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
```

## 🔄 断点续传机制

### JSON处理器
- 自动检测未翻译条目
- 每批翻译完成后立即保存结果
- 创建时间戳备份文件
- 支持中断后继续翻译

## 🛠️ 架构设计

### 核心组件

#### AsyncTranslator
- **职责**: 统一翻译能力
- **特性**: 异步并发、批处理、频率控制、重试机制

### 实现功能
- **单请求高并发**: 适配`doubao-seed-translation-250915`模型（不支持批量请求）
- **并发控制**: 使用Semaphore限制最大并发数（默认20）
- **Token跟踪**: 实时监控使用量，防止超过每日免费额度
- **智能批处理**: 基于token使用量的动态批次大小调整
- **检查点系统**: 每50个项目自动保存进度

## 📈 性能优化

### 并发控制
- **默认并发数**: 20
- **频率限制**: 避免触发API限制

## 🤝 贡献指南

### 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements.txt
```

---

**Git commit message**: "feat: implement token quota management and CLI tool structure"

**注意**: 本工具专为高效利用豆包API的免费额度而设计，强烈建议在处理大型文件时监控翻译进度，确保符合每日额度限制。