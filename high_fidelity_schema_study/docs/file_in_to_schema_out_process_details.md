# 从文件输入到统一模式信封输出：高保真 Schema 提取全流程技术详解

在科学数据集的管理与检索中，如何**准确、可审计地识别数据文件结构、推断其物理/逻辑/语义属性，并保持证据可追溯性**是一个核心挑战。本篇文档将深度剖析本项目如何实现从**原始文件摄入 (File In)** 到**统一模式信封输出 (Schema Out)** 的全流程细节。

---

## 核心设计哲学：确定性优先 (Deterministic-First)

传统的元数据/模式提取往往采用“端到端 LLM 盲猜”的方法——直接将文件名和前几行数据发送给大语言模型（LLM）进行猜测。这种方法在科研领域存在三大致命缺陷：
1. **幻觉与不可控性**：模型可能会虚构不存在的字段、形状或类型。
2. **缺乏审计证据**：无法溯源某项字段推断到底基于文件中的哪一行、哪个属性，还是基于外部文档的哪句话。
3. **不可复现与低确定性**：即使输入完全相同，模型多次运行的输出也可能不一致。

为解决此问题，本项目采用 **Deterministic-First（确定性优先）** 的设计哲学：
* **结构提取由程序主导**：首先使用高度稳定的确定性解析器读取文件结构与元数据，获取绝对准确的物理结构。
* **收集证据并计算置信度**：在解析过程中，保留每一个物理决策的证据来源（如表头名称、文件内属性、样例行位置）。
* **受约束的 LLM 语义补全**：仅在确定性解析完成后，才引入 LLM 解释外部 README 或复杂语义，且 LLM 只能修改特定语义字段，所有修改必须有证据支撑且通过兼容性校验。
* **统一信封图谱投影**：最后将所有结构、推断、主张（Claims）与证据（Evidence）投影为图谱结构，生成标准化的“模式信封 (Schema Envelope)”。

下面是完整的处理管线：

```text
原始文件/目录输入 (File In)
       │
       ▼
 1. 格式识别与路由检测 (Format Detection) ────► 判断魔数/后缀/特定目录结构
       │
       ▼
 2. 确定性提取 (Deterministic Extraction) ────► 运行专属提取器 (CSV, JSON, Zarr 等)
       │                                       └─ 提取物理类型、基本逻辑类型与源证据
       ▼
 3. 时间与单位剖析 (Profiling & Normalization) ─► 自动识别时间轴，标准化物理单位
       │
       ▼
 4. 受约束的语义合并 (Semantic Enrichment) ───► LLM 基于 Grounding 证据填充，严格兼容性校验
       │
       ▼
 模式信封统一投影 (Schema Out) ──────────────► 生成规范化 Envelope (含 Claims 与 Evidence 追溯图谱)
```

---

## 第一阶段：文件摄入与类型检测 (File Intake & Format Detection)

当一个路径被送入系统时，入口函数为 `extractors/registry.py` 中的 [extract_path](../extractors/registry.py#L415)。在运行对应的解析器之前，必须首先进行**资源合法性校验**与**格式智能识别**：

### 1. 资源合法性与类型校验
系统会通过 `_actual_resource_kind(path)` 判断输入是单个文件 (`file`) 还是目录存储 (`directory_store`，例如 Zarr)。
如果调用者指定了特定的资源类型需求（如强制要求 `directory_store`），而实际路径不符，系统会立即抛出 `resource_kind_mismatch` 错误。

### 2. 多重格式信号收集 (`detect_format`)
为了避免单靠后缀名带来的误判，系统会收集四种层级的格式信号（Signals）：
* **魔数信号 (`_magic_signal`)**：如果输入是文件，读取前 16 个字节。
  * `\x89HDF\r\n\x1a\n` ──► 识别为 `hdf5` 容器。
  * `PAR1` ──► 识别为 `parquet` 容器。
  * `CDF\x01`, `CDF\x02`, `CDF\x05` ──► 识别为 `netcdf` 经典格式。
  * `PK\x03\x04` ──► 识别为 `zip_container`。
  * **特殊重写逻辑**：若识别为 `hdf5` 容器，但文件后缀为 `.nc` 或 `.cdf`，且通过 [hdf5_has_netcdf_markers](../extractors/netcdf_extractor.py) 检测到文件内含有 NetCDF4 标识，则信号会被升级并重写为 `netcdf`。
* **目录结构信号 (`_directory_signal`)**：如果输入是目录，检查是否存在 Zarr 元数据文件。
  * 存在 `zarr.json` ──► 识别为 Zarr v3 存储。
  * 存在 `.zgroup`, `.zarray`, `.zmetadata` ──► 识别为 Zarr v2 存储。
* **后缀名信号 (`_suffix_signal`)**：查找后缀映射字典（如 `.json` / `.jsonl` ──► `json`, `.csv` / `.tsv` ──► `csv`）。
* **文本探针信号 (`_looks_like_delimited_text`)**：对于无魔数的文本文件，尝试读取前 8192 字节，使用 Python 的 `csv.Sniffer` 探测是否存在一致的分隔符（`,`, `\t`, `;`, `|`）。若前 5 行在分列后拥有完全一致的列数且列数 $\ge 2$，则生成 `csv` 信号。
* **格式提示信号 (`format_hint`)**：由用户手动指定的提示（如 `h5` 自动归一化为 `hdf5`）。

### 3. 优先级决策与冲突处理
探测完成后，系统按以下优先级处理信号：
$$\text{魔数 (Magic)} > \text{用户提示 (Hint)} > \text{后缀 (Suffix)} > \text{文本探针 (Text Probe)}$$

* 如果最强信号（如 Magic）与用户提示（Hint）指向不同的格式（如 Magic 识别为 HDF5，Hint 指向 JSON），则判定为 `conflicted`，系统将**弃权（Abstained）**，不再调用具体解析器，而是回退输出一个通用二进制（`raw_binary`）模式。
* 识别成功后，系统在 [EXTRACTOR_CAPABILITIES](../extractors/registry.py#L71) 中匹配对应的能力声明，并调用匹配的运行器。

---

## 第二阶段：确定性结构提取 (Deterministic Structural Extraction)

根据识别出的格式，系统将启动对应的确定性解析器。本阶段只关注**绝对客观的物理结构与内秉元数据**。

### 1. CSV Extractor (`csv_conservative_profiler`)
对应文件：[csv_extractor.py](../extractors/csv_extractor.py)。
* **数据流读取**：利用 `csv.DictReader` 读取表头，并截取前 $N$ 行样例数据（默认 $N=200$）。
* **保守物理类型推断**：
  * 对采集的列样本进行去除空白处理。
  * **Int 判断**：若列非空，且除了可选正负号外全为数字，则标记为 `int`。**特别注意**：为防止像邮政编码、电话号码或以 0 开头的 ID 被误判为整型而丢失前导零，系统内设了 `_has_leading_zero` 检测。任何包含前导零（如 `"0123"`）的纯数字列均被强制推断为 `string`。
  * **Datetime 判断**：尝试用多种格式（ISO-8601, `%Y-%m-%d %H:%M:%S` 等）解析，若非空值解析成功率达 100%，则推断为 `datetime`。
  * **Float 判断**：尝试转换为 float，且文本中包含小数点 `.` 或指数符号 `e/E`，则推断为 `float`。
  * **保守回退**：若有任何一行类型冲突，则保守回退为 `string`，并写入 `uncertainty_reason="conservative fallback to string to avoid over-claiming"`。
* **内置启发式映射**：
  * **语义类型推断**：通过列名（如 `lat` -> `latitude`, `temp` -> `air_temperature`）进行初步字典映射。
  * **逻辑类型推断**：基于推断出的语义与物理类型，划分其逻辑角色（如标识符 `identifier`、坐标 `coordinate`、测量值 `measurement`、标签 `label`、属性 `attribute`）。
  * **单位识别**：匹配表头后缀（如 `_c` -> `Celsius`，`_mg_l` -> `milligram_per_liter`）。
* **证据记录生成**：为字段生成结构层证据（`evidence_type="csv_header"`）和统计层证据（`evidence_type="sample_rows"`）。

### 2. JSON Extractor (`json_bounded_structure_extractor`)
对应文件：[json_extractor.py](../extractors/json_extractor.py)。
* **内存保护**：限制读取字节上限（默认 16MB），若超出则安全弃权。
* **模式双轨制**：
  1. **声明模式 (Declared Mode)**：检查文档根部是否声明了包含 `$schema` 或 `$id` 且带有 `properties` 的标准 JSON Schema。如果是，则递归遍历解析它的嵌套定义，生成 `declared` 状态的 Claims。若同时提供了 `examples`，提取其样例并检验物理类型是否与声明冲突。
  2. **观察模式 (Observed Mode)**：如果没有 Schema 声明，系统会启动递归观察路径分析器。
* **嵌套路径遍历**：
  * 定义递归 `visit(value, path, record_index)`。
  * 将多层嵌套的 JSON 对象展开为扁平的路径。例如，嵌套结构：
    ```json
    { "store": { "book": [{ "title": "Math" }] } }
    ```
    会被解析为：`$.store`, `$.store.book`, `$.store.book[]`, `$.store.book[].title`。
  * 统计每个路径节点的类型集合、出现次数（Missing Rate）及是否为空（Nullability）。对于数组，还会记录数组长度范围与元素类型。
* **安全限制**：由于 JSON 的无模式特点，确定性阶段明确声明不通过字段名猜测其语义角色，全部设为 `unknown`。

### 3. Zarr Extractor (`zarr_v2_metadata_extractor`)
对应文件：[zarr_extractor.py](../extractors/zarr_extractor.py)。
* **多维元数据探索**：
  * 这是一个针对目录存储（Directory Store）的提取器。
  * 提取器遍历整个 Zarr 目录，优先检测是否存在合并的 `.zmetadata` 文件。如果存在，直接在内存中建立虚拟文件树映射；如果不存在，则通过 `os.walk` 遍历，寻找分散的 `.zgroup`, `.zarray`, `.zattrs` 配置文件。
* **严格的版本校验**：
  * 解析每个 `.zgroup` / `.zarray` 里的 `zarr_format` 字段。
  * 如果 `zarr_format == 3`（Zarr v3），由于当前只支持 v2，提取器会抛出 `StructuredExtractionError`，状态置为 `abstained`（弃权）。
* **维度与坐标系深度解析**：
  * 读取 `.zarray` 元数据，捕获 `shape`、`chunks` 和 `dtype`，作为物理模式字段。
  * 基于 Xarray 约定：从 `.zattrs` 读取 `_ARRAY_DIMENSIONS` 列表，如果该列表长度与当前数组维度（Rank）一致，则生成维度声明证据。
  * 基于 CF (Climate and Forecast) 约定：检查属性中的 `axis` (T/X/Y/Z)、`standard_name` (如 `air_temperature`)、`units` (如 `degrees_north`)。
  * 通过约定判定字段属于**维度坐标 (dimension_coordinate)**、**辅助坐标 (auxiliary_coordinate)** 或是普通的物理测量值。
* **Metadata-only 约束**：
  * 该解析器仅读取元数据 JSON 文件，**不读取任何 chunk 分片数据**（不涉及网络或大磁盘 I/O），因此对字段的样例值、空值率（Unique/Missing Ratio）、值域范围等直接标记为 `unknown` 或 `abstained`。

---

## 第三阶段：数据概要分析与辅助语义层 (Profiling & Normalization)

物理结构与基础证据链被提取出后，系统立即在后台运行三个辅助确定性模块，以富化数据描述：

### 1. 时间语义深度分析 (`analyze_temporal_semantics`)
对应文件：[temporal_semantics.py](../temporal_semantics.py)。
* **多维度打分机制**：
  * 系统自动扫描所有提取出的字段，对每个字段进行“时间候选度打分”。
  * 评分因素：物理类型是否为 `datetime` ($+0.4$)、字段名是否强匹配时间正则（如 `timestamp`, `event_time`, `ts_utc`）($+0.4$)、语义类型是否已映射为 `observation_time` ($+0.15$)、逻辑类型是否包含时间特征 ($+0.15 \sim +0.35$)。
  * **分部时间组装**：若数据中没有现成的 datetime 字段，但同时包含名为 `year`、`month`、`day`（以及可选的 `hour`, `minute`, `second`）的列，系统会自动将其作为一个虚拟时间字段进行组合打分。
* **时间轴选定与歧义消除**：
  * 打分 $\ge 0.7$ 的字段被视为合格候选。
  * 如果有多个候选字段的分差 $\le 0.05$（例如同时存在 `dateTime` 和 `epochTime`），则在分析元数据中发出 `ambiguous_time_axis_candidates` 警告，避免随意猜测。
  * 选定分值最高者作为数据集的 **唯一时间轴 (Time Axis)**，并将该字段的逻辑类型正式覆写为 `time_axis`。
* **采样特性推断**：
  对时间轴中抽取的 Datetime 数组进行差分计算（Deltas）：
  * **时区检测**：利用正则分析时间字符串尾部（如 `Z` 或 `+08:00`）。若同时存在 Naive 和 Aware 的时间戳，则时区标记为 `conflicted`；否则提取统一的偏移量（如 `UTC`）。
  * **频率判定 (Frequency)**：计算相邻时间戳秒数差，识别出占绝对统治地位（占比 $\ge 75\%$）的间隔。如果是 $60$ 秒映射为 `1 minute`，如果是 $3600$ 秒映射为 `1 hour`。
  * **规律性判定 (Regularity)**：如果主频占比 $\ge 95\%$，判定为 `regular`；若在 $75\% \sim 95\%$ 之间，判定为 `mostly_regular`；低于 $75\%$ 判定为 `irregular`。
  * **缺失区间估计 (Missing Intervals)**：基于时间轴首尾跨度和所测出的主频，计算理论上应包含的步长数，与实际去重行数对比，得出缺失的时间采样点个数。

### 2. 物理单位归一化 (`normalize_unit_claim`)
对应文件：[unit_normalization.py](../unit_normalization.py)。
* 提取出的物理单位（如表头后缀解析出来的单位，或元数据中声明的单位）会送入归一化引擎。
* 引擎检索 `UNIT_ALIASES` 字典。例如，将 `celsius`, `c`, `Cel` 统一映射到规范化单位 `Celsius`，并附带符合国际标准的 UCUM（统一单位编码）代码 `Cel`；将 `mg/l`, `mg_l` 映射为 `milligram_per_liter`（UCUM: `mg/L`）。
* 对无法识别的单位标记为 `unmapped_unit`，无单位的标记为 `no_unit_claim`。
* 根据输入的证据类型确定证据强度。若来自 Zarr/NetCDF/HDF5 的文件属性，记为 `explicit_metadata` 证据；若仅来自 CSV 表头名称猜测，记为较弱的 `name_pattern` 证据。

### 3. 数据剖析 (`build_dataset_profile`)
对应文件：[deterministic_profile.py](../deterministic_profile.py)。
* 对每个字段进行缺失度统计（`missing_ratio`）。
* 评估标识符质量：分析标记为 `identifier` 字段的去重比例。
  * 缺失率大于 0 ──► `incomplete_identifier`。
  * 唯一性比例 $\ge 98\%$ ──► `unique_identifier`。
  * 唯一性比例 $50\% \sim 98\%$ ──► `group_identifier`。
  * 唯一性比例 $< 50\%$ ──► `low_cardinality_identifier`。
* 识别出的优质 ID 字段，将被写入元数据的 `best_identifier_fields` 中，为后续数据集关联做准备。

---

## 第四阶段：受约束的 LLM 语义增强层 (Evidence-Constrained LLM Semantics)

在确定性解析完成后，系统会评估是否要对不确定或标为 `unknown` 的属性进行增强。此阶段通过 LLM 补全数据背后的人类知识，但有极其严格的合并限制。

### 1. 任务包构建 (Grounding Bundle)
对应文件：[semantic_layer.py](../semantic_layer.py)。
* 系统将第二、三阶段输出的确定性 Schema 转换为 JSON，同时收集该数据集的外部关联文本（如 README、说明文档、元数据 XML 描述），封装成 `GroundingSnippet` 列表，赋予优先级并限制上下文窗口长度。
* 系统将该数据包和严格的系统规则（`SYSTEM_RULES`）发送给 LLM。
* **LLM 被明确告知**：
  * 不得凭空捏造字段，所有语义或类型推断必须基于 `supporting_evidence`。
  * 无法确定时必须填 `unknown`。
  * 输出格式必须严格遵循定义的 JSON Schema。

### 2. 校验与格式归一化 (`validate_annotation_result`)
当 LLM 返回标注结果后，系统会启动拦截式校验：
* 检测 `task_id` 是否匹配。
* 检查 LLM 返回的字段路径 `field_path` 是否真正存在于物理 Schema 中（防止模型虚构字段）。
* 校验 Logical Type 是否属于八大标准类型之一。
* 校验置信度 `confidence` 是否在 $[0.0, 1.0]$ 范围。
* 若 `semantic_type` 为 `unknown`，强制要求必须提供不确定原因描述 `uncertainty_reason`。
* 对所有证据文本进行格式归一化（整理为 `[source]: [detail]` 列表）。

### 3. 保守合并机制 (`merge_annotation_result`)
校验通过的结果并不会无条件覆盖 Schema，而是通过以下安全守则进行合并：
* **无证据拒绝**：如果 LLM 对某字段做出了修改，但返回的 `supporting_evidence` 列表为空，系统会抛出 `unsupported_annotation_no_evidence` 冲突，拒绝该修改。
* **合法性与兼容性检查**：检查提议的 `logical_type` 是否在提议的 `semantic_type` 兼容集合内（通过 `compatible_logical_types_from_semantic` 字典检索。例如，若语义类型是 `latitude`，而 LLM 提议将其逻辑类型设为 `measurement`，系统会判定不兼容，并记录 `semantic_logical_incompatibility` 冲突）。
* **保护确定性证据**：
  * 若确定性引擎已提取出强类型的 `logical_type` / `semantic_type` / `unit`：
    * 如果 LLM 提议的值与确定性结果一致，安全合并。
    * 如果不一致，原则上拒绝，并记录对应的 `conflict_type`（如 `logical_type_conflict`, `unit_conflict`）。
    * **特殊精化通道**：如果原本的逻辑类型是兼容的（如 `measurement` 细化为 `coordinate`），且语义名称匹配，且 LLM 输出的置信度 $\ge 0.85$，系统允许此精化合并，并记录为 `logical_type_overrides`。
  * 合并结果会连同所有的 `conflicts` 和 `logical_type_overrides` 一并记录到最终 Schema 的 `metadata` 中，实现全程透明且安全可审计。

---

## 第五阶段：模式信封统一投影 (Schema Out)

无论文件格式如何，也无论是否进行了语义层增强，系统最终都会调用 `unified_schema.py` 中的 [build_unified_schema_envelope](../unified_schema.py#L64)，将结果投影为一个高度标准化的统一模式信封。

信封的设计遵循**“主张与证据分离，由引用关联”**的图谱规范。

### 1. 信封顶层结构 (Top-Level Structure)
模式信封在结构上呈现为以下标准键值：
```json
{
  "schema_envelope_version": "1.0.0",
  "identity": {
    "dataset_id": "数据集标识符",
    "file_id": "文件名",
    "file_format": "已识别的物理格式",
    "data_modality": "数据模态（如 tabular, multidimensional）",
    "resource_kind": "资源类别（file 或 directory_store）"
  },
  "format_detection": "第二阶段所做出的详细格式决策记录",
  "extractor_capability": "解析器的元数据与能力声明",
  "outcome": {
    "status": "提取状态（success, partial, abstained, failed）",
    "issues": [ "提取过程中产生的警告、降级、采样截断说明等 Issue" ]
  },
  "physical_structure": {
    "fields": [ "最底层物理字段列表（包含名称、物理类型、长宽等）" ],
    "groups": [ "容器分级组结构" ],
    "dimensions": { "多维数据的维度映射" },
    "format_specific": { "格式特有的解析树，如 Zarr 独有数组配置" }
  },
  "logical_roles": [ { "field_path": "路径", "logical_type": "逻辑类型" } ],
  "semantic_hints": [ { "field_path": "路径", "semantic_type": "语义类型" } ],
  "units": [ { "field_path": "路径", "unit": "原单位", "normalization": "归一化结果" } ],
  "temporal_semantics": { "时间轴、采样频率、规律性、缺失分析" },
  "claims": [ "标准的主张列表" ],
  "evidence": [ "全局去重的证据实体库" ],
  "provenance": {
    "source_file_id": "源物理文件",
    "extractor_id": "所用提取器程序ID",
    "extractor_version": "解析器版本",
    "determinism_class": "确定性评级（如 strict, strict_metadata_only）",
    "transformation": "deterministic_unified_envelope_projection"
  },
  "conflicts": [ "各类语义或格式层冲突详细列表" ],
  "abstentions": [ "如果是弃权状态，列出弃权的具体原因与错误详情" ]
}
```

### 2. 主张与证据的绑定图谱 (Claims & Evidence Graph)
信封中最关键的审计设计在于 `claims` 与 `evidence` 数组的关联：
* **全局证据池 (`evidence`)**：
  提取器或 LLM 识别到的所有具体证据实体，被添加到一个去重的池中，并分配唯一的 ID。例如：
  ```json
  "evidence": [
    {
      "evidence_id": "e0001",
      "tier": "structural",
      "evidence_type": "csv_header",
      "source": "d:/data/weather.csv",
      "detail": "header='ts_utc'",
      "confidence": 1.0
    },
    {
      "evidence_id": "e0002",
      "tier": "statistical",
      "evidence_type": "sample_rows",
      "source": "d:/data/weather.csv",
      "detail": "sampled_rows=200",
      "confidence": 0.9
    }
  ]
  ```
* **主张实体列表 (`claims`)**：
  关于模式的所有陈述（如字段类型、逻辑分类、语义标签、单位）都被归一化为一条条客观的主张。每条主张分配一个 `claim_id`，声明它的主体、所指属性、值、状态、原因码，并使用 `evidence_refs` 指向一个或多个证据的 `evidence_id`：
  ```json
  "claims": [
    {
      "claim_id": "c0001",
      "subject": "ts_utc",
      "property": "physical_type",
      "value": "datetime",
      "state": "declared",
      "reason_code": "extractor_field_claim",
      "evidence_refs": [ "e0001", "e0002" ]
    },
    {
      "claim_id": "c0002",
      "subject": "ts_utc",
      "property": "logical_type",
      "value": "time_axis",
      "state": "supported",
      "reason_code": "extractor_field_property",
      "evidence_refs": [ "e0001", "e0002" ]
    }
  ]
  ```

这种设计确保了即便面对千兆级别的多维嵌套数据，所有的最终模式声明依然可以精准回溯到其在文件元数据、局部采样行或外部文档中对应的那份物理证据。

---

## 全流程实例串联 (Example Walkthrough)

假设有一份名为 `buoy_sensor_data.csv` 的原始文件输入，下面是它从**“File In”**到**“Schema Out”**的完整流转细节：

### 1. 文件进入 (File In)
* 系统加载 `buoy_sensor_data.csv` 路径。

### 2. 格式自动探测
* 扫描该文件，魔数未匹配到 HDF5/Parquet/NetCDF。
* 检测到后缀为 `.csv`。
* 启动文本探测探针，`csv.Sniffer` 发现以逗号 `,` 分隔，前 5 行每行列数均为 4。
* 判定所选格式为 `csv`，并匹配到提取器：`csv_conservative_profiler`。

### 3. 确定性提取
* 读取表头：`ts_utc`, `buoy_id`, `water_temp_c`, `flag`。
* 截取前 200 行数据，计算出物理类型：
  * `ts_utc`：全部符合 ISO 时间格式，判定物理类型为 `datetime`。
  * `buoy_id`：以 `'0'` 开头的字符串（例如 `'0052'`），触发 `_has_leading_zero`，判定物理类型为 `string`，标记原因码。
  * `water_temp_c`：全部为带浮点数的值，判定物理类型为 `float`。
  * `flag`：包含字母及空值，判定物理类型为 `string`。
* 产生基础的物理字段模式定义。

### 4. 辅助语义计算
* **时间语义分析**：
  * 评分系统启动，`ts_utc` 字段以极高分被判定为整个数据集的 `time_axis`。
  * 差分计算显示：采样点平均间隔为 60 秒，无时区标志，规律度为 `regular`。
  * `ts_utc` 的逻辑类型被正式标记为 `time_axis`。
* **单位归一化**：
  * 发现 `water_temp_c` 表头带有后缀 `_c`，提取单位名 `celsius`。
  * 归一化字典将其规范化为 `Celsius`（UCUM 代码: `Cel`），标记证据依据为 `name_pattern`。
* **确定性剖析**：
  * 检测到 `buoy_id` 在 200 行样例中不含空值，去重比例为 0.05（分组标识符），标记标识符质量为 `group_identifier`。

### 5. 受约束的语义补全
* 构建以 deterministic schema 为基础的 grounding 任务包。
* LLM 读取该任务包并解释附加说明（例如 README 指出：*“flag 包含对浮点测量数据的质控标准，0 为合格，1 为异常”*）。
* LLM 提议：
  * 将 `flag` 的 `semantic_type` 修改为 `quality_flag`，`logical_type` 修改为 `label`，并给出 README 对应段落作为 `supporting_evidence`。
* 系统合并层拦截校验：`quality_flag` 与 `label` 兼容，修改得到安全合并；`flag` 字段被附带上 LLM 置信度及证据溯源字段。

### 6. 统一信封投影 (Schema Out)
* 汇总所有结果，创建唯一的全局证据：
  * `e0001` 指向表头 `ts_utc`，
  * `e0002` 指向表头 `water_temp_c` 衍生单位，
  * `e0003` 指向外部 README 质控描述。
* 投影得到 Claims 并附带证据 ID 引用。
* 输出最终高度规范化的统一模式信封 JSON，完成全生命周期流程。
