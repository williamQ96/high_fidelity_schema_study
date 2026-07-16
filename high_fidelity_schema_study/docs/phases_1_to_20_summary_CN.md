# High-Fidelity Schema Extraction Study：Phases 1-20 中文摘要

本文给出项目 1-20 阶段的当前可读摘要。它用于解释项目如何从 frozen Artifact Paper 逐步收敛为可审查、可复现、边界清楚的 deterministic schema substrate。

## Phase 1-3：基础、语料与 Gold

- Phase 1 建立代码结构、数据模型、CLI、模板和初始项目日志。
- Phase 2 构建 3x3 内部 pilot corpus，覆盖 CSV、HDF5、time-series 三类输入和 easy/medium/hard 难度。
- Phase 3 编写人工 gold schema，并完成第二轮一致性审查。

这些阶段定义了项目的基本评估对象：field-level physical / logical / semantic / unit truth。

## Phase 4-7：确定性 baseline 与评估

- Phase 4 实现 CSV、HDF5 和 time-series deterministic extraction baseline。
- Phase 5 准备 Dryad / Zenodo 外部候选语料，用于 retrieval slice。
- Phase 6 建立回归测试，防止解析行为静默退化。
- Phase 7 构建 internal baseline evaluator，按 physical、logical、semantic、unit 等维度评分。

这些阶段形成 frozen Artifact Paper 的核心实验基础。

## Phase 8-11：语义增强、检索与论文 artifact

- Phase 8 引入 evidence-constrained semantic annotation，LLM 只能在 deterministic fields 上做受限补充，不能创造物理字段。
- Phase 9 构建 schema-enhanced retrieval experiment，与 metadata-only / README-only baseline 比较。
- Phase 10 固化 raw binary abstention 和 benchmark promotion policy。
- Phase 11 冻结 paper benchmark slice，生成 tables、figures、paper draft 和 GUI demo。

这一组阶段产生 frozen Artifact Paper 的主要结果。后续阶段不静默改写这些 headline metrics。

## Phase 12：Deterministic Substrate

Phase 12 引入中央 extraction orchestration API、capability registry、format signal / decision、structured issue、success / partial / failed / abstained outcome，以及独立 temporal semantics subsystem。

核心边界：没有 spec-backed extractor 时不猜字段；冲突和不确定性必须显式呈现。

## Phase 13：NetCDF/CF

Phase 13 用 Phase 12 contracts 增加 NetCDF/CF registry extension，提取 dimensions、variables、attributes、CF coordinates、calendar、units、fill/missing markers，并复用 temporal/unit validators。

边界：不是完整任意 NetCDF4 重建；non-standard calendars 保留但不强行解码。

## Phase 14A-14C：Zarr

- Phase 14A 支持本地 Zarr v2 directory store metadata extraction。
- Phase 14B 增加 producer-shaped compatibility corpus，覆盖 structured dtype、chunk-directory pruning、group-scoped coordinates 等。
- Phase 14C 增加 official / pinned-library metadata conformance evidence。

边界：不读 chunk payload，不支持 remote stores、Zarr v3 或 full Xarray reconstruction。

## Phase 15A：Parquet / Arrow

Phase 15A 增加 PyArrow-backed Parquet footer 和 Arrow schema extraction，记录 nested paths、nullability、row groups、encodings、compression、metadata 和 footer statistics。

边界：不读 row values，不独立验证 footer statistics。

## Phase 16A-16B：JSON 与 XML

- Phase 16A 实现 JSON / JSON Lines bounded observed structure extraction，并区分 declared JSON Schema 与 observed examples。
- Phase 16B 实现 lightweight namespace-aware XML / XSD structure extraction，并记录 `xsi:type` conflict。

边界：JSON 是 sample-bounded observation；XML 不是 full validating XML Schema processor。

## Phase 17：Unified Schema Envelope

Phase 17 增加 `extract_unified()`，把 legacy outcomes 投影到统一 envelope：identity、format detection、physical structure、logical roles、semantic hints、units、temporal semantics、claims、evidence、provenance、conflicts、abstentions 和 unsupported features。

边界：envelope 是 additive projection，不提升新的语义真值。

## Phase 18-19：Unified Evaluation 与 Agent Exports

- Phase 18 增加统一 evaluation entrypoint，但保持各 track 指标分离，不计算误导性的 aggregate score。
- Phase 19 增加 read-only agent-ready exports，agent 可查看 evidence 和上下文，但不能修改 canonical claims。

边界：项目是 agent-ready deterministic substrate，不是 autonomous data agent。

## Phase 20：Release Readiness 与最终收敛

Phase 20 完成 release-readiness audit、pinned dependencies、CI、demo examples、GUI scratch extraction、reviewer demo script、路径卫生检查和 frozen artifact diff 检查。

2026-06-28 final convergence pass 进一步完成：

- companion engineering appendix：`docs/phase20_companion_engineering_appendix.md`；
- 当前完整回归测试状态：`183 passed`；
- release-readiness audit：`ready=true`；
- public docs 对 frozen paper 与 post-freeze engineering evidence 的边界表述保持一致；
- CSV semantic guardrails：GPU temperature 不再被提升为 `air_temperature`，`input_dim_c` 不再产生 Celsius unit claim；
- Office lock files 被忽略，不纳入版本控制。

## 当前边界

- Frozen Artifact Paper metrics、tables、figures、qrels、benchmark freeze 和 `data/derived` 不因 Phases 12-20 自动改变。
- Phases 12-20 是 companion engineering evidence，不是新的 headline benchmark。
- Bounded challenge-pack `1.0000` 结果只证明声明的受控用例，不代表广泛生态鲁棒性。
- 下一步真正扩大论证力，应做多生产者、多来源外部兼容性验证，而不是增加无边界 agent autonomy。
