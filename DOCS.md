# local-file-processor — 完整技术文档

> 版本：2026-03-30
> 作者：duwei
> 仓库：https://github.com/duwei1018/local-file-processor

---

## 目录

1. [项目概述](#1-项目概述)
2. [目录结构](#2-目录结构)
3. [环境配置](#3-环境配置)
4. [快速开始](#4-快速开始)
5. [功能模块详解](#5-功能模块详解)
   - 5.1 [文件解析（parsers）](#51-文件解析parsers)
   - 5.2 [数据摄取流水线（pipeline）](#52-数据摄取流水线pipeline)
   - 5.3 [AI 智能处理（intelligence）](#53-ai-智能处理intelligence)
   - 5.4 [语义搜索（retrieval）](#54-语义搜索retrieval)
   - 5.5 [目录监听（watcher）](#55-目录监听watcher)
   - 5.6 [Markdown 导出（output）](#56-markdown-导出output)
   - 5.7 [格式互转（converter）](#57-格式互转converter)
   - 5.8 [文件分类整理（organizer）](#58-文件分类整理organizer)
6. [CLI 命令参考](#6-cli-命令参考)
7. [数据库结构](#7-数据库结构)
8. [输出目录与同步](#8-输出目录与同步)
9. [备份与版本控制](#9-备份与版本控制)
10. [LLM 后端配置](#10-llm-后端配置)
11. [已知限制与后续改善方向](#11-已知限制与后续改善方向)

---

## 1. 项目概述

`local-file-processor` 是一个**本地文件 AI 处理流水线**，专为研究人员、分析师设计。

**核心功能：**

| 功能 | 说明 |
|------|------|
| 多格式解析 | PDF、Word (.docx)、Markdown、纯文本 |
| 去重摄取 | SHA256 内容哈希，跳过重复文件 |
| 文本分块 | 约 500 token/块，50 token 重叠，保留语义完整性 |
| AI 分类 | 自动打标签、归类（9个预定义类别） |
| AI 摘要 | 生成文档摘要，存入数据库 |
| 结构化提取 | 从文档提取结构化字段（JSON） |
| 向量嵌入 | 支持 Kimi 或 Ollama 两种嵌入后端 |
| 语义搜索 | 余弦相似度搜索，可选 HNSW 索引加速 |
| 目录监听 | watchdog 实时监听新文件并自动处理 |
| Markdown 导出 | 将处理结果导出为 .md 文件 |
| 格式互转 | pdf/md/docx/txt 四种格式 12 个方向全互转 |
| 文件分类整理 | 按内容类别或文件类型自动建立分类文件夹并归档 |

**设计原则：**
- 本地优先：所有核心功能可离线运行（格式转换、规则分类）
- 可扩展：LLM 后端可替换（Kimi / Ollama / 其他 OpenAI 兼容接口）
- 无状态转换：converter 和 organizer 不依赖数据库，可单独使用
- 幂等：重复运行不产生重复数据（内容哈希去重）

---

## 2. 目录结构

```
local-file-processor/
├── main.py              # CLI 总入口（click）
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
├── .gitignore           # 排除 .env / db / uploads / __pycache__
├── backup.sh            # 一键备份 + git push 脚本
├── CHANGELOG.md         # 变更记录（每次修改必须追加）
├── README.md            # 面向用户的快速参考
├── DOCS.md              # 本文档（完整技术说明）
│
├── db/
│   └── init.sql         # DuckDB 表结构 DDL
│
├── input/               # 待处理文件放置目录（不进 git）
├── output/              # 本地临时导出目录
│
├── prompts/             # LLM 提示词模板
│   ├── classify.txt     # 分类提示词
│   ├── summarize.txt    # 摘要提示词
│   └── extract.txt      # 结构化提取提示词
│
└── src/
    ├── __init__.py
    ├── parsers/          # 文件解析器
    │   ├── base.py       # ParsedDocument 数据类
    │   ├── registry.py   # 解析器注册与调度
    │   ├── pdf_parser.py
    │   ├── docx_parser.py
    │   ├── markdown_parser.py
    │   └── text_parser.py
    │
    ├── pipeline/         # 摄取流水线
    │   ├── ingest.py     # FileIngestor：解析→清洗→去重→存储
    │   ├── chunker.py    # 文本分块（500 token，50 重叠）
    │   ├── cleaner.py    # 文本清洗（去除控制字符等）
    │   ├── hasher.py     # SHA256 内容指纹
    │   └── store.py      # DuckDBStore：所有数据库操作
    │
    ├── intelligence/     # AI 处理层
    │   ├── client.py     # LLM 客户端工厂（Kimi / Ollama）
    │   ├── classifier.py # 文档分类（LLM）
    │   ├── summarizer.py # 文档摘要（LLM）
    │   ├── extractor.py  # 结构化提取（LLM）
    │   └── embedder.py   # 向量嵌入
    │
    ├── retrieval/        # 搜索
    │   └── semantic_search.py  # 余弦相似度 / HNSW 搜索
    │
    ├── watcher/          # 目录监听
    │   └── file_watcher.py     # watchdog 事件处理
    │
    ├── output/           # 导出
    │   └── exporter.py   # FileExporter：数据库 → Markdown 文件
    │
    ├── converter/        # 格式互转（12 方向）
    │   ├── base.py       # BaseConverter / ConversionResult
    │   ├── _pdf_utils.py # PDF 共享工具（Unicode 字体）
    │   ├── pdf_to_md.py / pdf_to_docx.py / pdf_to_txt.py
    │   ├── md_to_pdf.py  / md_to_docx.py  / md_to_txt.py
    │   ├── docx_to_md.py / docx_to_pdf.py / docx_to_txt.py
    │   ├── txt_to_md.py  / txt_to_docx.py / txt_to_pdf.py
    │   └── __init__.py   # 注册表 + get_converter() API
    │
    └── organizer/        # 文件分类整理
        ├── rule_classifier.py  # 规则引擎（离线，9类）
        ├── organizer.py        # FileOrganizer（by-category / by-type）
        └── __init__.py
```

---

## 3. 环境配置

### 3.1 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：

| 包 | 用途 |
|----|------|
| `click` | CLI 框架 |
| `duckdb` | 本地向量数据库 |
| `openai` | Kimi / Ollama API 客户端 |
| `python-dotenv` | .env 加载 |
| `pypdf` | PDF 解析 |
| `python-docx` | Word 读写 |
| `fpdf2` | PDF 生成（格式转换） |
| `watchdog` | 目录监听 |
| `python-frontmatter` | Markdown frontmatter 解析 |

### 3.2 创建 .env 文件

```bash
cp .env.example .env
```

**关键配置项：**

```env
# LLM 后端（kimi 或 ollama）
LLM_BACKEND=kimi
KIMI_API_KEY=sk-xxxxx

# 输出目录
OUTPUT_DIR=/Users/duwei/Desktop/local-file-processor output
OUTPUT_DIR_NAS=/Users/duwei/Library/CloudStorage/SynologyDrive-duwei/行业研究/local-file-processor output

# 数据库路径
DB_PATH=db/local_files.duckdb
```

### 3.3 初始化数据库

```bash
python main.py db init
```

---

## 4. 快速开始

### 场景一：整理本地文件夹

```bash
# 将 input/ 目录下的文件按内容类别分类，复制到 Desktop 输出目录，并同步 NAS
python main.py organize input/

# 按文件格式分类
python main.py organize input/ --mode by-type
```

### 场景二：格式转换

```bash
python main.py convert report.pdf md       # PDF 转 Markdown
python main.py convert notes.md docx       # Markdown 转 Word
python main.py convert doc.docx pdf        # Word 转 PDF
```

### 场景三：AI 全流程处理

```bash
# 一键：摄取 → AI分类摘要 → 向量嵌入 → 导出 → 同步NAS
python main.py run input/
```

### 场景四：语义搜索

```bash
python main.py search "营业收入增长" --top-k 5
```

### 场景五：备份代码

```bash
./backup.sh "修复了某某问题"
```

---

## 5. 功能模块详解

### 5.1 文件解析（parsers）

**位置：** `src/parsers/`

**核心类：** `ParsedDocument`

```python
@dataclass
class ParsedDocument:
    title: str
    text: str         # 全文纯文本
    file_path: str
    file_type: str    # pdf / docx / md / txt
    author: str | None
    page_count: int
    headings: list[str]
    frontmatter: dict | None  # 仅 Markdown
```

**支持格式：**

| 格式 | 解析器 | 依赖 |
|------|--------|------|
| .pdf | `PDFParser` | pypdf |
| .docx | `DocxParser` | python-docx |
| .md | `MarkdownParser` | python-frontmatter |
| .txt | `TextParser` | 内置 |

**调用方式：**

```python
from src.parsers.registry import get_parser
parser = get_parser("report.pdf")
doc = parser.parse("report.pdf")
print(doc.title, doc.text[:200])
```

---

### 5.2 数据摄取流水线（pipeline）

**位置：** `src/pipeline/`

**流程：** 文件 → 解析 → 清洗 → SHA256指纹 → 去重检查 → 插入documents表 → 分块 → 插入file_chunks表 → 记录events

**关键参数：**
- 分块大小：500 token（约 350 中文字）
- 重叠：50 token（保持跨块上下文）
- 去重：基于标准化文本的 SHA256，跳过相同内容不同文件名的文件

**使用：**

```python
from src.pipeline.ingest import FileIngestor
ingestor = FileIngestor("db/local_files.duckdb")
doc_id, is_dup = ingestor.ingest_file("report.pdf")
ingestor.close()
```

---

### 5.3 AI 智能处理（intelligence）

**位置：** `src/intelligence/`

**LLM 客户端：** `client.py` 中的 `make_client_from_env()` 根据 `LLM_BACKEND` 环境变量返回统一接口（OpenAI 兼容）。

**三种 AI 处理：**

| 功能 | 模块 | 使用模型 | 输出 |
|------|------|----------|------|
| 分类 | `classifier.py` | `LLM_MODEL_FAST`（8k） | category + tags + confidence |
| 摘要 | `summarizer.py` | `LLM_MODEL_LARGE`（32k） | 自由文本摘要 |
| 结构化提取 | `extractor.py` | `LLM_MODEL_LARGE`（32k） | JSON 字典 |

**向量嵌入：** `embedder.py`，支持批量嵌入，默认 1536 维（Kimi）或自定义维度（Ollama）。

**批量处理：**

```bash
python main.py process --limit 20 --skip-embed
```

---

### 5.4 语义搜索（retrieval）

**位置：** `src/retrieval/semantic_search.py`

两种搜索模式：
1. **暴力余弦搜索**（默认）：无需预先建索引，适合 < 10万条
2. **HNSW 索引搜索**（`--hnsw`）：需先运行 `db build-index`，大规模时速度更快

```bash
python main.py search "合同违约条款" --top-k 10 --file-type pdf
python main.py search "revenue growth" --hnsw
```

---

### 5.5 目录监听（watcher）

**位置：** `src/watcher/file_watcher.py`

使用 `watchdog` 库监听文件系统事件。新文件创建时自动触发摄取，可选接续 AI 处理。

```bash
# 监听 input/ 目录，新文件到达自动摄取+AI处理
python main.py watch input/ --process
```

---

### 5.6 Markdown 导出（output）

**位置：** `src/output/exporter.py`

从数据库读取已处理文档，生成结构化 Markdown 文件（含摘要、标签、分类信息）。

默认输出到 `OUTPUT_DIR`（Desktop），执行后自动同步到 NAS。

```bash
python main.py export --limit 100
```

---

### 5.7 格式互转（converter）

**位置：** `src/converter/`

**12 个转换方向（全矩阵）：**

| 源 ↓ \ 目标 → | .md | .docx | .pdf | .txt |
|--------------|-----|-------|------|------|
| **.pdf** | ✓ | ✓ | — | ✓ |
| **.md** | — | ✓ | ✓ | ✓ |
| **.docx** | ✓ | — | ✓ | ✓ |
| **.txt** | ✓ | ✓ | ✓ | — |

**PDF 生成中文支持：**
`_pdf_utils.py` 自动搜索系统 Unicode 字体（优先 `/Library/Fonts/Arial Unicode.ttf`），确保中文字符正常渲染。

**API 调用：**

```python
from src.converter import get_converter
converter = get_converter(".pdf", ".md")
result = converter.convert("report.pdf", "report.md")
print(result.success, result.message)
```

**CLI 调用：**

```bash
python main.py convert <输入文件> <目标格式> [-o 输出路径]
python main.py convert report.pdf md
python main.py convert notes.md pdf -o /tmp/notes.pdf
```

**各格式转换说明：**

- **PDF → 其他**：通过 pypdf 提取文本，多页时按页分节
- **MD → 其他**：完整解析标题/加粗/斜体/列表/表格/代码块
- **DOCX → 其他**：按序遍历 document.body，保留段落和表格顺序
- **TXT → 其他**：启发式检测标题（短行、无句末标点），其余作正文

---

### 5.8 文件分类整理（organizer）

**位置：** `src/organizer/`

**两种分类模式：**

#### by-category（内容分类，默认）

`RuleClassifier` 基于文件名和内容关键词打分，选最高分类别：

| 类别 | 文件名关键词（×3分） | 内容关键词（×1分） |
|------|-------------------|-----------------|
| 财务报告 | 财报/年报/annual report | 营业收入/净利润/EBITDA |
| 合同协议 | 合同/协议/contract/nda | 甲方/乙方/违约/whereas |
| 学术论文 | 论文/paper/thesis | 摘要/abstract/参考文献/doi |
| 新闻报道 | 新闻/press release | 据报道/记者/announced |
| 会议记录 | 会议/meeting/纪要 | 出席/议题/action items |
| 说明书 | 说明书/manual/readme | 安装步骤/step 1/prerequisites |
| 技术文档 | 技术/api/spec | function/schema/接口文档 |
| 简历 | 简历/resume/cv | 工作经历/education/skills |
| 其他 | （兜底） | — |

可选 `--llm` 切换到 LLM 分类（精度更高但需 API 密钥）。

#### by-type（格式分类）

按扩展名分到 `PDF文档 / Word文档 / Markdown文档 / 纯文本` 四个文件夹。

**输出结构（by-category 示例）：**

```
Desktop/local-file-processor output/
├── 财务报告/
│   ├── 年度财务报告2024.pdf
│   └── 季报Q3.docx
├── 合同协议/
│   └── 采购合同.txt
├── 学术论文/
│   └── 深度学习综述.pdf
├── 会议记录/
│   └── 董事会纪要.docx
└── 其他/
    └── 杂记.txt
```

加 `--subdir-by-type` 后在类别目录下再按格式建子目录：

```
财务报告/
├── PDF文档/
│   └── 年度财务报告.pdf
└── Word文档/
    └── 季报.docx
```

---

## 6. CLI 命令参考

### 数据库管理

```bash
python main.py db init           # 创建表结构
python main.py db build-index    # 构建 HNSW 向量索引
python main.py db stats          # 查看各表行数
```

### 文件摄取

```bash
python main.py ingest input/              # 摄取目录（默认递归）
python main.py ingest input/file.pdf      # 摄取单文件
python main.py ingest input/ --ext .pdf,.md
python main.py ingest input/ --force      # 强制重新摄取（忽略去重）
```

### AI 处理

```bash
python main.py process                    # 处理未处理文档（默认20条）
python main.py process --limit 50
python main.py process --skip-embed       # 跳过向量嵌入
python main.py process --skip-classify
python main.py process --skip-summarize
python main.py process --skip-extract
```

### 语义搜索

```bash
python main.py search "关键词"
python main.py search "query" --top-k 10
python main.py search "query" --file-type pdf
python main.py search "query" --hnsw
```

### 文件分类整理

```bash
python main.py organize input/                      # 按内容分类，复制到 Desktop
python main.py organize input/ --mode by-type       # 按格式分类
python main.py organize input/ --action move        # 移动（不复制）
python main.py organize input/ --subdir-by-type     # 类别+格式双层目录
python main.py organize input/ --llm                # LLM 分类
python main.py organize input/ -o /path/to/out      # 自定义输出目录
python main.py organize input/ --ext .pdf,.docx     # 只处理指定格式
```

### 格式转换

```bash
python main.py convert <输入文件> <目标格式> [-o 输出路径]
# 支持：pdf md docx txt 四种格式间的任意转换
```

### 目录监听

```bash
python main.py watch input/
python main.py watch input/ --process     # 摄取后自动 AI 处理
```

### Markdown 导出

```bash
python main.py export                     # 导出到 Desktop 输出目录
python main.py export --output-dir /path --limit 100
```

### 全流程

```bash
python main.py run input/
python main.py run input/ --output-dir results/ --limit 50
```

---

## 7. 数据库结构

使用 DuckDB（`db/local_files.duckdb`），4张表：

### documents

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT | 主键 |
| title | TEXT | 文档标题 |
| file_path | TEXT | 原始文件路径 |
| file_type | TEXT | pdf/docx/md/txt |
| content | TEXT | 全文内容 |
| metadata | JSON | 扩展信息（content_hash/page_count 等） |
| summary | TEXT | AI 生成摘要 |
| tags | JSON | AI 分类标签列表 |
| source | TEXT | 来源路径 |
| author | TEXT | 作者 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 最后更新时间 |

### file_chunks

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT | 主键 |
| document_id | BIGINT | 关联文档 |
| chunk_index | INTEGER | 块序号（0-based） |
| text | TEXT | 块文本 |
| token_count | INTEGER | 估算 token 数 |

### embeddings

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT | 主键 |
| chunk_id | BIGINT | 关联块 |
| document_id | BIGINT | 关联文档 |
| model | TEXT | 嵌入模型名 |
| vector | FLOAT[1536] | 嵌入向量 |

### events（审计日志）

| 列 | 类型 | 说明 |
|----|------|------|
| id | BIGINT | 主键 |
| document_id | BIGINT | 关联文档 |
| type | TEXT | 事件类型（ingest/classify/summarize/embed/extract） |
| payload | JSON | 事件详情 |
| occurred_at | TIMESTAMP | 事件时间 |

---

## 8. 输出目录与同步

### 目录规划

| 目录 | 路径 | 用途 |
|------|------|------|
| 主输出（Desktop） | `~/Desktop/local-file-processor output/` | 日常查看，iCloud 同步 |
| NAS 输出 | `~/Library/CloudStorage/SynologyDrive-duwei/行业研究/local-file-processor output/` | NAS 存档，通过 Synology Drive 同步 |

### 同步机制

`organize` 和 `export` 命令执行完成后，自动调用 `rsync -a --delete` 将主输出同步到 NAS。

```
Desktop output  ──rsync──▶  NAS output
（写入侧）                   （只读备份）
```

- `rsync` 失败时仅打印警告，不中断主流程
- 若 NAS 未挂载（Synology Drive 未运行），同步跳过

### 手动同步

```bash
rsync -av --delete \
  ~/Desktop/local-file-processor\ output/ \
  ~/Library/CloudStorage/SynologyDrive-duwei/行业研究/local-file-processor\ output/
```

---

## 9. 备份与版本控制

### 使用 backup.sh

每次修改程序后运行：

```bash
./backup.sh "本次修改说明"
```

脚本执行步骤：
1. 在 `CHANGELOG.md` 头部追加本次变更记录
2. `git add` 所有源代码文件（排除 .env / db / uploads）
3. `git commit`
4. `git push origin main`

### 手动备份

```bash
git add main.py src/ requirements.txt README.md CHANGELOG.md DOCS.md .env.example
git commit -m "backup: 修改说明 [YYYY-MM-DD]"
git push origin main
```

### .gitignore 排除规则

```
.env              # API 密钥
db/               # 数据库文件
uploads/          # 原始 PDF 材料
__pycache__/
*.pyc
output/           # 本地临时输出
```

### GitHub 仓库

- 地址：https://github.com/duwei1018/local-file-processor
- 主分支：`main`
- 认证：Personal Access Token（存储在 git remote URL 中）

---

## 10. LLM 后端配置

### Kimi（Moonshot，云端，默认）

```env
LLM_BACKEND=kimi
KIMI_API_KEY=sk-...
LLM_MODEL_FAST=moonshot-v1-8k     # 分类用
LLM_MODEL_LARGE=moonshot-v1-32k   # 摘要/提取用
EMBEDDING_MODEL=moonshot-v1-embedding
```

申请地址：https://platform.moonshot.cn/

### Ollama（本地，离线）

```bash
# 安装并启动 Ollama
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

---

## 11. 已知限制与后续改善方向

### 当前限制

| 限制 | 说明 |
|------|------|
| PDF 格式保真 | PDF 转其他格式只提取文字，图片、复杂排版、数学公式丢失 |
| 中文 PDF 生成 | 依赖系统安装 Arial Unicode.ttf，其他系统需调整字体路径 |
| 表格提取精度 | 复杂合并单元格表格提取可能不完整 |
| 嵌入向量维度 | hardcoded 1536 维（Kimi），切换 Ollama 模型需调整 init.sql |
| 并发处理 | 当前单线程处理，大批量文件较慢 |
| LLM 分类精度 | 规则引擎对混合语言、非标准文档分类准确率有限 |

### 后续改善方向

#### 近期（优先级高）
- [ ] **批量格式转换**：`convert` 命令支持批量处理整个目录
- [ ] **转换质量改进**：PDF 转换时保留图片（pypdf → pdfplumber + 图片提取）
- [ ] **分类规则扩展**：增加更多行业类别（法律文书/医疗报告/政府公文）
- [ ] **进度条**：大批量处理时显示 `tqdm` 进度条

#### 中期
- [ ] **Web UI**：基于 Streamlit 的本地 Web 界面，可视化查看和搜索
- [ ] **OCR 支持**：扫描版 PDF 通过 tesseract/PaddleOCR 提取文字
- [ ] **多维度搜索**：同时支持全文关键词搜索 + 语义搜索混合排序
- [ ] **自动摘要归档**：organize 后自动生成分类目录的 index.md

#### 长期
- [ ] **知识图谱**：从文档中提取实体关系，建立文档间关联
- [ ] **问答系统**：基于已摄取文档的 RAG 问答（LangChain / LlamaIndex）
- [ ] **多用户支持**：基于用户的文档隔离和权限管理
- [ ] **云端部署**：Docker 化 + 支持远程存储（S3 / OSS）

---

*文档生成时间：2026-03-30*
*下次重大版本更新时同步更新本文档*
