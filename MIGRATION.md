# 项目重构迁移说明

本文档说明了从旧版本 doubao-batch-translator 项目重构到新版本"一核多壳"架构的迁移指南。

## 🔄 架构变化概览

### 旧架构问题
- 现有的Python `translator.py` 与 TypeScript 代码并存，结构混乱
- CLI和服务器功能耦合，难以维护
- 缺乏统一的核心翻译逻辑
- 文件处理逻辑散落在各个地方

### 新架构优势
- **核心模块化**: 统一的核心翻译器，支持多种处理器
- **接口清晰**: 核心与处理器分离，便于扩展
- **异步优化**: 全面异步化，提升性能
- **配置统一**: 集中配置管理
- **错误处理**: 完善的异常体系

## 📁 文件结构变化

### 旧结构
```
doubao-batch-translator/
├── src/                          # TypeScript源码
│   ├── cli.ts
│   ├── services/batchTranslator.ts
│   ├── processors/htmlProcessor.ts
│   └── ...
├── translator.py                 # Python翻译脚本
├── translation_work.json
└── package.json
```

### 新结构
```
doubao-batch-translator/
├── core/                         # 核心模块 ⭐
│   ├── __init__.py
│   ├── config.py                # 配置管理
│   ├── exceptions.py            # 异常定义
│   └── translator.py            # AsyncTranslator核心类
├── processors/                   # 处理器模块 ⭐
│   ├── __init__.py
│   ├── json_worker.py           # JSON翻译处理器
│   └── html_worker.py           # HTML翻译处理器
├── server/                       # HTTP服务器模块 ⭐
│   ├── __init__.py
│   └── api.py                   # FastAPI服务器
├── examples/                     # 示例文件
├── main.py                       # 统一入口 ⭐
├── requirements.txt              # Python依赖 ⭐
└── README.md                     # 详细文档 ⭐
```

## 🔧 迁移步骤

### 步骤1: 环境准备

```bash
# 1. 清理旧版本文件（可选）
# 保留src/目录作为参考，但核心功能迁移到新架构

# 2. 安装新版本依赖
pip install -r requirements.txt

# 3. 设置API密钥
export ARK_API_KEY=your_api_key_here
```

### 步骤2: 功能迁移

#### 2.1 JSON翻译功能

**旧方式:**
```bash
python translator.py translation_work.json --output translated.json
```

**新方式:**
```bash
python main.py json --file translation_work.json --output translated.json
```

**向后兼容:**
- 旧命令仍然可用（translator.py保留）
- 新命令提供更好的错误处理和进度显示

#### 2.2 HTML翻译功能

**旧方式:** 
通过TypeScript CLI工具处理HTML文件

**新方式:**
```bash
python main.py html --file input.html --output translated.html
```

**改进:**
- 智能识别URL和代码块
- 更准确的中文文本检测
- 属性翻译支持

#### 2.3 HTTP服务器功能

**旧方式:** 
需要自己搭建HTTP服务

**新方式:**
```bash
python main.py server --port 8000
```

**改进:**
- OpenAI兼容的API格式
- 内置健康检查
- 自动文档生成

### 步骤3: 代码迁移

#### 3.1 Python代码迁移

**旧代码结构:**
```python
# translator.py - 混合了翻译逻辑和文件处理
class BatchTranslator:
    def translate_all(self, data: List[Dict], progress_callback=None) -> List[Dict]:
        # 翻译逻辑
        pass

class JsonTranslator:
    def translate(self, api_key: str):
        # 文件处理逻辑
        pass
```

**新代码结构:**
```python
# core/translator.py - 专注翻译逻辑
class AsyncTranslator:
    async def translate_batch(self, texts: List[str], ...) -> List[Dict]:
        # 核心翻译逻辑
        pass

# processors/json_worker.py - 专注文件处理
class JSONProcessor:
    async def translate_file(self, input_file: str, ...) -> Dict[str, Any]:
        # 文件处理逻辑
        pass
```

#### 3.2 配置文件迁移

**旧配置方式:**
```bash
# 通过环境变量和参数
export ARK_API_KEY=key
python translator.py file.json --concurrent 5
```

**新配置方式:**
```bash
# 支持更多配置选项
export ARK_API_KEY=key
export MAX_CONCURRENT=5
export MAX_REQUESTS_PER_SECOND=50.0
python main.py json --file file.json --max-concurrent 3 --max-rps 30
```

### 步骤4: 测试验证

#### 4.1 功能测试

```bash
# 测试JSON翻译
python main.py json --file examples/translation_work.json --verbose

# 测试HTML翻译
python main.py html --file examples/sample.html --verbose

# 测试HTTP服务器
python main.py server --debug
```

#### 4.2 API测试

```bash
# 启动服务器后测试
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-translation-250915",
    "messages": [
      {
        "role": "user",
        "content": "Hello, world!"
      }
    ],
    "target_language": "zh"
  }'
```

## 📊 性能对比

| 特性 | 旧版本 | 新版本 | 改进 |
|------|--------|--------|------|
| 并发控制 | ✅ 基础并发 | ✅ 智能并发 | 更精确的频率控制 |
| 批处理 | ✅ 固定批大小 | ✅ 动态优化批大小 | 减少API调用次数 |
| 断点续传 | ✅ 有 | ✅ 增强 | 更可靠的进度保存 |
| 错误处理 | ⚠️ 基础 | ✅ 完善 | 更好的错误恢复 |
| 日志记录 | ✅ 基础 | ✅ 结构化 | 更清晰的日志信息 |
| 类型检查 | ❌ 弱 | ✅ 强 | 更好的代码质量 |
| 文档 | ⚠️ 简单 | ✅ 详细 | 更完整的文档 |

## 🚨 注意事项

### 兼容性说明

1. **Python版本要求**: 需要Python 3.13+
2. **依赖变更**: 新增了FastAPI、BeautifulSoup等依赖
3. **API变更**: HTTP API改为OpenAI兼容格式

### 行为变化

1. **批处理逻辑**: 新版本会根据文本长度动态调整批大小
2. **错误处理**: 更严格的异常处理，可能影响现有错误处理逻辑
3. **日志格式**: 采用结构化日志，格式发生变化

### 迁移检查清单

- [ ] Python 3.13+ 环境准备
- [ ] API密钥重新设置
- [ ] 依赖包重新安装
- [ ] 现有脚本测试验证
- [ ] HTTP API客户端更新
- [ ] 监控和日志系统更新

## 🔧 故障排除

### 常见迁移问题

#### 1. 依赖安装失败
```bash
# 解决方案
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. API密钥错误
```bash
# 验证密钥
echo $ARK_API_KEY
# 或者命令行指定
python main.py json --file data.json --api-key YOUR_KEY
```

#### 3. 端口占用
```bash
# 检查端口占用
lsof -i :8000
# 使用其他端口
python main.py server --port 8080
```

#### 4. 权限问题
```bash
# 确保文件读写权限
chmod +x main.py
chmod 644 *.json
```

### 回滚策略

如果迁移出现问题，可以回滚到旧版本：

```bash
# 1. 恢复旧版本文件
git checkout HEAD~1

# 2. 使用旧的翻译脚本
python translator.py translation_work.json

# 3. 清理新版本文件
rm -rf core/ processors/ server/
```

## 🎯 未来规划

### 短期目标 (1-2周)
- [ ] 监控生产环境运行状况
- [ ] 收集用户反馈
- [ ] 修复发现的问题

### 中期目标 (1-2月)
- [ ] 添加更多文件格式支持 (XML, CSV等)
- [ ] 实现缓存机制优化性能
- [ ] 添加Web管理界面

### 长期目标 (3-6月)
- [ ] 支持多种翻译服务 (Google, Baidu等)
- [ ] 实现分布式翻译
- [ ] 添加翻译质量评估

---

**迁移成功标志**: 所有原有功能正常工作，新功能测试通过，无关键错误日志。