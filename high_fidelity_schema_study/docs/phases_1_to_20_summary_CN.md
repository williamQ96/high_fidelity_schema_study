# 高保真模式提取研究：Phase 1-20 总结

本文档提供了本项目已实现的 20 个工程与研究阶段的中文总结，清晰阐述了每个阶段的**目的**与**实现方法**。

---

## Phase 1: 仓库与产物脚手架搭建 (Repository And Artifact Scaffolding)
* **目的**：
  建立基础的代码库结构、标准数据模型、命令行接口 (CLI) 入口点，以及用于基线模式复制和外部数据摄取的自动化构建脚本。
* **实现方法**：
  * 创建了主项目包结构和依赖配置文件 (`requirements.txt`, `requirements-dev.txt`)。
  * 实现了 [models.py](../models.py)，定义了字段声明、证据层级和提取结果的标准数据契约。
  * 开发了 [cli.py](../cli.py)，作为协调模式提取任务的轻量级控制台入口。
  * 编写了初始执行日志 ([log.md](../log.md)) 并梳理了结构化的项目大纲。

## Phase 2: 内部试点语料库 (Internal Pilot Corpus)
* **目的**：
  构建一个代表性的、小规模的测试数据集（即“试点语料库”），包含多种异构文件，用以在不同的文件格式、大小和复杂度下验证提取框架的健壮性。
* **实现方法**：
  * 设计了 3x3 的试点矩阵：包含 3 种格式（CSV、HDF5 和时间序列组织），横跨 3 个难度等级（简单、中等、困难）。
  * 生成了 9 个合成数据集并存放在 [data/raw](../data/raw) 目录下，涵盖了不同程度的元数据质量与结构歧义。
  * 为每个数据集配备了说明性 README 侧车文件，并编译了机器可读的试点清单文件 (`pilot_corpus_manifest.json`)。

## Phase 3: 黄金参考模式构建 (Gold Reference Construction)
* **目的**：
  建立经人工验证的参考元数据模式（即“Gold 模式”），作为衡量确定性与语义提取器准确性的地标真值（Ground Truth）。
* **实现方法**：
  * 在 [data/gold](../data/gold) 下手工编写了 9 个字段级参考 JSON 模式文件。
  * 对每个字段记录了期望的物理类型、逻辑类型（坐标、测量值、标识符）、语义类型、物理单位以及字段的必要性/重要度。
  * 进行了第二轮人工一致性审查（记录在 [gold-schema-second-pass-2026-05-11.md](../docs/gold-schema-second-pass-2026-05-11.md)），对 50 个字段进行了校验，防止标签不一致或定义冲突。

## Phase 4: 确定性提取基线 (Deterministic Extraction Baseline)
* **目的**：
  构建针对 CSV 结构、HDF5 层级和时间序列列的确定性解析器，在不依赖 LLM 猜测的前提下建立物理模式和诊断谱图。
* **实现方法**：
  * 实现了特定格式的提取引擎（CSV 和 HDF5 遍历解析）以及共享的时间序列分析模块。
  * 将 HDF5 的字符类型数据集标准化为标准字符串类型，而非原始 Python 对象。
  * 在 `metadata.deterministic_profile` 诊断字段下添加了缺失率、唯一 ID 质量以及多文件候选关联关系剖析（见 [internal_relationship_profile.json](../data/derived/internal_relationship_profile.json)）。
  * 自动批量生成派生模式并存入 [data/derived](../data/derived)。

## Phase 5: 外部语料库准备 (External Corpus Preparation)
* **目的**：
  从公共学术仓库（Dryad 和 Zenodo）下载并准备多样化的真实科学数据集，以验证提取框架的泛化能力。
* **实现方法**：
  * 在清单文件 `curated_sources.json` 中配置并维护精选的科学文献关联数据源。
  * 编写 [import_external_corpus.py](../import_external_corpus.py) 脚本用于下载数据集，利用公共下载流链接规避 API 授权限制和限频阻碍。
  * 在 [data/external](../data/external) 下整理了 16 个文件的外部语料库，并在 [data/external/derived](../data/external/derived) 生成对应的确定性派生模式。
  * 对文件进行了分类评估，划分为 10 个晋级目标、4 个干扰项和 2 个排除文件。

## Phase 6: 验证与回归防护 (Validation And Regression Protection)
* **目的**：
  建立持续集成 (CI) 守卫规则和全面的单元测试覆盖，确保代码修改不会导致现有解析器退化。
* **实现方法**：
  * 在 [tests](../tests) 目录下实现 pytest 单元测试，检查 CSV 解析、HDF5 层级结构以及时间序列规律性。
  * 编写了回归测试以比对提取字段和期望属性子集的一致性，防止静默回归。

## Phase 7: 评估管道构建 (Evaluation Pipeline)
* **目的**：
  制定定量评估指标，以衡量模式提取运行的完备性、准确性、必要字段覆盖率和置信度校准。
* **实现方法**：
  * 创建了 [evaluate_internal_baseline.py](../evaluate_internal_baseline.py)，将派生模式与黄金参考真值进行逐字段的比对。
  * 在物理、逻辑和语义三个层级分别计算完备性与准确性指标。
  * 产生了按错误类型归类的故障分析总结（例如未解析列、数据类型错误）以及置信度分桶校准统计。

## Phase 8: 语义增强层 (Semantic Augmentation Layer)
* **目的**：
  引入基于证据约束的下游语义标注接口，使用 LLM 辅助填补和细化逻辑/语义类型，且绝不篡改物理解析器提取出的原始结果。
* **实现方法**：
  * 在 [semantic_layer.py](../semantic_layer.py) 中设计了语义标注契约接口。
  * 在 [data/semantic_grounding](../data/semantic_grounding) 下生成元数据和 README 信息的背景上下文关联包，作为 LLM 的检索物料。
  * 编写 [semantic_annotate.py](../semantic_annotate.py)（按字段分片的 LLM 标注器）和 [merge_semantic_annotations.py](../merge_semantic_annotations.py)（具备强规则安全限制的回写合并程序）。
  * 记录所有元数据声明与 LLM 推断的冲突，保留提取的透明度。

## Phase 9: 检索实验 (Retrieval Experiment)
* **目的**：
  评估基于高保真模式增强的元数据检索，在检索和定位数据集时相比于“仅元数据”和“仅 README”传统检索方式的性能提升。
* **实现方法**：
  * 为三种元数据配置（仅 README、仅元数据、模式增强元数据）构建了词法检索索引。
  * 针对已选定的 10 个基准测试目标设计了 10 个 planted（埋点）查询。
  * 编写 [evaluate_retrieval_artifacts.py](../evaluate_retrieval_artifacts.py) 并输出 Recall@k、Precision@k、MRR 和 nDCG 指标，实验表明模式增强能大幅拉升检索召回率。

## Phase 10: 语料库扩展与加固 (Scale-Up And Corpus Hardening)
* **目的**：
  规范化基准测试文件准入/排除准则，划定无法确定或极低置信度的原始二进制文件与异构结构的提取界限。
* **实现方法**：
  * 制定了明确的文件准入与排除文档。
  * 确立了对原始二进制文件的避让机制（不做出物理/逻辑字段断言，仅保留文件级别的哈希和证明路径）。

## Phase 11: 论文及最终交付物 (Frozen Benchmark Release)
* **目的**：
  冻结评估数据集和基线代码，编译用于发表的研究结果数据表与 SVG 图表，并提供可视化评审工作台。
* **实现方法**：
  * 将试点和外部数据集配置永久冻结在 [benchmark_freeze_2026-05-04.json](../docs/benchmark_freeze_2026-05-04.json) 中。
  * 编写 [build_paper_tables.py](../build_paper_tables.py) 和 [build_paper_figures.py](../build_paper_figures.py)（在 [docs/figures](../docs/figures) 下自动绘制 SVG 图表）。
  * 撰写了完整的学术论文草稿 [paper_draft.md](../docs/paper_draft.md)。
  * 编写了位于 [gui_demo](../gui_demo) 的 HTML/JS 可视化演示网页，支持使用 Python 运行一个包含实时本地提取接口 (`server.py`) 的端到端数据审查工作台。

## Phase 12: 确定性基底升级 (Deterministic Substrate Upgrade - 冻结后开发)
* **目的**：
  重构核心数据处理结构，引入通用接口注册表和格式决策路由，并加入保留时区的通用时间戳规则引擎。
* **实现方法**：
  * 实现了基于格式魔数（Magic Number）和信号的确定性能力注册中心及分流器。
  * 统一和类型化提取请求与返回载荷（`ExtractionRequest`, `ExtractionOutcome`）。
  * 构建独立的保留时区时间语义验证模块，用于解析各种时间轴频率、规整度与数据冲突。
  * 并在包含 13 个边缘用例的 Phase 12 挑战包上完成了准确性验证。

## Phase 13: NetCDF/CF 注册表扩展 (NetCDF/CF Registry Extension)
* **目的**：
  在通用提取注册表中集成第一个全新的科学数据格式：NetCDF 及其气候和预测 (CF) 元数据规约。
* **实现方法**：
  * 编写了 NetCDF classic 提取器（通过 `scipy`）和 NetCDF4 提取器（通过遍历 `h5py` 文件底层结构）。
  * 提取变量、维度、属性、缺省标记、CF 坐标轴特征以及时间日历。
  * 重用 Phase 12 的时间语义校验子系统，并在 14 个 NetCDF/CF 验证用例的挑战包上通过了兼容性测试。

## Phase 14: Zarr / 兼容 Xarray 的科学数组提取 (Zarr Array Extraction)
* **目的**：
  扩展提取框架以支持多文件目录流（如 Zarr v2），并在 producer 导出布局以及第三方库兼容性（Xarray, zarr-python）上完成全面对照。
* **实现方法**：
  * **Phase 14A (摄取与基本功能)**：扩展资源感知以辨识本地文件夹结构，实现不依赖底层大科学依赖的轻量 Zarr 元数据分析，解析 `.zarray` 物理元数据、`.zgroup` JSON 和 `_ARRAY_DIMENSIONS` 映射，并在 14 个挑战用例上进行测试。
  * **Phase 14B (物理兼容度)**：开发了一个 17 个用例的本地 Zarr 物理兼容性测试集，重塑了 NumPy 结构化 Dtype 支持，完成了斜杠子层级 Chunk 目录剪枝和组内坐标隔离校验。
  * **Phase 14C (外部标准一致性)**：集成了一个 12 用例的 Zarr Conformance 语料库，直接对比框架的元数据 preserving 输出与主流 `zarr-python` 与 `Xarray` 实际加载对象的一致性。

## Phase 15A: Parquet / Arrow 元数据优先提取 (Parquet / Arrow Metadata-First Extraction)
* **目的**：
  在不读取庞大行数据的前提下，快速、高保证地解析 Parquet 文件页脚和内嵌的 Arrow logical schema 信息。
* **实现方法**：
  * 编写了基于 `pyarrow` 的 Parquet 解析能力并注册到中心调度器。
  * 递归解构 Arrow 逻辑层级字段（支持嵌套类型、时区戳），并记录 Parquet 底层物理特性（压缩算法、列编码、Row Groups 和页脚统计信息）。
  * 在 8 个精心挑选的 Parquet 挑战文件上完成了评估。

## Phase 16A: 保守性 JSON 结构提取 (Conservative JSON Structure Extraction)
* **目的**：
  实现针对任意 JSON 或 JSON Lines 格式的物理轮廓推断，并在伴随有 JSON Schema 声明文件时记录实际样例与模式契约的冲突。
* **实现方法**：
  * 引入受采样范围限制的 JSON 键值和多类型值路径递归发现器。
  * 支持提取外部 JSON Schema 声明，并自动比对实际解析样例（如实际存在 Null 或非预期类型）并记录为 Issue 冲突。
  * 在 6 个 JSON 挑战用例上通过了测试。

## Phase 16B: 轻量级 XML / XSD 结构提取 (Lightweight XML / XSD Structure Extraction)
* **目的**：
  提取 XML 标签拓扑、命名空间信息，并提取轻量级 XML Schema Definition (XSD) 元素声明与多态冲突。
* **实现方法**：
  * 实现了命名空间感知的 XML 元素和属性树路径观察器。
  * 自动发现数组重复项、提取内嵌 XSD 的元素定义，并标记 `xsi:type` 等声明性Issue。
  * 在 5 个 XML 挑战用例上通过了评估。

## Phase 17: 统一模式信封 (Unified Schema Envelope)
* **目的**：
  构建一个版本化、标准化的通用数据模型包装信封，将各种不同数据格式提取出的结构和字段无损地投影成一致的数据表示。
* **实现方法**：
  * 增加了 `extract_unified()` API 入口，将各类具体提取器（CSV, HDF5, Zarr, NetCDF, Parquet, JSON, XML）产生的格式特征，统一整理成标识、物理、逻辑、语义、证据链和 provenance 信息。
  * 确保原解析器的结果不可变性与后向兼容，在 8 个格式的 envelope validator 上完成了无缝校验。

## Phase 18: 统一评估工具链 (Unified Evaluation Harness)
* **目的**：
  将历史上所有的基准数据集、兼容性测试包以及扩展挑战音轨的定量评估，整合进单一的统一运行入口。
* **实现方法**：
  * 编写了统一比对评估脚本，独立驱动 11 条测试轨道。
  * 坚持“指标分立”原则，不对各格式的测试结果做非科学的加权平均，保障每个数据格式的性能透明度。

## Phase 19: 面向 Agent 的数据束导出 (Agent-Ready Exports)
* **目的**：
  为下游的 AI 编码代理或数据大模型提供结构化、只读的数据提取背景和交互接口，保护底层物理提取不被静默污染。
* **实现方法**：
  * 构造了专用的数据上下文 JSON 束，里面封装了确切的证据链条、Provenance 步骤和用于语义搜索的字段特征。
  * 增加代理写保护锁（Canonical-Mutation Guards），防止大模型输出反向修改原始数据的物理模式定义。

## Phase 20: 发布就绪度审计与工作台 (Release Readiness Audit & Workbench)
* **目的**：
  对整个研究代码库的可移植性、路径洁净度以及自动化演示工具进行发布前的终审与收尾。
* **实现方法**：
  * 为所有 8 种数据格式提供了免配置的可运行演示样本，清理了所有绝对文件路径以保证零配置随处运行。
  * 撰写了 [DESIGN.md](../gui_demo/DESIGN.md) 梳理界面体系。
  * 通过了最终的发布就绪度审计脚本校验（`ready=true`）。
