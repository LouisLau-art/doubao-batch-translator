# 豆包批量翻译器 (Doubao Batch Translator)

一个高效的Python异步命令行翻译工具，基于"一核多壳"架构设计，支持JSON文件翻译、HTML文件翻译和HTTP API服务。

## 🚀 核心特性

### 架构特点

- **一核多壳设计**: 核心`AsyncTranslator`提供统一翻译能力，外层处理器适配不同场景
- **快慢双车道并发**: 智能识别模型性能，自动分流到快车道(500并发)或慢车道(80并发)
  - 🐢 慢车道：`doubao-seed-translation-250915` (RPM=5000, 免费额度)
  - 🚀 快车道：`DeepSeek`, `Doubao Pro` 等 (RPM=30000, 高性能)
- **异步并发**: 基于asyncio的高效异步处理，支持高并发翻译
- **模块化设计**: 各功能模块独立，便于维护和扩展
- **智能降级**: 慢车道超限自动切换快车道，确保服务可用性

## 📁 项目结构

```
doubao-batch-translator/
├── main.py                    # 主入口文件
├── requirements.txt           # 项目依赖
├── README.md                  # 项目说明文档
├── .env.example               # 环境变量示例
├── .gitignore                 # Git忽略文件
├── PROJECT_STRUCTURE.md       # 项目结构说明
├── check_untranslated.py      # 检查未翻译内容的脚本
│
├── core/                      # 核心模块
│   ├── client.py              # 异步翻译客户端
│   ├── config.py              # 配置管理
│   ├── exceptions.py          # 自定义异常
│   └── token_tracker.py       # Token配额跟踪
│
├── processors/                # 处理器模块
│   ├── json_worker.py         # JSON文件处理器
│   ├── html_worker.py         # HTML文件处理器
│   └── epub_worker.py         # ePub电子书处理器
│
└── server/                    # HTTP服务器模块
      └── api.py               # API服务实现
```

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
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，设置API密钥
# ARK_API_KEY=your_api_key_here
```

### 3. 基本使用

#### JSON文件翻译 (RenPy翻译专用)

```bash
# 基本用法
python main.py json --file <your_json_file_path>
```

#### HTML文件翻译

```bash
# 基本用法
python main.py html --file <your_html_file_path> --output translated.html --target-lang zh
```

#### ePub电子书翻译

```bash
# 单本翻译
python main.py epub --file <your_epub_file_path> --output translated.epub --target-lang zh

# 批量翻译整个目录 (推荐)
python main.py epub --file /path/to/epub/folder/ --output /path/to/output/ --target-lang zh --auto-approve
```

#### 🔄 人工翻译工作流 (新功能)

批量翻译完成后，如果仍有漏译，系统会自动生成 `人工翻译.json` 供您手动补充：

```bash
# 步骤1: 批量翻译 (自动生成漏译报告和JSON)
python main.py epub --file /path/to/books/ --output /path/to/translated/ --target-lang zh --auto-approve

# 步骤2: (可选) 如果需要重新生成JSON
python main.py generate-json --dir /path/to/translated/

# 步骤3: 编辑 人工翻译.json，填写您的译文

# 步骤4: 将人工译文回填到EPUB
python main.py apply-fix --json /path/to/translated/人工翻译.json
```

**JSON 格式示例**:
```json
{
  "books": [
    {
      "epub_name": "book_translated.epub",
      "segments": [
        {
          "original": "Untranslated text...",
          "translation": ""  // ← 在这里填写您的译文
        }
      ]
    }
  ]
}
```

#### 启动HTTP API服务器

```bash
# 基本启动
python main.py server --port 8000

# 调试模式
python main.py server --port 8000 --debug
```

### 5. 🌐 沉浸式翻译插件配置

本项目提供 HTTP API 服务，可与 [沉浸式翻译](https://immersivetranslate.com/) 浏览器插件配合使用，让你在浏览网页时直接使用豆包专用翻译模型。

#### 启动服务器

```bash
python main.py server --port 8000
```

服务器启动后会监听 `http://0.0.0.0:8000`。

#### 配置方式一：OpenAI 兼容模式（推荐）

1. 打开沉浸式翻译设置 → 翻译服务 → 选择 **OpenAI**
2. 配置以下参数：
   - **API Key**: 任意填写（如 `sk-xxx`，服务器不验证）
   - **自定义 API 地址**: `http://127.0.0.1:8000/v1/chat/completions`
   - **模型**: `doubao-seed-translation-250915`
3. **重要**：Prompt 配置
   - **System Prompt**: 可留空（专用翻译模型不需要）
   - **Prompt**: 填写 `{{text}}`（必须包含这个变量）
   - **Multiple Prompt**: 填写 `{{text}}`
   - **Subtitle Prompt**: 填写 `{{text}}`

#### 配置方式二：自定义 API 模式

1. 打开沉浸式翻译设置 → 开发者设置 → 启用 **Beta 测试功能**
2. 翻译服务 → 选择 **自定义 API**
3. 设置 URL: `http://127.0.0.1:8000/translate`

**请求格式**（插件自动处理）:
```json
{
  "source_lang": "en",
  "target_lang": "zh",
  "text_list": ["Hello", "World"]
}
```

**响应格式**:
```json
{
  "translations": [
    {"detected_source_lang": "en", "text": "你好"},
    {"detected_source_lang": "en", "text": "世界"}
  ]
}
```

#### API 端点说明

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 健康检查 |
| `/v1/models` | GET | 获取可用模型列表 |
| `/v1/chat/completions` | POST | OpenAI 兼容翻译接口 |
| `/translate` | POST | 沉浸式翻译自定义 API 接口 |

#### 常见问题

**Q: 所有内容都被翻译成 "OK"？**  
A: 检查 Prompt 配置，确保包含 `{{text}}` 变量。如果 Prompt 为空，messages 会是空数组。

**Q: 出现 422 错误？**  
A: 确认使用正确的端点。OpenAI 模式用 `/v1/chat/completions`，自定义 API 模式用 `/translate`。

**Q: 连接被拒绝？**  
A: 确保服务器正在运行，使用 `127.0.0.1` 而不是 `0.0.0.0` 作为客户端地址。

#### 配置方式三：直接对接火山方舟 API（无需中间服务器）

你可以直接在沉浸式翻译中配置火山方舟 API，无需使用本项目提供的中间服务器。这种方式更轻量，适合不需要批量翻译功能的用户。

##### 配置步骤

1. 打开沉浸式翻译设置 → 翻译服务 → 点击 **Edit Full User Config**
2. 在 `translationServices` 对象中添加或修改以下配置：

```jsonc
"custom-ai-d2JnahaZ": {
  "type": "custom-ai",
  "extends": "custom-ai",
  "name": "Doubao Seed Translation",
  "APIKEY": "你的 APIKey",
  "apiUrl": "https://ark.cn-beijing.volces.com/api/v3/responses",
  "model": "doubao-seed-translation-250915",
  "group": "custom",
  "visible": true,
  "limit": "80",
  "maxTextLengthPerRequest": "1000", // 按照模型最大输入Token设定
  "maxTextGroupLengthPerRequest": "1", // 每次只支持翻一个text
  "maxTextGroupLengthPerRequestForSubtitle": "1",
  "prompt": "{{text}}", // 必填，占位符
  "systemPrompt": "",
  "multiplePrompt": "{{text}}",
  "subtitlePrompt": "{{text}}",
  "headerConfigs": {
    "Authorization": "Bearer {{APIKEY}}",
    "Content-Type": "application/json"
  },
  "bodyConfigs": {
    "model": "doubao-seed-translation-250915",
    "input": [
      {
        "role": "user",
        "content": [
          {
            "type": "input_text",
            "text": "{{text}}",
            "translation_options": {
              "target_language": "{{to}}"
            }
          }
        ]
      }
    ]
  }
}
```

> 如果你希望显式指定 `source_language`，可以在 `translation_options` 中添加 `"source_language": "{{from}}"`。

3. 保存配置后，选择 **Doubao Seed Translation** 作为当前翻译服务

##### 功能验证方法

1. 打开任意网页
2. 确保已切换到「Doubao Seed Translation」为当前翻译服务
3. 打开 DevTools → network 观察请求结构是否如下：

```json
POST https://ark.cn-beijing.volces.com/api/v3/responses

{
  "model": "doubao-seed-translation-250915",
  "input": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "Hello world",
          "translation_options": {
            "target_language": "zh"
          }
        }
      ]
    }
  ]
}
```

##### 问题排查清单

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 翻译失败或未调用 | Body格式不符，或没带 header | 使用上面的 bodyConfig 与 headerConfig 模板 |
| 多段落被截断或失败 | 模型不支持聚合段落 | 设置 `"maxTextGroupLengthPerRequest": "1"` |
| 输出断行、排版偏移 | CSS 被原网页强制 | 用 `globalStyles` 加 `-webkit-line-clamp: unset;` |
| 插件未调用你自定义服务 | translationService 名填错 | 确保 `"translationService": "custom-ai-d2JnahaZ"` |

##### 进阶功能拓展建议（可选）

1. **匹配特定语言自动使用翻译模型**
   ```json
   "translationLanguagePattern": {
     "matches": ["en", "ja"]
   }
   ```

2. **显示主题样式**
   ```json
   "translationTheme": "underline"
   ```

   或者为不同网站设置：
   ```json
   "translationThemePatterns": {
     "highlight": {
       "matches": ["microsoft.com"]
     }
   }
   ```

3. **避免未配置项出现在 UI 面板中**
   ```json
   "showUnconfiguredTranslationServiceInPopup": false,
   ```

4. **绑定使用该服务用于全部网页或特定网页**
   ```json
   "translationUrlPattern": {
     "matches": [ "*" ] // 或指定网站如 "twitter.com"
   }
   ```

### 4. Token配额管理

- **每日2M免费额度监控**: 实时跟踪token使用量，防止超额
- **断点续传**: 支持翻译进度保存，中断后可继续

## 🔧 详细配置

### 命令行参数

#### 通用参数

- `--api-key`: API密钥（可选，默认从环境变量读取）
- `--verbose, -v`: 启用详细日志
- `--max-concurrent`: 最大并发请求数（默认: 20）
- `--max-rps`: 每秒最大请求数（默认: 10.0）

#### JSON翻译参数

- `--file, -f`: 输入文件（必需）
- `--output, -o`: 输出文件
- `--source-lang`: 源语言
- `--target-lang, -t`: 目标语言（默认: zh）

#### HTML翻译参数

- `--file, -f`: 输入文件（必需）
- `--output, -o`: 输出文件
- `--source-lang`: 源语言
- `--target-lang, -t`: 目标语言（默认: zh）

#### ePub翻译参数

- `--file, -f`: 输入文件（必需）
- `--output, -o`: 输出文件（必需）
- `--source-lang`: 源语言
- `--target-lang, -t`: 目标语言（默认: zh）

#### 服务器参数

- `--host`: 绑定地址（默认: 0.0.0.0）
- `--port, -p`: 监听端口（默认: 8000）
- `--debug`: 启用调试模式

### 环境变量配置

```bash
# API配置
export ARK_API_KEY=your_api_key
```

### 支持的语言

| 代码  | 语言名称   | 代码      | 语言名称   |
| --- | ------ | ------- | ------ |
| zh  | 中文（简体） | zh-Hant | 中文（繁体） |
| en  | 英语     | de      | 德语     |
| fr  | 法语     | es      | 西班牙语   |
| it  | 意大利语   | pt      | 葡萄牙语   |
| ja  | 日语     | ko      | 韩语     |
| th  | 泰语     | vi      | 越南语    |
| ru  | 俄语     | ar      | 阿拉伯语   |

### 支持的模型

#### 🐢 慢车道模型 (RPM=5000, 80并发)
适用于免费额度使用、稳定翻译场景

| 模型ID | 特点 | 推荐场景 |
|--------|------|----------|
| `doubao-seed-translation-250915` | 免费额度、稳定可靠 | 日常翻译、免费使用 |

#### 🚀 快车道模型 (RPM=30000, 500并发)
适用于大批量、高并发翻译场景

| 模型ID | 特点 | 推荐场景 |
|--------|------|----------|
| `deepseek-v3-250324` | 高性能、低成本 | 大批量文档翻译 |
| `deepseek-v3-1-terminus` | 高性能 | 大批量文档翻译 |
| `doubao-seed-1-6-lite-251015` | 轻量快速 | 实时翻译 |
| `doubao-seed-1-6-251015` | 高性能 | 批量处理 |
| `doubao-1-5-vision-pro-32k-250115` | 视觉能力、大上下文 | 图文混合翻译 |
| `doubao-1.5-vision-pro-250328` | 视觉能力 | UI文本翻译 |
| `doubao-1.5-vision-lite-250315` | 轻量视觉 | 快速图文翻译 |
| `doubao-1-5-ui-tars-250428` | UI优化 | 界面文本翻译 |

**配置方式**: 编辑 `models.json` 文件，将需要使用的模型按优先级排列

```json
[
  "doubao-seed-translation-250915",  // 优先使用免费额度
  "deepseek-v3-250324",              // 备用快车道
  "doubao-seed-1-6-251015"           // 备用快车道
]
```

系统会自动根据模型类型选择对应的并发策略，无需手动配置。详见 [CONCURRENCY_OPTIMIZATION.md](CONCURRENCY_OPTIMIZATION.md)


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

### 项目结构说明

详细的项目结构说明请参考 [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) 文件。

---

**注意**: 本工具专为高效利用豆包API的免费额度而设计，强烈建议在处理大型文件时监控翻译进度，确保符合每日额度限制。