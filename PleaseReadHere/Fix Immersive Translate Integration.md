# Chat Conversation

Note: _This is purely the output of the chat conversation and does not contain any raw data, codebase snippets, etc. used to generate the output._

### User Input

我现在想测试一下server的功能是否正常
我之前在沉浸式翻译这个插件里面把地址填的http://0.0.0.0:8000/v1/chat/completions

我需要说一下
doubao-seed-translation-250915这个模型是垂类模型 或者说专用模型
不兼容opanai的格式
他长这样:
在请求模型时，需要传入源语言source_language和目标语言target_language对象参数,参考代码如下

curl --location --request POST 'https://ark.cn-beijing.volces.com/api/v3/responses' \
--header "Authorization: Bearer $ARK_API_KEY" \
--header "Content-Type: application/json" \
--data-raw '{
  "model": "doubao-seed-translation-250915",
  "input": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "若夫淫雨霏霏，连月不开，阴风怒号，浊浪排空",
          "translation_options": {
            "source_language": "zh", 
            "target_language": "en"
          }
        }
      ]
    }
  ]
}'

*：source_language参数可不填，翻译模型可自适应源语言；target_language 参数必填

模型限制
上下文窗口
4k
最大输入Token长度
1k
最大输出Token长度
3k
TPM
500k
RPM
5k

这个项目的server就是把发往doubao-seed-translator的openai请求先变成特殊请求
把收到的特殊报文再变成兼容openai的报文

因为沉浸式翻译这个插件的自定义translation service只支持openai格式的
所以 咱们这个项目 可以让doubao-seed-translator在沉浸式翻译里用

但我上次测试了一下,发现好像并不成功

### Planner Response

我来帮你测试和调试server功能。首先让我了解一下项目的结构和server的实现代码。

*Listed directory [doubao-batch-translator](file:///home/louis/doubao-batch-translator) *

*Searched filesystem*

*Semantic searched codebase*

### Planner Response

让我查看完整的 server/api.py 文件，特别是它如何与 `AsyncTranslator` 交互以及如何调用 doubao-seed-translation 模型：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

*Viewed [client.py](file:///home/louis/doubao-batch-translator/core/client.py) *

### Planner Response

现在我来查看 [core/config.py](cci:7://file:///home/louis/doubao-batch-translator/core/config.py:0:0-0:0) 以了解配置和端点 URL：

*Viewed [config.py](file:///home/louis/doubao-batch-translator/core/config.py) *

### Planner Response

好的，我不能查看 [.env](cci:7://file:///home/louis/doubao-batch-translator/.env:0:0-0:0) 文件。让我查看 models.json 和启动服务器进行测试：

*Viewed [models.json](file:///home/louis/doubao-batch-translator/models.json) *

### Planner Response

现在我对代码有了清晰的理解。让我启动服务器并进行测试。首先启动服务器，然后发送测试请求：

*User accepted the command `cd /home/louis/doubao-batch-translator && python main.py server --port 8000 --debug 2>&1`*

*Checked command status*

### Planner Response

服务器应该正在启动，让我发送一个测试请求：

*User accepted the command `curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-translation-250915",
    "messages": [{"role": "user", "content": "Hello, how are you?"}],
    "target_language": "zh"
  }'`*

### Planner Response

服务器工作正常！翻译结果返回了 "您好，最近怎么样？"，说明 doubao-seed-translation 模型的特殊请求格式转换是成功的。

让我再进行几个测试，验证不同场景：

*User accepted the command `curl -s http://localhost:8000/ | head -5`*

*User accepted the command `curl -s http://localhost:8000/v1/models | head -10`*

*User accepted the command `curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-translation-250915",
    "messages": [{"role": "user", "content": "The quick brown fox jumps over the lazy dog"}],
    "target_language": "zh"
  }' | python3 -m json.tool 2>/dev/null || cat`*

*Checked command status*

*Checked command status*

### Planner Response

让我重新运行健康检查和模型列表查询：

*User accepted the command `curl -s http://localhost:8000/ && echo "" && curl -s http://localhost:8000/v1/models | python3 -m json.tool`*

### Planner Response

所有基本测试都通过了：
- ✅ 健康检查 `/` 返回正常
- ✅ 模型列表 `/v1/models` 返回正常
- ✅ 翻译请求 `/v1/chat/completions` 正常工作，成功将英文翻译成中文

现在让我检查一下服务器日志，看看有没有潜在问题，并且模拟沉浸式翻译插件可能发送的请求格式：

*Checked command status*

### Planner Response

让我模拟沉浸式翻译插件的典型请求格式（它通常不传 `target_language` 参数，而是在 system prompt 里说明目标语言）：

*User accepted the command `curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-translation-250915",
    "messages": [
      {"role": "system", "content": "You are a translator. Translate the following text to Chinese."},
      {"role": "user", "content": "Hello world, this is a test."}
    ]
  }' | python3 -m json.tool`*

### Planner Response

翻译成功了（"您好，世界，这里是一次测试"）！

## 测试结论

**服务器功能正常！** 我刚才的所有测试都成功了：

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 健康检查 `/` | ✅ | 返回 `{"status":"healthy"}` |
| 模型列表 `/v1/models` | ✅ | 正常返回模型信息 |
| 翻译请求（带 `target_language`）| ✅ | "Hello, how are you?" → "您好，最近怎么样？" |
| 翻译请求（无 `target_language`，默认 zh）| ✅ | 正常工作 |
| 较长文本翻译 | ✅ | "The quick brown fox..." → "快速的棕色狐狸跳过了懒惰的狗。" |

---

既然服务器工作正常，但你之前测试不成功，问题可能出在以下几个方面：

### 可能的问题排查：

1. **地址问题**：你在沉浸式翻译里填的是 `http://0.0.0.0:8000/v1/chat/completions`。如果是从浏览器插件访问，应该用 `http://127.0.0.1:8000/v1/chat/completions` 或 `http://localhost:8000/v1/chat/completions`。`0.0.0.0` 是服务器绑定地址，客户端连接时应该用 `127.0.0.1` 或 `localhost`。

2. **浏览器/插件的网络限制**：某些浏览器可能会阻止插件访问本地服务。

3. **服务器没有启动**：确保运行 `python main.py server --port 8000` 时服务器在后台运行。

---

**你想让我帮你进一步排查吗？** 请告诉我：
1. 你上次测试时服务器启动了吗？有没有看到启动日志？
2. 沉浸式翻译插件显示的错误信息是什么？
3. 你的浏览器是什么？(Chrome/Firefox/Edge?)

*User accepted the command `python main.py server --port 8000`*

### User Input

在网页上 在沉浸式翻译里配置后 在网页上启动 发现所有的外文都被翻译成了OK @[TerminalName: python, ProcessId: 59361] 

### Planner Response

我找到问题了！所有外文都被翻译成 "OK" 是因为服务器代码中的**心跳检测逻辑**有问题。

让我查看服务器的运行日志来确认：

*Read terminal output: python*

### Planner Response

**确认问题了！** 日志显示所有请求都被判定为"空消息列表，返回心跳成功"，这说明沉浸式翻译插件发送的请求格式与我们的 Pydantic 模型不兼容。

让我添加一些调试日志来看看插件实际发送的是什么格式的请求：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

### Planner Response

我发现问题了！[Message](cci:2://file:///home/louis/doubao-batch-translator/server/api.py:28:0-30:16) 模型强制要求 `content` 是 `str` 类型，但沉浸式翻译插件可能发送的 `content` 是一个数组或其他格式。同时，我们需要添加调试日志来查看实际收到的请求。

让我修复这个问题：

*Edited relevant file*

### Planner Response

现在我需要修改请求处理逻辑，使用新的 [get_text_content()](cci:1://file:///home/louis/doubao-batch-translator/server/api.py:36:4-52:17) 方法，并添加调试日志来查看实际收到的请求：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

*Edited relevant file*

### Planner Response

现在让我终止旧的服务器进程并使用调试模式重启，这样可以看到详细日志：

### User Input

这是我在沉浸式翻译的文档里看到的内容:
请求

    method: POST
    content-type: application/json
    body
        source_lang: 源 {语言代码}
        target_lang: 目标 {语言代码}
        text_list: 翻译文本字符串的数组

响应

    response
        translations: 数组
            detected_source_lang: 翻译原文本 {语言代码}
            text: 已翻译的文本

保留占位符

目的是针对网页翻译中的非文本内容进行占位，翻译之后保留该特殊符号，我们会在翻译完成之后将相应的非文本内容进行还原
格式

字符串数组

    0: 成对分隔符的左边
    1: 成对分隔符的右边
    2: 标签分隔符

例子

    例子 1: [', ']

   原文: 😁 hello 👏🏻 wrold
占位原文: {0} hello {1} world

占位译文: {0} 你好 {1} 世界
   译文: 😁 你好 👏🏻 世界

    例子 2: ['', '', 'b']

   原文: 😁 hello 👏🏻 wrold
占位原文: <b0></b0> hello <b1></b1> world

占位译文: <b0></b0> 你好 <b1></b1> 世界
   译文: 😁 你好 👏🏻 世界

### Planner Response

原来如此！**沉浸式翻译使用的是自己的 API 格式，而不是 OpenAI 格式！**

你之前看到所有内容都变成 "OK" 的原因是：沉浸式翻译发送的请求格式不包含 `messages` 字段，而是用 `source_lang`, `target_lang`, `text_list`，所以我们的服务器把它当成了空消息，返回了心跳响应 "OK"。

我需要添加一个新的端点来支持沉浸式翻译的格式：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

*Edited relevant file*

### Planner Response

现在添加沉浸式翻译的API端点：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

*Edited relevant file*

### Planner Response

现在我需要先终止旧的服务器进程（端口8001的那个），然后重启服务器进行测试：

*User accepted the command `pkill -f "python main.py server"`*

*User accepted the command `cd /home/louis/doubao-batch-translator && python main.py server --port 8000 --debug 2>&1`*

*Checked command status*

*User accepted the command `curl -s -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "source_lang": "en",
    "target_lang": "zh",
    "text_list": ["Hello world", "How are you?", "This is a test"]
  }' | python3 -m json.tool`*

### Planner Response

**完美！** 沉浸式翻译的 `/translate` 端点工作正常了！翻译结果：
- "Hello world" → "哈喽，世界"
- "How are you?" → "你好吗？"  
- "This is a test" → "这是一次测试"

现在让我验证一下服务器健康检查和 OpenAI 兼容端点也都正常：

*User accepted the command `echo "=== 健康检查 ===" && curl -s http://localhost:8000/ && echo -e "\n\n=== 沉浸式翻译 /translate ===" && curl -s -X POST http://localhost:8000/translate -H "Content-Type: application/json" -d '{"target_lang":"zh","text_list":["Good morning"]}' | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['translations'][0]['text'])"`*

### Planner Response

**全部测试通过！** 

现在你需要在**沉浸式翻译**插件中修改配置：

## 📝 配置步骤

在沉浸式翻译插件的「自定义翻译服务」设置中，将地址改为：

```
http://127.0.0.1:8000/translate
```

**注意：**
1. 使用 `127.0.0.1` 而不是 `0.0.0.0`（`0.0.0.0` 是服务器绑定地址，客户端应该用 `127.0.0.1` 或 `localhost`）
2. 端点路径是 `/translate`（不是之前的 `/v1/chat/completions`）

---

## 🔧 服务启动命令

确保服务器在后台运行：
```bash
python main.py server --port 8000
```

---

现在可以在网页上试试沉浸式翻译了！翻译应该能正常工作了。

*User accepted the command `python main.py server --port 8001`*

*User accepted the command `python main.py server --port 8001`*

### User Input

@[TerminalName: python, ProcessId: 59361] 
我按你说的做了 这次稍微有点不一样了 终于不是全部翻译成ok了

### Planner Response

让我看看服务器现在的日志，了解一下现在的情况：

*Read terminal output: python*

### Planner Response

我看到了两个问题：

1. **422 Unprocessable Content** - 请求格式验证失败，说明沉浸式翻译发送的请求格式与我们的模型定义不完全匹配
2. **307 Temporary Redirect** - 插件发送的是 `/translate/` (带斜杠)，被重定向到 `/translate`

让我检查沉浸式翻译实际发送的请求格式，并修复这些问题：

*User accepted the command `pkill -f "python main.py server"`*

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

### Planner Response

问题是 `text_list` 是必填项但没有默认值。沉浸式翻译插件可能发送的字段名不同，或者格式略有差异。让我添加一个原始请求日志来查看实际收到的内容，并使用更宽松的请求模型：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

### Planner Response

我需要修改端点来接收原始 JSON 内容并添加调试日志，这样可以看到沉浸式翻译实际发送的是什么：

*Edited relevant file*

### Planner Response

现在启动服务器进行测试：

*User accepted the command `cd /home/louis/doubao-batch-translator && python main.py server --port 8000 2>&1`*

*Checked command status*

*User accepted the command `curl -s -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{"source_lang": "en", "target_lang": "zh", "text_list": ["Hello"]}' && echo ""`*

### Planner Response

服务器测试正常。

现在你可以在**沉浸式翻译**插件中使用新的配置：

## 📝 配置步骤

在沉浸式翻译插件的「自定义翻译服务」设置中：

**URL 地址**：
```
http://127.0.0.1:8000/translate
```

（注意端口是 **8000**，不是 8001）

**然后启动服务器**：
```bash
python main.py server --port 8000
```

---

现在服务器会：
1. 打印收到的原始请求内容（方便调试）
2. 支持 `/translate` 和 `/translate/` 两种路径
3. 灵活匹配字段名（`text_list`, `texts`, [text](cci:1://file:///home/louis/doubao-batch-translator/server/api.py:36:4-52:17) 等都支持）

请在浏览器中测试一下，然后告诉我服务器日志显示什么。我想看看沉浸式翻译插件实际发送的请求格式是什么。

*User accepted the command `python main.py server --port 8000`*

### User Input

@[TerminalName: python, ProcessId: 59361] 现在可以了吗

### Planner Response

端口 8000 上已经有服务器在运行了（是我之前启动的）。让我查看一下那个服务器的日志：

*Checked command status*

*Read terminal output: python*

### Planner Response

现在我看清楚问题了！沉浸式翻译插件发送的请求格式是：

```json
{"model": "doubao-seed-translation-250915", "temperature": 0, "messages": []}
```

这是 **OpenAI 格式**，不是自定义翻译服务格式！你在沉浸式翻译插件里选择的应该是 "OpenAI" 翻译服务类型，而不是"自定义翻译服务"。

## 问题原因

沉浸式翻译有两种配置方式：
1. **自定义翻译服务** → 使用 `text_list` 格式 → 地址填 `/translate`
2. **OpenAI 兼容服务** → 使用 `messages` 格式 → 地址填 `/v1/chat/completions`

你现在配置的是 **OpenAI 格式**，但路径填了 `/translate`，所以请求被发到了错误的端点。

---

## 解决方案

**方案 A**：在沉浸式翻译中使用 **OpenAI 格式**（推荐）

在沉浸式翻译的设置中：
- 翻译服务类型选择：**OpenAI** 或 **ChatGPT**
- API 地址填：`http://127.0.0.1:8001/v1/chat/completions`
- API Key：随便填一个（如 `sk-xxx`，我们服务器不验证）
- 模型名：`doubao-seed-translation-250915`

不过 OpenAI 格式有个问题，沉浸式翻译发送的 messages 是空的。让我再查看一下沉浸式翻译 OpenAI 模式的请求格式，可能它用的是另一个字段来传文本。

让我修改一下 OpenAI 端点，记录更多信息：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

### Planner Response

我需要修改 `/v1/chat/completions` 端点，让它也接收原始请求以便调试：

*Edited relevant file*

### Planner Response

现在还需要修复后面翻译调用部分，确保使用正确的变量（[model](cci:1://file:///home/louis/doubao-batch-translator/core/config.py:59:4-61:82) 而不是 `request.model`）：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

*Edited relevant file*

### Planner Response

现在重启服务器进行测试：

*User accepted the command `pkill -f "python main.py server" && sleep 2 && cd /home/louis/doubao-batch-translator && python main.py server --port 8000 2>&1`*

*Checked command status*

*User accepted the command `curl -s http://localhost:8000/ && echo ""`*

### Planner Response

服务器已经在 8000 端口运行了。

现在请在你的浏览器中用沉浸式翻译测试一下，然后告诉我服务器日志显示的内容。根据日志输出的 `[OpenAI] 原始请求: ...`，我们可以看到插件实际发送的是什么格式。

你当前在沉浸式翻译里配置的是哪种服务类型？
1. **自定义翻译服务** - 地址应该是 `http://127.0.0.1:8000/translate`
2. **OpenAI** - 地址应该是 `http://127.0.0.1:8000/v1/chat/completions`

请确认一下配置，然后在网页上测试翻译，完成后我会检查日志来诊断问题。

### User Input

@[TerminalName: python, ProcessId: 59361] 现在还是ok 我用的是http://127.0.0.1:8000/v1/chat/completions

### Planner Response

让我查看服务器日志，看看它收到的实际请求是什么：

*Read terminal output: python*

### Planner Response

我明白了！问题很清楚了：

**沉浸式翻译插件发送的请求 `messages` 是空数组 `[]`！**

```json
{"model": "doubao-seed-translation-250915", "temperature": 0, "messages": []}
```

这说明沉浸式翻译的 **OpenAI 翻译服务模式**，它可能是在另一个地方传递待翻译的文本，或者你选择的服务类型不对。

---

## 🔧 解决方案

沉浸式翻译插件有多种服务类型，请确认你选择的是哪一种：

### 检查你的沉浸式翻译设置

在沉浸式翻译的设置页面，请查看：

1. **翻译服务** 部分 → 你选的是什么？
   - 如果是 "OpenAI" → 它应该把文本放在 messages 里，但现在是空的，说明配置可能有问题
   - 如果是 "自定义接口(Beta)" → 需要用 `/translate` 端点

2. 请确认你在沉浸式翻译里配置的 **完整设置**（可以截图给我看看）

---

### 临时解决方案

让我先尝试通过查看沉浸式翻译的官方文档来确定正确的配置方式：

*Searched web for 沉浸式翻译 immersive translate OpenAI 自定义接口 API 格式 配置教程*

### Planner Response

根据搜索结果，我现在理解了。沉浸式翻译的 OpenAI 模式在发送**连接测试**时会发送空的 messages，这就是为什么你看到这么多空消息。

问题是：**沉浸式翻译发送的实际翻译请求在哪里？**

从日志来看，所有请求都是空消息，这说明：
1. 沉浸式翻译可能只是在**测试连接**阶段
2. 或者它在翻译时使用了不同的端点/格式

让我查阅一下沉浸式翻译的自定义接口文档：

*Read URL content from /docs/services/custom/ *

*Viewed content chunk*

*Viewed content chunk*

### Planner Response

现在我确认了！沉浸式翻译的**自定义接口（Custom API）**格式是：

**请求格式:**
```json
{
  "source_lang": "en",
  "target_lang": "zh", 
  "text_list": ["Hello", "World"]
}
```

**响应格式:**
```json
{
  "translations": [
    {"detected_source_lang": "en", "text": "你好"},
    {"detected_source_lang": "en", "text": "世界"}
  ]
}
```

我们的 `/translate` 端点已经支持这个格式了！问题是你在沉浸式翻译中选择的是 **OpenAI** 服务类型，而不是 **自定义 API**。

---

## ✅ 正确配置步骤

请按照以下步骤在沉浸式翻译中配置：

### 1. 开启开发者设置
- 打开沉浸式翻译设置 → 点击**开发者设置**
- 开启 **"启用 Beta 测试功能"**

### 2. 配置自定义翻译服务
- 回到**翻译服务**页面
- 找到 **"自定义 API"** 或 **"Custom API"**
- 设置 URL 为: `http://127.0.0.1:8000/translate`

### 3. 将"自定义 API"设为默认翻译服务

---

完成后，服务器日志应该会显示类似这样的内容：
```
[沉浸式翻译] 原始请求: {"source_lang": "en", "target_lang": "zh", "text_list": [...]}
[沉浸式翻译] 完成 (0.5s): 10 条
```

请试试看！

### User Input

沉浸式翻译里还有一些别的设置:
System Prompt(The dialogue sent to Doubao Seed Translation as a system, where {{text}} represents the text content of the paragraph, {{from}} represents the language of the paragraph, and {{to}} represents the target language.)：
You are a professional {{to}} native translator who needs to fluently translate text into {{to}}.

## Translation Rules
1. Output only the translated content, without explanations or additional content (such as "Here's the translation:" or "Translation as follows:")
2. The returned translation must maintain exactly the same number of paragraphs and format as the original text
3. If the text contains HTML tags, consider where the tags should be placed in the translation while maintaining fluency
4. For content that should not be translated (such as proper nouns, code, etc.), keep the original text.
5. If input contains %%, use %% in your output, if input has no %%, don't use %% in your output{{title_prompt}}{{summary_prompt}}{{terms_prompt}}

## OUTPUT FORMAT:
- **Single paragraph input** → Output translation directly (no separators, no extra text)
- **Multi-paragraph input** → Use %% as paragraph separator between translations

## Examples
### Multi-paragraph Input:
Paragraph A
%%
Paragraph B
%%
Paragraph C
%%
Paragraph D

### Multi-paragraph Output:
Translation A
%%
Translation B
%%
Translation C
%%
Translation D

### Single paragraph Input:
Single paragraph content

### Single paragraph Output:
Direct translation without separators

Prompt(Prompt sent as user to Doubao Seed Translation, where {{text}} denotes the text content of the paragraph, {{from}} denotes the language of the paragraph, {{to}} denotes the target language, {{content_type}} denotes the type of the original text, with possible values of `html` or `text`, and {{html_only}} is a value that will only be present if the original contains the html tag. The value of {{html_only}} is only available if the original text contains html tags.)：Translate to {{to}} (output translation only):

{{text}}

Multiple Prompt(Multiple paragraph translation instructions: When you need to translate multiple paragraphs, the system will send requests to Doubao Seed Translation as a user. In the request: - {{from}} indicates the source language - {{to}} indicates the target language - {{text}} indicates the content to be translated, with multiple paragraphs separated by \n\n%%\n\n Advanced customization: For more precise control, you can use the {{yaml}} format. In this case, AI will return results in YAML format, each item must include the text field (translation field name). The original text field name sent to AI by the system is text. Output example: ``` - id: 1 text: First paragraph translation - id: 2 text: Second paragraph translation ```)：

Subtitle Prompt(Subtitle translation instructions: The system will send requests to Doubao Seed Translation as a user. In the request: - {{from}} indicates the source language - {{to}} indicates the target language - {{text}} indicates the content to be translated, with multiple paragraphs separated by \n\n%%\n\n Advanced customization: For more precise control, you can use the {{yaml}} format. In this case, AI will return results in YAML format, each item must include the translation field (translation field name, default is translation). The original text field name passed to AI by the system is text. Output example: ``` - id: 1 text: Source translation: Translation - id: 2 text: Source translation: Translation ```)：
Translate to {{to}}:

{{text}}

我之前注意到专用模型和普通模型的区别,所以把这些prompt都给去掉了
是否是这个原因导致message数组为空?

### Planner Response

**是的！这很可能就是问题所在！**

你把 Prompt 都去掉了，所以沉浸式翻译在构建 OpenAI 请求时，没有内容可以放入 `messages` 数组，导致它变成空数组 `[]`。

---

## 🎯 解决方案

你有两个选择：

### 方案 A：恢复 Prompt（使用 OpenAI 格式）

把 **Prompt** 字段恢复为简单格式：
```
{{text}}
```

这样沉浸式翻译就会把待翻译的文本放入 messages 中。由于你使用的是 `doubao-seed-translation-250915` 专用翻译模型，我们的服务器会自动处理，不需要 system prompt。

**注意**：你可以把 System Prompt 留空或者删掉，只需要保留 Prompt 字段包含 `{{text}}`

---

### 方案 B：使用自定义 API 模式（推荐）

因为 doubao-seed-translation 是**专用翻译模型**，不需要任何 prompt，使用自定义 API 模式更干净。

1. 在沉浸式翻译的**开发者设置**中启用 Beta 功能
2. 在翻译服务中选择 **"自定义 API"**
3. 设置 URL 为：`http://127.0.0.1:8000/translate`

这种方式不需要任何 prompt 配置，插件会直接发送 `text_list` 格式的请求。

---

## 我的建议

**先试试方案 A**，因为你已经配置好 OpenAI 模式了：

1. 找到 **Prompt** 设置
2. 填入：`{{text}}`
3. System Prompt 可以留空
4. 保存并测试

如果方案 A 不行，再切换到方案 B（自定义 API 模式）。

*User accepted the command `python main.py server --port 8001`*

### User Input

@[TerminalName: python, ProcessId: 59361] 这次基本上是成功了,但我想知道的是
为什么日志里有那么多的提示词的内容?
说什么"你是一个专业的简体中文母语译者，需将文本流畅地翻译为简体中文。\n\n##"
这显然是废话,doubao-seed-translation不需要这些

### Planner Response

太好了，翻译成功了！🎉

关于你的问题：

## 为什么日志里有 prompt？

这是因为**沉浸式翻译使用 OpenAI 格式**时，它会按照标准 OpenAI 流程发送：
- [system](cci:1://file:///home/louis/doubao-batch-translator/core/client.py:144:4-153:9) 消息：包含 System Prompt（那些"你是专业翻译"的废话）
- `user` 消息：包含待翻译的文本

**但不用担心！** 我们的服务器**只提取 user 消息中的文本**，然后发送给 doubao-seed-translation 模型。那些 system prompt 完全被忽略了，不会发送给翻译模型。

```
沉浸式翻译发送:                    我们实际使用:
┌─────────────────────────────┐    ┌──────────────────┐
│ system: "你是专业翻译..."    │ ──→│ (忽略)           │
│ user: "Hello world"         │ ──→│ "Hello world"    │
└─────────────────────────────┘    └──────────────────┘
                                           ↓
                               doubao-seed-translation
                                           ↓
                                     "你好世界"
```

---

## 如果你想让日志更干净

我可以修改日志，只显示实际翻译的文本，而不是整个原始请求。要我改吗？

另外，你可以在沉浸式翻译里把 **System Prompt 留空**，只保留 **Prompt** 字段为 `{{text}}`，这样请求会更简洁（虽然不影响翻译结果）。

---

**总结**：翻译已经正常工作了！那些 prompt 只是沉浸式翻译发过来的，我们的服务器已经正确忽略它们，只用文本内容调用专用翻译模型。

### User Input

我给你看一下沉浸式翻译文档的内容:
AI Prompt 配置指南
概述

沉浸式翻译支持自定义 AI 翻译的 Prompt 配置，让高级用户可以根据自己的需求调整翻译行为。本文档将详细介绍配置方式、支持的变量以及高级用法。
支持的变量
基础变量

    {{text}} - 需要翻译的文本内容
    {{from}} - 源语言
    {{to}} - 目标语言
    {{content_type}} - 原文本的类型（html 或 text）

上下文变量

    {{title_prompt}} - 网页标题（当可用时）
    {{summary_prompt}} - 网页上下文摘要（当可用时）
    {{terms_prompt}} - 相关专业术语（当可用时）

配置方式
1. System Prompt(systemPrompt)

以系统身份发送给 AI 的翻译请求。用于设定 AI 的角色和基本规则。
2. Prompt(prompt)

以用户身份发送给 AI 的对话，包含实际需要翻译的内容。
3. System Multiple Prompt(systemMultiplePrompt)

当段落数大于 1 时，以系统身份发送给 AI 的翻译请求。用于处理多段落翻译场景。
4. Multiple Prompt(multiplePrompt)

多段落翻译时，以用户身份发送的请求。支持使用分隔符或 YAML 格式。
5. Subtitle Prompt(subtitlePrompt)

当需要翻译字幕时，以用户身份发送给 AI 的对话，包含实际需要翻译的内容。
默认配置示例

如果只收集到一个段落，那么默认会走单段落的 Prompt, 如果收集到多个段落，那么默认会走多段落的 Prompt，大多数情况会是多段落。多段落的默认分隔符是 %%，我们故意使用这个不太常见的分隔符来减少大模型的幻觉。你可以用此 Prompt 为基础去修改为你需要的 Prompt, 以下是默认的 Prompt 配置：
单段落翻译

systemPrompt: |
    你是一位专业的 {{to}} 母语翻译者，需要流畅地将文本翻译成 {{to}}。

    ## 翻译规则
    1. 仅输出翻译内容，不要包含解释或其他额外内容（例如"翻译如下："或"以下是翻译："等）
    2. 返回的翻译必须保持与原文完全相同的段落数和格式
    3. 如果文本包含 HTML 标签，在保持流畅性的同时，请考虑标签在翻译中的位置
    4. 对于不应翻译的内容（如专有名词、代码等），请保留原文
    5. 直接输出翻译（无分隔符，无额外文本）{{title_prompt}}{{summary_prompt}}{{terms_prompt}}
prompt: |
  翻译成 {{to}}（仅输出翻译）：
  
  {{text}}

多段落翻译

multipleSystemPrompt: |
    你是一位专业的 {{to}} 母语翻译者，需要流畅地将文本翻译成 {{to}}。

    ## 翻译规则
    1. 仅输出翻译内容，不要包含解释或其他额外内容（例如"翻译如下："或"以下是翻译："等）
    2. 返回的翻译必须保持与原文完全相同的段落数和格式
    3. 如果文本包含 HTML 标签，在保持流畅性的同时，请考虑标签在翻译中的位置
    4. 对于不应翻译的内容（如专有名词、代码等），请保留原文{{title_prompt}}{{summary_prompt}}{{terms_prompt}}

    ## 输入输出格式示例

    ### 输入示例：
    Paragraph A

    %%

    Paragraph B

    %%

    Paragraph C

    %%

    Paragraph D

    ### 输出示例：
    Translation A

    %%

    Translation B

    %%

    Translation C

    %%

    Translation D

multiplePrompt: |
  翻译成 {{to}}：
  
  {{text}}
subtitlePrompt: |
  翻译成 {{to}}：
  
  {{text}}

高级用法（YAML 格式）

对于需要更精确控制的场景（比如多步骤输出），可以使用 YAML 格式进行配置：
高级变量

    {{yaml}} - YAML 格式的输入数据

默认的 'yaml' 变量大概长这样；

- id: 1
  text: Hello world
- id: 2
  text: How are you?

我们默认期待大模型的输出是这样的：

- id: 1
  text: 你好世界
- id: 2
  text: 你好吗？

如果你使用默认的 {{yaml}}，那么你需要在 prompt 中把这个期望表达清楚。如果你希望修改默认和响应的 yaml 格式，这无法通过沉浸式翻译设置页面中的 UI 来解决，你必须直接编辑沉浸式翻译 JSON 格式的用户配置。

用户配置编辑路径： 设置页->开发者设置->Edit Full User Config (编辑前，请备份你的用户配置)

你可以在用户配置的 JSON 中找到翻译服务的配置（如果没有，直接按照这个结构添加即可）：

{
  ...
  "translationServices": {
    "openai": {
       ...
      }
  },
  ...

yaml 变量由 env.imt_yaml_item 组成，所以你可以修改 imt_yaml_item 的格式，像下面这样：

  "translationServices": {
    "openai": {
       "env": {
          "imt_yaml_item": "- id: {{id}}\n  source: {{text}}"
        }
    }
   }

另一个特殊变量是 imt_subtitle_yaml_item, 和 imt_yaml_item 类似，用于翻译字幕的 YAML item.

其他的 env 变量，你可以添加任何 env变量，直接在 prompt 中按照 {{变量名}} 的格式使用，比如如下默认的env变量：

    {{imt_source_field}} - 原文字段名（默认：text）
    {{imt_trans_field}} - 译文字段名（默认：text）
    {{imt_sub_source_field}} - 字幕原文字段名
    {{imt_sub_trans_field}} - 字幕译文字段名

包括 title_prompt,summary_prompt,terms_prompt背后也是通过 env来配置的，默认如下：

        "title_prompt": "\n\n## 上下文感知\n文档元数据：\n标题：《{{imt_title}}》",
        "summary_prompt": "\n\n## 上下文感知\n文档元数据：\n摘要：{{imt_theme}}...",
        "terms_prompt": "\n\n必需术语：翻译时必须使用以下术语，如果 'source':'target' 中 source == target，则保持源术语不变。\n\n 术语 -> \n\n {{imt_terms}}",
        "sub_summary_prompt": "\n\n## 上下文感知\n文档元数据：\n类型：字幕\n摘要：{{imt_theme}}...",
        "sub_terms_prompt": "\n\n必需术语：翻译时必须使用以下术语，如果 'source':'target' 中 source == target，则保持源术语不变。\n\n 术语 -> \n\n {{imt_terms}}"

其中 imt_title, imt_theme,imt_terms 为特殊变量，由系统注入，imt_title为标题，imt_theme为整个网页的总结，imt_terms为模型提取的关键术语。

    注意： imt_theme, imt_terms 是专有服务提取的，目前仅为 Pro 会员提供。

YAML Prompt 示例

systemPrompt: |
  你是一个专业、可靠的机器翻译引擎。
  {{title_prompt}}{{summary_prompt}}{{terms_prompt}}

multiplePrompt: |
    你将收到一个 YAML 格式的输入，包含带有 "id" 和 "{{imt_source_field}}" 字段的条目。输入内容如下：

    <yaml>
    {{yaml}}
    </yaml>

    对于 YAML 中的每个条目，将 "{{imt_source_field}}" 字段的内容翻译成 {{to}}，{{html_only}} 将翻译结果写回该条目的 "{{imt_source_field}}" 字段。

    以下是期望格式的示例：

    {{normal_result_yaml_example}}

    请直接返回翻译后的 YAML，不要包含 <yaml> 标签或任何额外信息。
subtitlePrompt: |
    你将收到一个 YAML 格式的字幕输入，包含带有 "id" 和 "{{imt_sub_source_field}}" 字段的条目。输入内容如下：

    <yaml>
    {{yaml}}
    </yaml>

    对于 YAML 中的每个条目，将 "{{imt_sub_source_field}}" 字段的内容翻译成 {{to}}，{{html_only}} 将翻译结果写回该条目的 "{{imt_sub_source_field}}" 字段。

    以下是期望格式的示例：

    {{subtitle_result_yaml_example}}

    请直接返回翻译后的 YAML，不要包含 <yaml> 标签或任何额外信息。

其中 html_only 为特殊变量，仅翻译的原文为 HTML 格式时才有，值为： \n\n注意：如果文本包含 HTML 标签，请在翻译后考虑标签在翻译结果中的位置，同时保持结果的流畅性。 , 当用户主动在 AI 翻译服务中设置 开启"富文本翻译"时才会有这个变量存在。否则为空。

normal_result_yaml_example 在 env 中设置，默认为：

<example>
Input:
  - id: 1
    {{imt_source_field}}: Source
Output:
  - id: 1
    {{imt_trans_field}}: Translation
</example>

subtitle_result_yaml_example 在 env 中设置，默认值为：

<example>
Input:
  - id: 1
    {{imt_sub_source_field}}: ...
  - id: 2
    {{imt_sub_source_field}}: ...
  - id: 3
    {{imt_sub_source_field}}: ...
Output:
  - id: 1
    {{imt_sub_source_field}}: ...
  - id: 2
    {{imt_sub_source_field}}: ...
  - id: 3
    {{imt_sub_source_field}}: ...
</example>

你可以在 env 中覆盖它。
高级示例：反思式翻译

这个示例展示了如何使用 YAML 格式实现更复杂的翻译流程，包含初步翻译和优化翻译两个步骤：

env:
  imt_source_field: source
  imt_trans_field: step2  # 最终译文使用 step2 字段
  imt_sub_source_field: source
  imt_sub_trans_field: step2
  imt_yaml_item: |-
    - id: {{id}}
      {{imt_source_field}}: {{text}}
  imt_subtitle_yaml_item: |-
    - id: {{id}}
      {{imt_sub_source_field}}: {{text}}

systemPrompt: |
  你是一个专业、可靠的机器翻译引擎。
  {{title_prompt}}{{summary_prompt}}{{terms_prompt}}

multiplePrompt: |
  以下是 YAML 输入：
  <yaml>
  {{yaml}}
  </yaml>
  
  请按照以下步骤操作：
  1. 从提供的 YAML 对象中提取 "source" 字段的内容。
  2. 将提取的内容翻译成 {{to}}。将初步翻译结果放入 step1 字段。
  3. 优化 step1 中的初步翻译，使其在 {{to}} 中更加自然和易于理解。 
     将优化后的翻译放入 step2 字段。
  4. 将结果格式化为包含 id、step1 和 step2 字段的 YAML 数组，如下例所示：
  
  - id: 1 
    step1: 初步翻译
    step2: 优化翻译
  
  请直接返回翻译后的 YAML，不要包含任何 <example_output> 标签或额外信息。

工作流程说明

    输入格式：

    - id: 1
      source: "Hello world"
    - id: 2
      source: "How are you?"

    AI 处理步骤：
        Step 1: 进行初步翻译
        Step 2: 优化翻译，使其更自然流畅

    输出格式：

    - id: 1
      step1: "你好世界"
      step2: "你好，世界"
    - id: 2
      step1: "你怎么样？"
      step2: "你好吗？"

高级自定义选项

你可以在扩展配置页面 -> 开发者设置 -> User Config 里编辑更多 UI 里无法编辑的自定义配置，适用于高级用户，参数讲解详见最后的说明。当前内置的 config 可以在这里，点击 Click to expand the final config 找到。
User Rules

通过 Rules 可以对特定的网站进行自定义配置，决定哪些内容是否需要被翻译，或调整网页样式等。

[
  {
    "matches": "www.google.com",
    "selectors": [".title"]
  },
  {
    "matches": "twitter.com",
    "selectors": [".text"],
    "excludeSelectors": ["nav", "footer"]
  }
]

使用 matches 来匹配对应的网站。允许通配符，如 *.google.com,www.google.com/test/*,file://*

使用 selectors 会覆盖智能翻译范围，仅翻译该选择器匹配到的元素。

使用 excludeSelectors 可以排除元素，不翻译该位置。

使用 selectors.add 会在默认的基础上添加一些 selectors

使用 selectors.remove 会在默认的基础上减少一些 selectors

[
  {
    "matches": "www.google.com",
    "selectors.add": ["baidu.com"],
    "excludeSelectors": ["buzzing.cc"]
  }
]

如果译文导致页面错位，文字重叠等边缘情况，可以使用 globalStyles 调整网页样式来修复。比如 youtube 的标题，用来移除原网页的最大高度。

{
  "matches": "www.google.com",
  "globalStyles": { ".title": "max-height:unset;" }
}

Injected CSS

通过 Injected CSS 可以向全局注入自定义网页样式。可以搭配 Rules 的 translationClasses 一起使用。

.immersive-translate-target-wrapper img {
  width: 16px;
  height: 16px;
}

也可以像常规的网页样式管理器那样，对网站进行更加个性化的样式设计。（甚至利用 display:none 去广告）

.title {
  color: red;
}

User Config

通过 Config 可以自定义此插件的相关配置，如翻译服务、特定语言语言翻译选项等。

{
  "translationService": "tencent",
  "translationServices": {
    "tencent": {
      "secretId": "xxx",
      "secretKey": "xxx",
      "matches": ["twitter.com"]
    }
  },
  "translationUrlPattern": {
    "excludeMatches": ["www.google.com"]
  },
  "translationLanguagePattern": {
    "matches": ["en"]
  },
  "translationTheme": "none",
  "translationThemePatterns": {
    "underline": {
      "matches": ["discord.com"]
    }
  },
  "sourceLanguageUrlPattern": {
    "en": {
      "matches": ["*.google.com"]
    }
  },
  "generalRule": {
    "_comment": "",
    "normalizeBody": "",
    "injectedCss": [],
    "additionalInjectedCss": [],
    "wrapperPrefix": "smart",
    "wrapperSuffix": "smart",
    "isPdf": false,
    "isTransformPreTagNewLine": false,
    "urlChangeDelay": 20,
    "isShowUserscriptPagePopup": true,
    "observeUrlChange": true,
    "paragraphMinTextCount": 8,
    "paragraphMinWordCount": 2,
    "blockMinTextCount": 32,
    "blockMinWordCount": 5,
    "containerMinTextCount": 18,
    "lineBreakMaxTextCount": 0,
    "globalAttributes": {},
    "globalStyles": {},
    "selectors": [],
    "preWhitespaceDetectedTags": ["DIV", "SPAN"],
    "stayOriginalSelectors": [],
    "additionalSelectors": [],
    "atomicBlockTags": [],
    "excludeSelectors": [],
    "additionalExcludeSelectors": [],
    "translationClasses": [],
    "excludeTags": [],
    "metaTags": ["META", "SCRIPT", "STYLE", "NOSCRIPT"],
    "additionalExcludeTags": [],
    "stayOriginalTags": ["CODE", "TT", "IMG", "SUP"],
    "additionalStayOriginalTags": [],
    "inlineTags": [],
    "additionalInlineTags": [],
    "extraInlineSelectors": [],
    "additionalInlineSelectors": [],
    "extraBlockSelectors": [],
    "allBlockTags": [],
    "pdfNewParagraphLineHeight": 2.4,
    "pdfNewParagraphIndent": 1.2,
    "pdfNewParagraphIndentRightIndentPx": 130,
    "fingerCountToToggleTranslagePageWhenTouching": 4
  },
  "rules": [
    {
      "matches": "www.google.com",
      "selectors": [".class"]
    }
  ]
}

其中，rules 里的规则字段，可以使用 generalRule 里的全部字段。rules 拥有最高优先级，当匹配到特定网站的某一条 rule 时，会合并 generalRule 和该 rule 的规则。

介绍一些 Config 常见的字段。
允许渲染普通 HTML 标签

去 开发设置 -> Edit Full User Config

编辑 "enableRenderHtmlTag": true
不在 popup 面板里展示未配置的翻译服务

"showUnconfiguredTranslationServiceInPopup": false
翻译服务配置

使用 translationService 选择默认的翻译引擎，当前支持：

| "bing"
| "transmart"
| "google"
| "deepl"
| "openai"
| "gemini"
| "baidu"
| "volc"
| "youdao"
| "caiyun"
| "tencent"
| "openl"

使用 translationServices 配置各家翻译服务的 apikey，不同服务商需要的参数不一样，它们的 API 密钥均可在各自官网的开发者中心申请。

如腾讯翻译君，需要配置 secretId, secretKey。你可以前往腾讯云申请 API 密钥，每月免费字符 500 万。具体申请过程参考这里

"translationServices": {
  "tencent": {
    "secretId": "xxx",
    "secretKey": "xxx",
    "matches":["twitter.com"],
    "limit": 3,
    "apiUrl":"",
    "maxTextGroupLengthPerRequest": 25,
    "maxTextLengthPerRequest": 1800
  }
}

matches 字段，为特定网站使用该翻译服务。

limit字段，指定该翻译服务的每秒最多请求数（有些服务会限制每秒最大请求数）。

maxTextGroupLengthPerRequest 字段，每次请求最大的段落数

maxTextLengthPerRequest 字段，每次请求最大的字符数

apiUrl 可以自定义翻译接口的地址。
openai temperature 设置

openai 的"temperature"参数用于调节语言模型的输出文本的随机性和创造性。设置较低的温度值（如 0.1 或 0.2）会生成更确定、一致且可预测的文本，而较高的温度值（如 0.8 或 1.0）则使输出更随机、多样化，增加文本的创造性。

具体设置在开发设置 -> Edit Full User Config 中，找到 openai 对应的字段，插入一条新字段 temperature 即可完成设置。

示例如下

  "translationServices": {
    "openai": {
      "model": "gpt-3.5-turbo",
      "provider": "custom",
      "temperature": 1
    }
  },

总是翻译特定网站

translationUrlPattern 配置总是翻译的网站，以及永不翻译的网站。

    matches 配置总是翻译的网站，
    excludeMatches 配置永不翻译的网站。

配置值可以是域名或带有 * 的网址，比如：www.google.com/mail/*

"translationUrlPattern": {
    "matches": ["stackoverflow.com"]
    "excludeMatches": ["www.google.com/mail/*"]
}

总是翻译特定语言

translationLanguagePattern, 配置总是翻译的语言，以及永不翻译的语言。

    matches 配置总是翻译的语言，比如 en,
    excludeMatches 配置永不翻译的语言。

译文显示格式

translationTheme 为译文的显示格式，当前支持以下样式：

| "none"
| "dashed"
| "dotted"
| "underline"
| "mask"
| "paper"
| "highlight"
| "blockquote"
| "weakening"
| "italic"
| "bold"
| "thinDashed";

对应的中文名：

{
  "none": "无",
  "dashed": "虚线下划线",
  "dotted": "点状下划线",
  "underline": "直线下划线",
  "mask": "模糊效果",
  "paper": "白纸阴影效果",
  "highlight": "高亮",
  "blockquote": "引用样式",
  "weakening": "弱化",
  "italic": "斜体",
  "bold": "加粗",
  "thinDashed": "细虚线下划线"
}

translationThemePatterns 可以为不同网站配置不同的译文样式。

"translationThemePatterns": {
  "underline": {
    "matches": ["discord.com"]
  }
}

类 gpt 页面流消息翻译

{
  "matches": ["chat.openai.com"], //类 gpt 网址
  "excludeSelectors": [".markdown *"],
  "aiRule": {
    "streamingSelector": ".result-streaming.markdown",
    "messageWrapperSelector": ".markdown",
    "streamingChange": true
  }
}

自定义专业术语的翻译

最新支持 AI 术语库 功能，注意该术语仅支持 AI 翻译服务。

AI 术语库默认不支持谷歌/微软这类机器翻译术语

机器翻译模型采用的是占位符替换，使用术语库可能会导致翻译质量下降。

强制开启方法（不推荐）：

【开发者设置】 -> 【Edit Full User Config】

{
  ....
  "enableMachineTranslateTerms":true,
  ...
}

Rules

rules 为数组对象，可以配置针对特别网站的规则，比如让推特只翻译某一部分区域：

{
  "rules": [
    {
      "id": "twitter",
      "matches": ["twitter.com", "mobile.twitter.com", "tweetdeck.twitter.com"],
      "selectors": [
        "[data-testid='tweetText']",
        ".tweet-text",
        ".js-quoted-tweet-text",
        "[data-testid='card.layoutSmall.detail'] > div:nth-child(2)",
        "[data-testid='developerBuiltCardContainer'] > div:nth-child(2)",
        "[data-testid='card.layoutLarge.detail'] > div:nth-child(2)"
      ],
      "extraInlineSelectors": ["[data-testid=\"tweetText\"] div"]
    }
  ]
}

当前内置的 rules 可以在这里 找到。

以下挑选部分重要字段进行说明：

export interface Rule {
  // 匹配网站
  id?: string; //系统每个适配的规则都有自己的 id，如果用户想要复用这条规则在此基础之上变动的话，需要在自己的规则上加上这个相应的 id 就可以复用了
  matches?: string | string[]; // 该条 Rule 将仅匹配此处的网站。
  excludeMatches?: string | string[]; // 排除特定的网站。
  selectorMatches?: string | string[]; // 用选择器来匹配，而无需指定所有 url
  excludeSelectorMatches?: string | string[]; // 排除规则，同上。

  // 指定翻译范围
  selectors?: string | string[]; // 仅翻译匹配到的元素
  excludeSelectors?: string | string[]; // 排除元素，不翻译匹配的元素
  excludeTags?: string | string[]; // 排除 Tags，不翻译匹配的 Tag

  // 追加翻译范围，而不是覆盖
  additionalSelectors?: string | string[]; // 追加翻译范围。在智能翻译的区域，追加翻译位置。
  additionalExcludeSelectors?: string | string[]; // 追加排除元素，让智能翻译不翻译特定位置。
  additionalExcludeTags?: string | string[]; // 追加排除 Tags

  // 保持原样
  stayOriginalSelectors?: string | string[]; // 匹配的元素将保持原样。常用于论坛网站的标签。
  stayOriginalTags?: string | string[]; // 匹配到的 Tag 将保持原样，比如 `code`

  // Block or Inline
  extraBlockSelectors?: string | string[]; // 额外的选择器，匹配的元素将作为 block 元素，独占一行。
  extraInlineSelectors?: string | string[]; // 额外的选择器，匹配的元素将作为 inline 元素。

  inlineTags?: string | string[]; // 匹配的 Tag 将作为 inline 元素
  preWhitespaceDetectedTags?: string | string[]; // 匹配的 Tag 将自动换行

  // 译文样式
  translationClasses?: string | string | string[]; // 为译文添加额外的 Class

  // 全局样式
  globalStyles?: Record<string, string>; // 修改页面样式，若译文导致页面错乱，这个很有用。`
  globalAttributes?: Record<string, Record<string, string>>; // 修改页面元素的属性

  // 嵌入样式
  injectedCss?: string | string[]; // 嵌入 CSS 样式
  additionalInjectedCss?: string | string[]; // 追加 CSS 样式，而不是直接覆盖。

  // 上下文
  wrapperPrefix?: string; // 译文区域的前缀，默认为 smart，根据字数决定是否换行。
  wrapperSuffix?: string; // 译文区域的后缀

  // 译文换行字数
  blockMinTextCount?: number; // 将译文作为 block 的最小字符数，否则译文为 inline 元素。
  blockMinWordCount?: number; // 同上。如果希望它们始终换行，可以都填 0.

  // 内容可翻译的最小字数
  containerMinTextCount?: number; // 智能识别时，元素最少包含的字符数，才会被翻译，默认为 18
  paragraphMinTextCount?: number; // 原文段落的最小字符数，大于数字的内容将被翻译
  paragraphMinWordCount?: number; // 原文段落的最小单词数

  // 长段落强制换行字数
  lineBreakMaxTextCount?: number; // 开启翻译长段落时，强制进行分行的段落最大字符数。

  // 启动翻译的时机
  urlChangeDelay?: number; // 进入页面后，延迟多少毫秒开始翻译。为了等网页的初始化，目前默认为 250ms
  observeUrlChange?: boolean; // 检测 url 地址发生变化时，再次启动翻译，默认为 true。

  // 移动端
  isShowUserscriptPagePopup?: boolean; // 在移动设备上展示页面内的浮窗，默认为 true.
  fingerCountToToggleTranslagePageWhenTouching?: number; // 四指触摸则翻译，可以设置为 0，2，3，4，5

  // AI streaming 翻译
  aiRule: {
    streamingSelector: string; //gpt 网页中标记正在翻译元素的选择器
    messageWrapperSelector: string; // 消息正文选择器
    streamingChange: boolean; //类 gpt 网页反复的消息是增量更新还是全量更新。gpt 是增量
  };
}

Rules matches 匹配逻辑

这部分介绍关于 match 的匹配方式，怎样来匹配到对应的域名，这里我们讲的是单个 match 的，实际匹配的时候 matches 是个数组，会尝试让每个 match 都去匹配，只要有一个匹配中，就算命中。

首先让我们先确定好输入形式，即我们的 match 支持哪些形式的合法输入

    省略主机号的url，如 immersivetranslate.com
    一个合法的 url，有自己的协议，域名，或者路径，如 https://immersivetranslate.com
    上面都不满足的情况下，会将输入转换成一个正则表达式去处理，在此基础上再去匹配一些特定的规则

确定好输入之后，让我们简单做个分类以更好地区分基本的url和带有正则表达式的url：

    匹配单个网站的 match，如 https://immersivetranslate.com 或者省略协议的 immersivetranslate.com
    掺有正则表达式特殊符号的 match，如 https://*/*sub.info=*fmoviesz.to* 这里会匹配特定的搜索url参数，这里我们的程序会自动将后面那一串转化为正则表达式以此来匹配对应的url，转换之后的结果为/^https:\/\/[^/]+?\/.*?sub.info=.*?fmoviesz.to.*?\/?$/。这样做的好处在于大幅降低了配置match的复杂性

在区分之后，对于这两类 match 我们分开来讲对应的匹配逻辑，在代码中也是如此，这两类的匹配逻辑是分开的。在代码中我们是通过这个表达式 !match.includes("*") && match.includes("://") 来区分这两类的 match 的

对于匹配单个站点的match的字符串，即不含正则表达式相关符号的，需要考虑的问题有三个：

    对于省略网络协议的 match 的处理：如 immersivetranslate.com 我们会直接判断 match 是否等于url的 hostname，等于则匹配成功，即不会将 match 解析为 URL，将其作为 hostname 来判断
    对于多级路由的处理，分为两种情况
        完整的 match，如 https://immersivetranslate.com/docs/advanced/,这类是合法的 URL，我们会将其解析为 URL，提取协议，主机名，端口号以及路径名来比较，当全部相等时则匹配成功
        省略了网络协议的match，如 immersivetranslate.com/docs/advanced/ 由于这类是不合法的 url，对于这类会将其归类到正则表达式的逻辑处理里面去

当上面的匹配策略都不生效时，就会到我们的兜底匹配，即将其识别为一个正则表达式，我们会对 match 进行转换，将其转换成一个合法的正则表达式。这部分的例子可以参照这个

    https://*/*sub.info=*fmoviesz.to* ==> /^https:\/\/[^/]+?\/.*?sub.info=.*?fmoviesz.to.*?\/?$/

最后总结一下我们的处理逻辑，1. 判断 url 的 hostname 是否等于 match 字符串，等于则匹配成功 2. 判断匹配所有的 url 的 match，例如 *，*://*等等 3. 判断 match 是否为一个合法的 url，我们会尝试比较 match 和 url 是否相等。具体比较协议，端口，主机名，路径名，相等则成功 4. 判断 match 为一个正则表达式，将其转换成一个合法的正则表达式并尝试匹配 5. 都不满足的话，则匹配失败
翻译服务自定义请求头和请求体参数

在【开发者设置】->【Edit Full User Config】

{
  ...
  "translationServices": {
    "claude": {
      "headerConfigs": {
        "anthropic-version": "2023-06-01",
        "anthropic-dangerous-direct-browser-access": "true"
      },
      "bodyConfigs": {
        "max_tokens": 2048
      }
    }
  ...
}
}

Gemini 系列模型用户如何自定义配置

由于 Gemini 系列模型的特殊性，插件内置了部分设置。用户若想覆盖插件内置的设置，可以参考以下配置：

{
...
"translationServices": {
    "gemini": {
      "modelsOverrides": [
        // 指定要重写的模型，这里重写了 gemini-2.5-flash 和 gemini-2.5-flash-lite 两个模型
        "models": [
          "gemini-2.5-flash",
          "gemini-2.5-flash-lite"
        ]
      ]
    }
  },
...
}

让插件严格遵循自定义提示词

    为减少大语言模型出现“幻觉”的问题，插件内置了翻译质量校验机制。系统会通过对比响应文本与请求文本的 Token（令牌）数量比例，来判断翻译结果的合理性。当该比例异常（过高或过低）时，当前结果会被视为无效并自动切换到备用翻译方案。

    如果您的自定义提示词属于非翻译类任务（如扩写、润色或其他指令），可能会导致 Token 比例不符合常规标准。为此，您可以通过设置如下参数，强制让程序严格执行您的自定义指令，跳过比例校验：

...
  "translationServices": {
    "claude": {
      "strictPrompt": true
    }
  ...

修改默认翻译缓存自动清理时长

插件针对翻译缓存，默认 30 天自动清除。目的是为了防止缓存过大，导致后续翻译卡顿。可以如下操作修改默认值

在【开发者设置】->【Edit Full User Config】

{
  cacheMaxAgeDay: 30,
  ...
}

自定义多语言提示词

下面展示了 openai 对于翻译日语/中文繁体的提示词修改

{
  ...
  "translationServices": {
    "openai.add": {
        "langOverrides": [
          {
          "id": "auto2ja",
          "systemPrompt": "あなたはプロフェッショナルで正確な翻訳エンジンです。翻訳されたテキストのみを返し、説明は一切行いません。",
          "prompt": "次のテキストを{{to}}に翻訳してください：\n\n<text>\n{{text}}\n</text>\n\n翻訳結果を直接出力し、追加のテキストやタグは一切含めないでください。",
          "multiplePrompt": "\"id\"フィールドと \"{{imt_source_field}}\" フィールドを含むYAML形式の入力が与えられます。以下が入力です：\n\n<yaml>\n{{yaml}}\n</yaml>\n\nYAMLの各エントリについて、\"{{imt_source_field}}\" フィールドの内容を {{to}} に翻訳してください。そのエントリの \"{{imt_source_field}}\" フィールドに翻訳結果を書き戻してください。\n\n以下は期待される形式の例です：\n\n{{normal_result_yaml_example}}\n\n追加のタグを一切含めずに、翻訳されたYAMLを直接返してください。",
          "subtitlePrompt": "YAML形式のビデオ字幕セットの \"{{imt_sub_source_field}}\" フィールドを {{to}} に翻訳します。以下がYAML形式の元の字幕です：\n\n<yaml_subtitles>\n{{yaml}}\n</yaml_subtitles>\n\n各字幕エントリの \"{{imt_sub_source_field}}\" フィールドのみを簡体字中国語に翻訳してください。\"id\" フィールドは翻訳や変更をしないでください。\n\n翻訳された字幕を同じYAML形式で出力し、各字幕エントリを一行ずつにしてください。\"id\" フィールドは変更せず、\"{{imt_sub_source_field}}\" フィールドに {{to}} の翻訳を含めてください。\n\n請直接返回翻訳後の YAML，不要添加任何額外的標籤。"
        },
        {
          "id": "auto2zh-TW",
          "systemPrompt": "你是一個專業的、地道的翻譯引擎。你只返回翻譯的文本，不做任何解釋。",
          "prompt": "將以下文本翻譯成 {{to}}：\n\n<text>\n{{text}}\n</text>\n\n直接輸出翻譯結果，不要添加任何額外的文本或標籤。",
          "multiplePrompt": "你將會得到一個包含 \"id\" 和 \"{{imt_source_field}}\" 欄位的 YAML 格式輸入。以下是輸入內容：\n\n<yaml>\n{{yaml}}\n</yaml>\n\n對於 YAML 中的每個條目，將 \"{{imt_source_field}}\" 欄位的內容翻譯成 {{to}}。將翻譯結果寫回每個條目的 \"{{imt_source_field}}\" 欄位。\n\n以下是期望的格式範例：\n\n{{normal_result_yaml_example}}\n\n請直接返回翻譯後的 YAML，不要添加任何額外的標籤。",
          "subtitlePrompt": "你將會翻譯一組 YAML 格式的影片字幕中的 \"{{imt_sub_source_field}}\" 欄位為 {{to}}。以下是原始字幕的 YAML 格式：\n\n<yaml_subtitles>\n{{yaml}}\n</yaml_subtitles>\n\n請僅翻譯每個字幕條目中的 \"{{imt_sub_source_field}}\" 欄位為簡體中文。不要翻譯或更改 \"id\" 欄位。\n\n以相同的 YAML 格式輸出翻譯後的字幕，每個字幕條目各佔一行。\"id\" 欄位應保持不變，\"{{imt_sub_source_field}}\" 欄位應包含你的 {{to}} 翻譯結果。\n\n請直接返回翻譯後的 YAML，不要添加任何額外的標籤。"
        }
        ]
      }
    }
  ...
}

高级自定义选项实战
实用小技巧

这部分会介绍一些即插即用的保姆级配置。

将这些配置一键复制，打开开发者设置，展开 Edit Full User Config ，复制到最后一项即可，注意不要忘记给前一项加上逗号，以及最后一项不能加逗号
不能用的翻译服务太多了，如何在插件面板里只展示能用的翻译服务

  "showUnconfiguredTranslationServiceInPopup": false

如何让不同的站点默认选择不同的翻译服务？例如有的网站我想要好一点但要花钱的翻译效果，有的网站我只需要免费能看的翻译就行了

注意看，眼前这个配置叫翻译服务，他配置了谷歌翻译，让有关推特的相关站点的翻译都使用他去翻译，因为 google 翻译是免费的，推特是冲浪的，只要能看懂就行了。

仔细看，他还配置了 deepl 的翻译服务，他让 deepl 专门去翻译 scihub 这种容错率低的需要高精确的学术网站

  "translationServices": {
    "google": {
      "matches":["https://twitter.com"]
    },
    "deepl": {
      "matches":["https://www.sci-hub.se"]
    }
  }

    ⚠️ 请注意，若您希望翻译属于同一域名的所有网站，简单使用 _.twitter.com 或 https://twitter.com/ 是无效的。正确的做法应参照上文所示。这是因为 _.twitter.com 仅能匹配子域名如 xxx.twitter.com，而不包括顶级域名本身。

网站适配案例

这部分会介绍一些插件自己对常见的网站的 rules，通过实际例子来理解高级自定义选项。同时为了简洁，这里只会介绍最常用的字段，比如 selectors , excludeSelectors 等等，如果你对这部分内容感兴趣的话，欢迎联系我们，我们会继续更新相关的内容。

在介绍之前，一个非常关键的东西就是沉浸式翻译插件的工作原理，同时也是一个插件的工作原理。在此之前，需要有一定的 HTML 、CSS 、 JavaScript 基础，相关基础可以在 MDN 网站上学习。Okay，话不多说，让我们走进沉浸式翻译的内部一探究竟。插件的工作机制简单来说，就是向网页中注入第三方脚本，这个脚本可以对网页结构，样式，甚至行为进行相当自由地魔改。

我们的沉浸式翻译插件也不例外，让我们来简单分析一下沉浸式翻译它干了个什么事

    获取需要翻译的元素集合
    翻译元素集合中的文本
    将翻译的结果插入到元素集合中

Okay，但是再仔细想想，自然而然就会带出接下来两个问题

    我们还需要确定哪些元素需要被翻译，如果全盘翻译，往往会破坏用户的沉浸式体验，像一些简单明了的按钮，或者导航栏。
    将翻译的结果插入到元素集合中也会带来一个新的挑战，如何保证插入的结果与原生网页保持一致，不去影响原生网页的样式。

我们的 Rules 的核心就是解决上述两个问题。因为作为插件，沉浸式翻译面对的是市面上所有的网页，加起来可能超过几十万，甚至几百万的网页，这些网页的页面结构，使用的技术也是相差殆尽。因为网页的不同，导致了一个通用的逻辑是几乎不可能的，很难找到一套通用的逻辑，能够去适配所有的网站内容。这样看来，解决方法似乎只有挨着挨着对每个网站进行单独的适配。接着为了更方便地适配，我们又利用了配置即代码的思想，将适配的工作转换成了配置字段的工作。这样的另一个好处就是，用户也可以参与到适配工作起来。

同时，在进行配置的时候，最好不要直接使用下面几个字段，这样会导致覆盖掉原先的配置项，而是采用 selector.add excludeSelector.add 这几个字段以继承的方式，在原先的配置项的基础上进行修改

下面，我们将会介绍沉浸式翻译对站点的适配工作

下面是推特的 Rules，为了简洁，我们将关注其中的几个关键字段，剩余字段可以结合上文中的 Rules 理解

[
  {
    "id": "twitter",
    "matches": [
      "twitter.com",
      "mobile.twitter.com",
      "tweetdeck.twitter.com",
      "pro.twitter.com",
      "https://platform.twitter.com/embed*"
    ],
    "selectors": [
      // 指定翻译的元素，只会翻译选择器匹配到的元素
      "[data-testid=\"tweetText\"]",
      ".tweet-text",
      ".js-quoted-tweet-text",
      "[data-testid='card.layoutSmall.detail'] > div:nth-child(2)",
      "[data-testid='developerBuiltCardContainer'] > div:nth-child(2)",
      "[data-testid='card.layoutLarge.detail'] > div:nth-child(2)",
      "[data-testid='cellInnerDiv'] div[data-testid='UserCell'] > div> div:nth-child(2)",
      "[data-testid='UserDescription']",
      "[data-testid='HoverCard'] div[dir=auto]",
      "[data-testid='HoverCard'] span[dir=auto]",
      "[data-testid='HoverCard'] [role='dialog'] div[dir=ltr]",
      "[data-testid='birdwatch-pivot'] div[dir=ltr]"
    ],
    "excludeSelectors": [
      // 不会翻译的被 CSS 选择器选中的元素
      "[aria-describedby][role=button]",
      "header",
      "[data-testid='radioGroupplayback_rate'] div",
      "[data-testid='userFollowIndicator']",
      "[class='css-901oao r-14j79pv r-37j5jr r-n6v787 r-16dba41 r-1cwl3u0 r-bcqeeo r-qvutc0']",
      "[class='css-175oi2r r-1wbh5a2 r-dnmrzs']"
    ],
    "globalStyles": {
      // 全局样式，强制覆盖掉原样式
      "[data-testid='card.layoutLarge.detail'] > div:nth-child(2)": "-webkit-line-clamp: unset;",
      "[data-testid='card.layoutSmall.detail'] > div:nth-child(2)": "-webkit-line-clamp: unset;",
      "[data-testid='tweetText']": "-webkit-line-clamp: unset;"
    }
  }
]

    selector: 指定翻译的元素集合

    为什么需要这个字段
        因为不是所有元素都有文字且需要翻译的，提供这样一个字段既可以保证性能又可以保证用户的沉浸式体验

    举个例子
        在推特中，如果我们不指定 selector，那么他将会将页面中的所有识别为英文的文字都进行翻译一遍，如下图，用户的昵称往往是不需要翻译的。

    用户主页

    字段含义

        "selectors": [ // 会被翻译的 CSS 选择器集合
        "[data-testid=\"tweetText\"]",
      ]

    这里数组的每一项都是一个 CSS 选择器，用来选择页面中的需要翻译的元素，这里我们以第一个选择器为例，如下图所示，第一个选择器命中的是所有推文的元素

    tweet

    excludeSelectors: 不会被翻译的元素集合

    为什么需要这个字段
        因为一个仅翻译的选择器是不够的，可能会出现，匹配中的元素却不需要翻译的，即两者可能存在重合的部分，因此需要再设置一个字段来排除掉不需要翻译的元素
        由于页面结构是非常复杂的，提供这样两个配置项，让配置更加灵活
        相关的优先级是：对于同等选择器，selectors > excludeSelectors，剩下的依靠 CSS 优先级来比较

    字段含义

        "excludeSelectors": [ // 不会翻译的被 CSS 选择器选中的元素
        "[aria-describedby][role=button]",
      ],

    还是看第一个，这里我们排除掉了关注按钮的这个翻译 twitter-follow

    globalStyles：添加全局样式，强制覆盖掉原先的样式

    为什么需要这个字段
        在某些情况下，因为原先网页的相关 CSS 样式，会导致整个的翻译展示效果不是很好，出现被截断，不换行等等效果
        通过这个字段，提供一种暴力的解决方案，直接修改原生网页的 CSS 属性来解决

    字段含义

          "globalStyles": {
        // 全局样式，强制覆盖掉原样式
        "[data-testid='card.layoutLarge.detail'] > div:nth-child(2)": "-webkit-line-clamp: unset;",
        "[data-testid='card.layoutSmall.detail'] > div:nth-child(2)": "-webkit-line-clamp: unset;",
        "[data-testid='tweetText']": "-webkit-line-clamp: unset;"
      }

    -webkit-line-clamp 这个属性用来控制显示的行数，多余的行会被截断，这里设置成 unset ，可以保证译文不会被这个属性所截断

自定义网站适配

关于适配规则，当然你也可以自定义规则，进入到插件选项页面，点击开发者设置，展开 Edit User Rules ，在这里进行各个网站的自定义适配。下面结合实际规则进行讲解

[
  {
    "selectors.remove": [
      "[data-testid=\"tweetText\"]"
    ],
    "selectors.add": [
      ""
    ],
    "excludeSelectors.add":[
      ""
    ],
    "excludeSelectors.remove:[
      ""
    ],
    "id": "twitter"
  }
]

这个规则会让推特页面的推文不进行翻译。下面详细介绍字段的含义

id 是沉浸式翻译目前已经定义好的相关网站的集合，每个 id 都对应相关的站点。id 的好处有两个

    使用 id 能继承沉浸式翻译之前的适配规则，用户可以在这基础上进行增删
    使用 id 就不用写繁琐的匹配字段了

下面介绍一些沉浸式翻译内置服务的常见的 id

    "isEbook" epub 阅读器页面的配置
    "isEbookBuilder" 生成 epub 双语书页面的配置
    "pdf" pdf 双语对照翻译页面的配置

完整的 id 集合可以在开发者设置中，Click to expand the final config 中找到

selectors 负责指定需要翻译的 CSS 选择器，建议使用子项 .add .remove 在原先的基础上进行增删

excludeSelectors 负责排除不需要翻译的 CSS 选择器，建议使用子项 .add .remove 在原先的基础上进行增删

更多讲解

Block 和 inline 的区别，如果想了解更多可以看这里

    block 元素会独占一行，多个相邻的 block 元素会各自新起一行。
    inline 元素不会独占一行，多个相邻的 inline 元素会排列在同一行里，直到一行排列不下才会新换一行。


### Planner Response

感谢你分享这个详细的文档！我现在完全理解了。

## 问题解答

你说得对，这些 prompt 对于 `doubao-seed-translation-250915` 专用翻译模型来说**确实是废话**。

但好消息是：**我们的服务器已经自动忽略了这些 prompt！** 

工作流程是这样的：
```
沉浸式翻译发送:             我们的服务器处理:           发送给模型的:
┌─────────────────┐         ┌──────────────┐           ┌──────────────┐
│ system prompt   │ ──────→ │ 完全忽略     │           │              │
│ (废话)          │         │              │           │              │
├─────────────────┤         ├──────────────┤           ├──────────────┤
│ user: {{text}}  │ ──────→ │ 只提取文本   │ ────────→ │ 纯文本       │
│ (Hello world)   │         │              │           │ (Hello world)│
└─────────────────┘         └──────────────┘           └──────────────┘
```

日志里显示完整请求只是为了**调试**，实际上我们只用了 `{{text}}` 部分。

---

## 如何让配置更干净（可选）

如果你想让请求更简洁，可以在沉浸式翻译的设置中简化 prompt：

### 方法 1：简化 Prompt 配置
在沉浸式翻译的 OpenAI 翻译服务设置中：

- **System Prompt**: 留空（完全删掉）
- **Prompt**: 只填 `{{text}}`
- **Multiple Prompt**: 只填 `{{text}}`
- **Subtitle Prompt**: 只填 `{{text}}`

这样沉浸式翻译发送的请求会变成：
```json
{"model": "...", "messages": [{"role": "user", "content": "Hello world"}]}
```

### 方法 2：简化服务器日志
如果你觉得日志太长了，我可以修改服务器，让它只打印关键信息而不是完整的原始请求。要我改吗？

---

**总结**：翻译功能已经正常工作了！那些 prompt 只是沉浸式翻译的"标准操作"，我们的服务器已经正确地忽略它们，只提取纯文本发给专用翻译模型。

### User Input

我的意思是 那些文档 你看了之后 觉得如何 我们有没有必要搞点高级玩法
如果你觉得没必要,请整理一下,尤其把readme整理一下,把教程弄详细一点
然后上传至github

### Planner Response

看完文档后，我的分析如下：

## 📊 高级功能评估

| 功能 | 是否需要支持 | 原因 |
|------|-------------|------|
| YAML 格式翻译 | ❌ 不需要 | doubao-seed-translation 是专用模型，不支持结构化输出 |
| 反思式翻译 | ❌ 不需要 | 专用模型不支持两步翻译流程 |
| 多段落 %% 分隔 | ❌ 不需要 | 模型输入限制 1k tokens，效果有限；我们已有批量翻译 |
| 自定义术语库 | ❌ 不需要 | PRO 功能，专用模型不支持 prompt 注入术语 |

**结论**：对于 `doubao-seed-translation-250915` 专用翻译模型，这些高级功能**没有必要**。专用模型的优势就是简单直接、翻译质量稳定，不需要复杂的 prompt 工程。

---

现在让我整理 README，添加详细教程，然后上传到 GitHub：

*Viewed [README.md](file:///home/louis/doubao-batch-translator/README.md) *

### Planner Response

现在让我更新 README，添加详细的沉浸式翻译配置教程：

*Edited relevant file*

### Planner Response

现在让我清理服务器代码中的调试日志，让它更简洁：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

*Edited relevant file*

### Planner Response

现在添加简洁的日志输出：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

### Planner Response

让我添加一个简洁的请求日志：

*Edited relevant file*

### Planner Response

现在让我同样为 OpenAI 端点添加简洁日志：

*Viewed [api.py](file:///home/louis/doubao-batch-translator/server/api.py) *

*Edited relevant file*

### Planner Response

现在检查 git 状态并提交更改：

*User accepted the command `cd /home/louis/doubao-batch-translator && git status -s`*

*User accepted the command `cd /home/louis/doubao-batch-translator && git add -A && git commit -m "feat: 添加沉浸式翻译插件支持

- 新增 /translate 端点，支持沉浸式翻译自定义 API 格式
- 优化 /v1/chat/completions 端点，兼容 OpenAI 格式
- 更新 README，添加详细的沉浸式翻译配置教程
- 简化日志输出，只显示关键翻译信息
- 支持灵活的请求字段名匹配 (source_lang/source_language/from)"`*

*User accepted the command `cd /home/louis/doubao-batch-translator && git push`*

*Checked command status*

### Planner Response

已成功推送到 GitHub！

## ✅ 完成总结

### 1. 高级功能评估结论
对于 `doubao-seed-translation-250915` 专用翻译模型，沉浸式翻译的高级功能（YAML 格式、反思式翻译、术语库等）**没有必要实现**，因为专用模型不支持复杂的 prompt 工程。

### 2. 代码更改

| 文件 | 更改内容 |
|------|----------|
| [server/api.py](cci:7://file:///home/louis/doubao-batch-translator/server/api.py:0:0-0:0) | 添加 `/translate` 端点支持沉浸式翻译自定义 API 格式；优化日志输出 |
| [README.md](cci:7://file:///home/louis/doubao-batch-translator/README.md:0:0-0:0) | 添加详细的沉浸式翻译配置教程，包括 OpenAI 模式和自定义 API 模式 |

### 3. 已推送到 GitHub
```
commit 2a465ed: feat: 添加沉浸式翻译插件支持
```

### 4. 沉浸式翻译配置快速指南

**OpenAI 模式**（你正在使用的）:
- URL: `http://127.0.0.1:8000/v1/chat/completions`
- Prompt: 填写 `{{text}}`

**自定义 API 模式**:
- URL: `http://127.0.0.1:8000/translate`
- 无需配置 Prompt

现在你可以在 [GitHub](https://github.com/LouisLau-art/doubao-batch-translator) 上查看更新后的 README 了！