# local-file-processor

本地文件 AI 处理流水线。将本地文件（PDF、Word、Markdown、文本）自动解析、分块、分类、摘要、向量嵌入，存入 DuckDB，并支持语义搜索。

## 功能概览

| 功能 | 说明 |
|------|------|
| 多格式解析 | PDF、.docx、.md、.txt |
| 去重摄取 | SHA256 哈希，跳过重复文件 |
| 文本分块 | 约 500 token/块，50 token 重叠 |
| AI 分类 | 自动打标签、归类 |
| AI 摘要 | 生成文档摘要 |
| 结构化提取 | 从文档中提取结构化字段 |
| 向量嵌入 | 支持 Kimi 或 Ollama 两种后端 |
| 语义搜索 | 余弦相似度搜索，可选 HNSW 索引加速 |
| 目录监听 | watchdog 实时监听新文件并自动处理 |
| Markdown 导出 | 将处理结果导出为 .md 文件 |
| 格式互转 | pdf/md/docx/txt 四种格式 12 个方向全互转 |
| 文件分类整理 | 按内容类别或文件类型自动建立分类文件夹并归档 |

## 目录结构

```
local-file-processor/
├── main.py              # CLI 入口
├── requirements.txt
├── .env.example
├── db/
│   └── init.sql         # DuckDB 表结构
├── input/               # 待处理文件放这里
├── output/              # 导出结果
├── prompts/             # LLM 提示词模板
│   ├── classify.txt
│   ├── summarize.txt
│   └── extract.txt
└── src/
    ├── parsers/         # 文件解析器（pdf/docx/md/txt）
    ├── pipeline/        # 摄取、分块、存储
    ├── intelligence/    # LLM 客户端、分类、摘要、提取、嵌入
    ├── retrieval/       # 语义搜索
    ├── watcher/         # 目录监听
    ├── output/          # Markdown 导出
    ├── converter/       # 格式互转（pdf/md/docx/txt 12方向）
    └── organizer/       # 文件分类整理（规则引擎 + LLM 两种模式）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 KIMI_API_KEY 或配置 Ollama
```

### 3. 初始化数据库

```bash
python main.py db init
```

### 4. 全流程处理

```bash
# 一键：摄取 → AI处理 → 导出
python main.py run input/
```

## 命令参考

### 数据库

```bash
python main.py db init          # 初始化表结构
python main.py db build-index   # 构建 HNSW 向量索引
python main.py db stats         # 查看各表行数
```

### 文件摄取

```bash
python main.py ingest input/              # 摄取目录（默认递归）
python main.py ingest input/file.pdf      # 摄取单文件
python main.py ingest input/ --ext .pdf,.md   # 过滤扩展名
python main.py ingest input/ --force      # 强制重新摄取重复文件
```

### AI 处理

```bash
python main.py process                    # 处理未处理的文档（默认最多20条）
python main.py process --limit 50         # 指定批次大小
python main.py process --skip-embed       # 跳过向量嵌入
python main.py process --skip-classify    # 跳过分类
python main.py process --skip-summarize   # 跳过摘要
python main.py process --skip-extract     # 跳过结构化提取
```

### 语义搜索

```bash
python main.py search "关键词或问题"
python main.py search "query" --top-k 10
python main.py search "query" --file-type pdf
python main.py search "query" --hnsw       # 使用 HNSW 索引（需先 build-index）
```

### 目录监听

```bash
python main.py watch input/               # 监听目录，自动摄取新文件
python main.py watch input/ --process     # 摄取后自动执行 AI 处理
```

### 导出

```bash
python main.py export                     # 导出到 output/（默认最多50条）
python main.py export --output-dir /path/to/dir --limit 100
```

### 文件分类整理

自动将文件按内容或格式归档到对应文件夹，支持两种分类模式：

```bash
# 默认：按内容类别分类（规则引擎，无需 LLM，离线可用）
python main.py organize input/

# 按文件格式分类（.pdf / .docx / .md / .txt）
python main.py organize input/ --mode by-type

# 按内容分类，同时在类别目录下创建格式子目录
python main.py organize input/ --subdir-by-type

# 移动文件（默认为复制）
python main.py organize input/ --action move

# 使用 LLM 提升分类精度
python main.py organize input/ --llm

# 指定输出目录
python main.py organize input/ -o sorted/

# 只处理指定格式
python main.py organize input/ --ext .pdf,.docx
```

**内容类别（by-category 模式）：**

| 类别 | 典型关键词示例 |
|------|--------------|
| 财务报告 | 营业收入、净利润、资产负债表、annual report |
| 合同协议 | 甲方、乙方、违约、agreement、contract |
| 学术论文 | 摘要、参考文献、abstract、keywords、doi |
| 新闻报道 | 据报道、记者、announced、press release |
| 会议记录 | 出席、议题、行动项、attendees、minutes |
| 说明书 | 安装步骤、注意事项、getting started、step 1 |
| 技术文档 | function、api、schema、接口文档、架构 |
| 简历 | 工作经历、教育背景、work experience |
| 其他 | 无显著关键词匹配时的兜底分类 |

**格式类别（by-type 模式）：** PDF文档 / Word文档 / Markdown文档 / 纯文本

### 格式转换

```bash
# 基本用法：python main.py convert <输入文件> <目标格式>
python main.py convert report.pdf md           # PDF → Markdown
python main.py convert report.pdf docx         # PDF → Word
python main.py convert report.pdf txt          # PDF → 纯文本
python main.py convert notes.md docx           # Markdown → Word
python main.py convert notes.md pdf            # Markdown → PDF
python main.py convert notes.md txt            # Markdown → 纯文本
python main.py convert doc.docx md             # Word → Markdown
python main.py convert doc.docx pdf            # Word → PDF
python main.py convert doc.docx txt            # Word → 纯文本
python main.py convert file.txt md             # 纯文本 → Markdown
python main.py convert file.txt docx           # 纯文本 → Word
python main.py convert file.txt pdf            # 纯文本 → PDF

# 指定输出路径
python main.py convert report.pdf md -o output/report.md
```

支持的转换（12个方向）：

| 源格式 | 目标格式 |
|--------|---------|
| `.pdf` | `.md` / `.docx` / `.txt` |
| `.md` | `.pdf` / `.docx` / `.txt` |
| `.docx` | `.md` / `.pdf` / `.txt` |
| `.txt` | `.md` / `.docx` / `.pdf` |

### 全流程

```bash
python main.py run input/
python main.py run input/ --output-dir results/ --limit 50
```

## LLM 后端配置

### Kimi（默认，云端）

```env
LLM_BACKEND=kimi
KIMI_API_KEY=sk-...
LLM_MODEL_FAST=moonshot-v1-8k
LLM_MODEL_LARGE=moonshot-v1-32k
EMBEDDING_MODEL=moonshot-v1-embedding
```

### Ollama（本地）

```bash
ollama serve
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

```env
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
LLM_MODEL_FAST=qwen2.5:7b
LLM_MODEL_LARGE=qwen2.5:14b
EMBEDDING_MODEL=nomic-embed-text
```

## 数据库说明

使用 DuckDB 本地存储，4 张表：

| 表 | 说明 |
|----|------|
| `documents` | 每个文件一行，含内容、摘要、标签 |
| `file_chunks` | 分块后的文本，约 500 token/块 |
| `embeddings` | 每个 chunk 的向量（1536 维） |
| `events` | 流水线审计日志 |

默认路径：`db/local_files.duckdb`，可通过 `DB_PATH` 环境变量或 `--db-path` 参数覆盖。
