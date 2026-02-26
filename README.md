# WordStoryGen · 小红书英语单词故事文案 + 封面生成器

自动生成「爆款风格」英语单词故事文案，并用本地 Ollama 模型 + 自定义背景图生成高清封面。

---

## 架构说明（简短）

- **main.py**：命令行入口，解析 `cet4/cet6/kaoyan` 及 `--count`、`--format`、`--only-story`、`--only-cover`、`--title`；加载 `.env`；串联「选词 → 生成文案 → 保存/导出 → 生成封面」。
- **generator/word_loader.py**：从 `data/*.txt` 读词库，维护 `used_words.json`（防重复、损坏先备份再重建）。
- **generator/ollama_client.py**：Ollama HTTP API 封装，支持超时、重试、temperature、日志。
- **generator/story_generator.py**：读取 `prompts/story_prompt.txt`，将 `{word}` 替换后调用 Ollama 生成完整故事文案。
- **generator/cover_maker.py**：用 PIL 在 `bg1.jpg`（或缺省渐变）上绘制标题，自适应字号与换行、黑色字体、居中，导出 1080×1440 到 `output/covers/`。
- **generator/exporters.py**：导出器，将文案数据（JSON 结构）导出为 TXT 等展示格式；后续可扩展 HTML/Markdown/Excel。
- 文案：**JSON = 主存储**（数据层），**TXT = 导出格式**（展示层）；`--format json|txt|both` 控制输出。
- 文案结果存 `output/posts/<id>.json` 和/或 `<id>.txt`，封面存 `output/covers/<id>.png`，日志写 `logs/`。

---

## 一、项目介绍

- **文案**：吸睛标题 + 情感小故事（优先爱情题材）+ 反转引出英文单词 + 单词释义与记忆技巧。
- **词库**：从 `data/CET4.txt`、`data/CET6.txt`、`data/考研.txt` 按需选词，已用单词记录在 `used_words.json`，不重复使用。
- **模型**：通过 Ollama HTTP API 调用本地模型（默认 `qwen2.5`），可配置温度、超时、重试。
- **封面**：在项目目录下的 `bg1.jpg` 上叠加标题（黑色字体），自动换行、居中、字体自适应，导出 1080×1440 竖版图到 `output/covers/`。

---

## 二、功能说明

| 功能 | 说明 |
|------|------|
| 文案生成 | 固定结构：标题 → 故事 → 反转+单词 → 释义+记忆；Prompt 见 `prompts/story_prompt.txt` |
| 输出格式 | `--format json` 仅 JSON，`--format txt` 仅 TXT，`--format both` 同时输出（默认）；JSON 为主存储，TXT 为展示导出 |
| 词库选择 | 命令行参数 `cet4` / `cet6` / `kaoyan` 对应三个词库文件 |
| 已用记录 | 使用过的单词写入 `used_words.json`，同词库内不重复 |
| 封面生成 | 背景 `bg1.jpg`，标题黑色字体、自动排版、多行、居中，输出到 `output/covers/` |
| 批量生成 | `--count N` 一次生成 N 篇 |
| 仅文案 | `--only-story` 只生成并保存文案，不生成封面 |
| 仅封面 | `--only-cover` 只生成封面；可加 `--title "标题"` 指定标题且不消耗单词 |

---

## 三、安装步骤

### 1. 创建虚拟环境（推荐）

```bash
cd WordStoryGen
python -m venv venv
```

- **Windows**: `venv\Scripts\activate`
- **macOS/Linux**: `source venv/bin/activate`

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（可选）

复制示例并按需修改：

```bash
copy .env.example .env
```

编辑 `.env`：

- `OLLAMA_BASE_URL`: Ollama 服务地址，默认 `http://localhost:11434`
- `OLLAMA_MODEL`: 模型名，默认 `qwen2.5`
- `OLLAMA_TEMPERATURE`: 采样温度，默认 `0.8`
- `OLLAMA_TIMEOUT`: 请求超时秒数，默认 `120`

### 4. 配置 Ollama

- 安装 [Ollama](https://ollama.com/) 并保持服务运行。
- 拉取模型，例如：  
  `ollama pull qwen2.5`  
  若使用其他模型，在 `.env` 中设置 `OLLAMA_MODEL=模型名`。

### 5. 准备背景图与词库

- 将封面背景图放在项目根目录，命名为 **`bg1.jpg`**（建议 1080×1440 或等比例）。若不放置，程序会使用默认渐变背景。
- 词库文件：`data/CET4.txt`、`data/CET6.txt`、`data/考研.txt`，每行一个单词即可。项目已带示例词库。

---

## 四、运行示例

```bash
# 使用 CET4 词库生成 1 篇文案 + 封面（默认同时输出 JSON + TXT）
python main.py cet4

# 仅输出 JSON（适合后续做自动发布、评分、Excel 等）
python main.py cet4 --format json

# 仅输出 TXT（适合直接复制到小红书）
python main.py cet4 --format txt

# 使用考研词库生成 3 篇
python main.py kaoyan --count 3

# 只生成文案，不生成封面
python main.py cet6 --only-story

# 只生成封面，并指定标题（不消耗单词）
python main.py cet4 --only-cover --title "她结婚那天，新郎不是我"
```

生成结果：

- 文案：`output/posts/` 下 JSON（含 title、word、bank、content、created_at）及/或 TXT（由 `--format` 决定）。
- 封面：`output/covers/` 下 PNG（1080×1440）。
- 日志：`logs/` 下按日期命名的 log 文件。

---

## 五、常见错误解决

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `Ollama 调用失败，已重试 N 次` | Ollama 未启动或地址/端口错误 | 确认 Ollama 已运行，检查 `.env` 中 `OLLAMA_BASE_URL` |
| `模型返回内容为空` / 响应异常 | 模型未拉取或名称错误 | `ollama list` 查看已安装模型，`.env` 中 `OLLAMA_MODEL` 与之一致 |
| `词库 xxx 中已无未使用单词` | 该词库全部单词已用过 | 往对应 txt 中追加新词，或清空 `used_words.json` 中对应列表 |
| 封面中文乱码或方框 | 未找到合适中文字体 | Windows 一般会自动用系统字体；或放置字体到 `fonts/` 并命名为 `SourceHanSansSC-Regular.otf` 等（见 `cover_maker.py` 中 `_find_font_path`） |
| `used_words.json 损坏，已重置` | 文件被手改或编码错误 | 程序会自动重置为各词库空列表；若需保留记录，请备份后修复 JSON 格式 |

---

## 六、如何更换模型

1. 在 Ollama 中拉取新模型：`ollama pull <模型名>`  
2. 在项目根目录 `.env` 中设置：`OLLAMA_MODEL=<模型名>`  
3. 无需改代码，重启运行即可。

---

## 七、如何自定义 Prompt

- 编辑 **`prompts/story_prompt.txt`**。
- 模板中可用占位符 **`{word}`**，程序会替换为当前选中的单词。
- 修改后直接再次运行即可生效。

---

## 八、如何更换封面背景

- 将新背景图放到项目根目录，命名为 **`bg1.jpg`**（覆盖原文件即可）。
- 建议尺寸 1080×1440（竖版），或等比例；程序会缩放到该尺寸。

---

## 九、如何增加词库

1. 在 `data/` 下新建或修改 txt 文件，每行一个英文单词。
2. 若需新词库类型（如 `toefl`）：
   - 在 `generator/word_loader.py` 的 `WordBankType` 和 `BANK_FILES` 中增加 `toefl` 与对应文件名；
   - 在 `main.py` 的 `parser.add_argument("bank", choices=[...])` 中加入 `toefl`。

---

## 十、项目结构（约定）

```
project/
├── main.py
├── generator/
│   ├── __init__.py
│   ├── story_generator.py
│   ├── word_loader.py
│   ├── cover_maker.py
│   └── ollama_client.py
├── data/
│   ├── CET4.txt
│   ├── CET6.txt
│   └── 考研.txt
├── prompts/
│   └── story_prompt.txt
├── output/
│   ├── posts/
│   └── covers/
├── logs/
├── used_words.json
├── bg1.jpg
├── requirements.txt
├── .env.example
└── README.md
```

---

## 十一、环境与依赖说明

- **Python**：建议 3.10+。
- **虚拟环境**：推荐使用 `venv`，避免污染系统环境。
- **依赖**：见 `requirements.txt`（含 `requests`、`Pillow`、`python-dotenv`）。

复制即运行：按上述安装步骤配置好 Ollama、词库和背景图后，执行 `python main.py cet4` 即可生成一篇文案与对应封面。
