# CHANGELOG — local-file-processor

所有实质性变更均记录于此文件。格式：最新版本在最前。

---

## [2026-03-30] 输出目录配置、NAS同步、备份脚本与完整文档

**变更类型**：新增 / 修改

**变更内容**：
- 新增 `_PRIMARY_OUT` / `_NAS_OUT` 两个输出目录常量，从 `.env` 读取
  - Desktop: `~/Desktop/local-file-processor output`
  - NAS: `~/Library/CloudStorage/SynologyDrive-duwei/行业研究/local-file-processor output`
- `organize` 和 `export` 命令执行后自动调用 `rsync` 同步到 NAS
- `_sync_to_nas()` 辅助函数：rsync 失败时仅警告，不中断主流程
- `.env.example` 新增 `OUTPUT_DIR` / `OUTPUT_DIR_NAS` / `ORGANIZE_OUTPUT_DIR` 三个变量说明
- 新增 `backup.sh`：一键备份项目代码 + 追加 CHANGELOG + git commit + push
- 新增 `DOCS.md`：完整项目技术文档，供存档与后续改善参考

**影响范围**：`main.py`, `.env.example`, `CHANGELOG.md`（新建）, `backup.sh`（新建）, `DOCS.md`（新建）

---

## [2026-03-29] 文件分类整理模块（organizer）

**变更类型**：新增

**变更内容**：
- 新增 `src/organizer/` 模块
  - `rule_classifier.py`：基于规则的文件分类器，9类（财务报告/合同协议/学术论文/新闻报道/会议记录/说明书/技术文档/简历/其他），离线可用
  - `organizer.py`：`FileOrganizer` 类，支持 by-category / by-type 两种模式，copy/move 两种操作，可选 LLM 分类
  - `__init__.py`：模块导出
- `main.py` 新增 `organize` 命令，含 `--mode` / `--action` / `--subdir-by-type` / `--llm` 等选项
- `README.md` 新增分类整理章节

**影响范围**：`src/organizer/`（新建）, `main.py`, `README.md`

---

## [2026-03-29] 格式互转模块（converter）全量实现

**变更类型**：新增

**变更内容**：
- 新增 12 个方向的格式转换器（pdf/md/docx/txt 四格式全互转）
  - `pdf_to_md.py` / `pdf_to_docx.py` / `pdf_to_txt.py`
  - `md_to_pdf.py` / `md_to_txt.py`（md_to_docx.py 已存在）
  - `docx_to_pdf.py` / `docx_to_txt.py`（docx_to_md.py 已存在）
  - `txt_to_md.py` / `txt_to_docx.py` / `txt_to_pdf.py`
- 新增 `_pdf_utils.py`：共享 PDF 工具，加载 `Arial Unicode.ttf` 支持中文字符
- 完善 `__init__.py`：转换器注册表 + `get_converter()` / `supported_pairs()` API
- `main.py` 新增 `convert` 命令
- `requirements.txt` 新增 `fpdf2>=2.7.0`
- `README.md` 新增格式转换章节

**影响范围**：`src/converter/`（全量更新）, `main.py`, `requirements.txt`, `README.md`

---

## [2026-03-28] 初始版本：本地文件AI处理流水线

**变更类型**：新增

**变更内容**：
- 项目初始化：`local-file-processor` 独立流水线
- 多格式解析：`src/parsers/`（pdf/docx/md/txt）
- 文件摄取与去重：`src/pipeline/`（ingest/chunker/cleaner/hasher/store）
- AI 处理：`src/intelligence/`（分类/摘要/结构化提取/向量嵌入）
- 语义搜索：`src/retrieval/semantic_search.py`
- 目录监听：`src/watcher/file_watcher.py`
- Markdown 导出：`src/output/exporter.py`
- DuckDB 数据库：4张表（documents/file_chunks/embeddings/events）
- CLI 入口：`main.py`（ingest/process/search/watch/export/run/db 命令）
- 支持 Kimi（云端）/ Ollama（本地）双 LLM 后端

**影响范围**：全部文件（初始提交）

---
