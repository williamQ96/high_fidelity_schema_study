# 从文件输入到统一 Schema Envelope 输出

本文说明本项目当前的 File In -> Schema Out 流程。目标不是让模型猜 schema，而是从文件结构、显式元数据、确定性验证器和可记录证据中，产出尽可能强、同时不过度声称的 schema。

## 设计原则

- **确定性优先**：先由格式解析器建立物理结构，再做受限的逻辑/语义解释。
- **证据先行**：每个字段和关键 claim 都应能追溯到表头、样本行、文件属性、格式元数据或验证器结果。
- **不凭空补全**：没有 spec-backed extractor、证据冲突或语义不足时，输出 `unknown`、`conflicted`、`partial`、`failed` 或 `abstained`。
- **冻结论文与工程扩展分离**：Artifact Paper 的 frozen metrics 不被 Phases 12-20 的工程改动静默改写。

```text
原始文件 / 目录存储
  -> 格式检测与路由
  -> extractor capability registry
  -> 格式专属确定性 extractor
  -> temporal / unit / profile validators
  -> structured ExtractionOutcome
  -> unified schema envelope
```

## 1. 文件摄入与格式检测

入口是 `extract_path(ExtractionRequest(...))`。系统首先判断输入是普通文件还是目录存储，然后收集格式信号：

- magic bytes：例如 HDF5、Parquet、classic NetCDF、ZIP container。
- directory signal：例如 Zarr v2 的 `.zgroup` / `.zarray` / `.zmetadata`。
- explicit format hint：只有在不与强 magic/container signal 冲突时才采纳。
- suffix 与保守 text probe：例如 CSV/TSV、JSON/JSONL、XML。

格式决策遵循：

```text
magic/container signature > compatible explicit hint > suffix/text probe
```

如果强信号冲突，系统会结构化弃权，不猜字段。

## 2. 确定性结构提取

每个注册 extractor 都通过 capability registry 调用，并返回结构化 outcome。

### CSV

CSV extractor 会读取表头并采样前 `sample_limit` 行，建立：

- `field_name` / `field_path`
- conservative physical type
- nullable、missing count、unique ratio、value range
- source evidence：`csv_header` 与 `sample_rows`
- bounded temporal analysis
- guarded logical / semantic / unit hints

当前 CSV 语义规则是保守的：

- `lat` / `longitude` 等明确坐标名可以映射为坐标语义。
- 有明确环境/气象上下文的 temperature 字段才可成为 `air_temperature`。
- 有明确 GPU 上下文的 `gpu_*temp*` 字段映射为 `gpu_temperature`。
- 泛化的 `temp` 不再自动提升为 `air_temperature`。
- `_c` / `_f` / `_k` 只有在 temperature-like 字段中才作为温度单位；`input_dim_c` 这类 channel count 不产生 Celsius claim。

### 其他已注册格式

- HDF5：遍历 group/dataset，保留 path、dtype、shape 和显式 attributes。
- NetCDF/CF：解析 dimensions、variables、CF coordinate attributes、calendar、units 和 missing markers。
- Zarr v2：只读本地目录存储元数据，不读 chunk payload，不声称 remote store / Zarr v3 / full Xarray reconstruction。
- Parquet/Arrow：读取 footer 和 embedded Arrow schema，不读 row values。
- JSON/JSON Lines：做 sample-bounded observed path/type-set extraction，并区分 declared JSON Schema 与 observed examples。
- XML/XSD：做 lightweight namespace-aware element/attribute observation 和 XSD declaration extraction，不是完整 validating XML processor。

## 3. Temporal、Unit 与 Profile 验证

提取物理字段后，系统运行共享验证层：

- temporal semantics：候选时间字段、canonical axis 选择、timezone、frequency、regularity、missing intervals、ambiguity/conflict issues。
- unit normalization：只对有证据的 unit claim 做 UCUM-like normalization；无法映射则记录 `unmapped_unit`。
- deterministic profile：记录 missingness、identifier quality、relationship candidates 等诊断信息。

这些验证结果是证据化 claim，不是额外的自由推断层。

## 4. 受限语义层

历史实验中存在 LLM-assisted semantic annotation，但它只在确定性 schema 之后工作：

- 不能创建物理字段。
- 不能覆盖显式元数据。
- 非 `unknown` claim 必须引用 supporting evidence。
- 冲突必须记录，而不是静默合并。

因此本项目应被理解为 **agent-ready deterministic schema substrate**，而不是 autonomous data agent。

## 5. Unified Schema Envelope

`extract_unified()` 会把 legacy outcome 投影到统一 envelope：

- identity
- format detection
- extractor capability
- outcome issues
- physical structure
- logical roles
- semantic hints
- units
- temporal semantics
- claims
- evidence
- provenance
- conflicts / abstentions / unsupported features

Envelope 是 additive projection，不提升新的语义真值，也不替代 legacy schema。

## Phase 20 收敛边界

Phase 20 的目标是发布级 artifact readiness：

- 当前完整回归测试：`183 passed`。
- release-readiness audit：`ready=true`。
- frozen Artifact Paper artifacts 不变。
- Phases 12-20 作为 companion engineering evidence，不改写 frozen paper metrics。

更多说明见 `docs/phase20_companion_engineering_appendix.md`。
