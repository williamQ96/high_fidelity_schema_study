# 当前阶段报告

日期：2026-05-01

## 1. 我们一开始的目标是什么

这个项目一开始的目标很明确：

- 做一个 **high-fidelity schema extraction study**
- 避免“把文件扔给 LLM，然后让它猜 schema”这种弱方法
- 采用 **deterministic-first** 的路线
- 让 LLM 只做受约束的语义补充，而不是凭空创造结构
- 把评估保持在 **field level**，而不是压成一个不可解释的总分

换句话说，这个项目不是在做“模型猜字段”，而是在做：

- 文件结构可证据化提取
- 语义层可追溯补充
- retrieval 行为可解释比较

## 2. 计划是什么

项目原始计划可以概括为 7 步：

1. 定义目标 schema 和评估维度。
2. 建立一个小型 internal pilot corpus。
3. 做 deterministic extractors 和 baseline。
4. 扩展到来自 Zenodo / Dryad 的 external corpus。
5. 建 retrieval artifacts，并比较不同 retrieval baseline。
6. 增加 evidence-constrained semantic layer。
7. 评估 semantic augmentation 是否真的带来收益。

## 3. 方法是什么

核心方法是：

```text
Raw Dataset
  ->
File Type Detection
  ->
Deterministic Structural Extraction
  ->
Field-Level Evidence Capture
  ->
Semantic Annotation / Normalization
  ->
Uncertainty Estimation
  ->
Schema Output + Provenance
  ->
Evaluation
```

项目的关键方法论承诺是：

- **先 deterministic，后 semantic**
- **每个 claim 都要有 evidence**
- **semantic layer 不能覆盖明确的结构证据**

## 4. 一些重要术语

### Pilot

`pilot` 指的是为了验证方法而故意构造的小规模、可控、可解释的数据集集合。

它不是最终 benchmark，而是用来回答：

- pipeline 能不能跑通
- schema 输出长什么样
- 评估维度是否合理
- 失败模式在哪里出现

### Gold

`gold` 是人工写的参考真值。

它是字段级 answer key，记录：

- physical type
- logical type
- semantic type
- unit
- necessity

Gold 不是模型输出。  
Gold 是模型和系统输出要被比较的对象。

### External

`external` 指的是来自外部公开仓库的真实数据，而不是我们自己手工构造的 internal pilot。

当前 external 主要来自：

- Zenodo
- Dryad

### Same-family distractor

`same-family distractor` 指的是和目标文件来自同一个 dataset family / 同一个 record bundle，但不是 query 真正要找的文件。

这种 distractor 很难，因为它们共享：

- 背景描述
- 关键词
- 类似字段
- 同一研究语境

### Cross-domain distractor

`cross-domain distractor` 指的是来自不同主题、不同数据家族的数据文件。

这种 distractor 适合测广义泛化，但通常没有 same-family distractor 那么难。

## 5. 我们现在已经做到了什么

### Internal pilot

已经完成：

- 9 个 internal pilot dataset
- 9 个 gold schema
- 9 个 deterministic derived schema

覆盖：

- CSV
- HDF5
- time-series

### Deterministic extraction

已经完成：

- conservative CSV extractor
- time-series profiler
- HDF5 extractor
- deterministic batch builders

### Evaluation

已经完成：

- internal field-level baseline evaluation
- uncertainty analysis
- grouped error-mode analysis

### External corpus

已经完成：

- curated external source manifest
- Dryad + Zenodo 的本地 external corpus
- 当前 curated external 文件的 deterministic derived schema

当前 external corpus：

- `16` 个本地文件
- `16` 个 derived schema

### Retrieval

已经完成：

- `metadata_only`
- `readme_only`
- `schema_enhanced`

三套 retrieval artifacts，以及 planted query set 和 retrieval report。

当前 retrieval pool：

- `16` 个文件
- `10` 个 target
- `6` 个 distractor

### Semantic layer

已经完成：

- semantic grounding bundle generation
- semantic annotation runner
- result normalization
- validation
- conservative merge-back
- semantic merge report

当前 semantic smoke 结果：

- `2` 个 internal task
- `4` 个 external task

## 6. 我们特别的方法论

这个项目有几个特别重要的方法论选择。

### 分层 schema

我们明确分成：

- physical schema
- logical schema
- semantic schema

这样可以避免把“看得见的结构”与“推断出来的意义”混在一起。

### Evidence-grounded merging

semantic layer 不是想改什么就改什么。

如果 semantic 输出：

- 没有 supporting evidence
- 和 explicit metadata 冲突
- logical type 与 semantic type 不兼容

那么它会被记录，但不会直接 merge 回 schema。

### No-regression-first semantic policy

semantic layer 当前是偏保守的：

- 优先不破坏 deterministic baseline
- 先保证 merge 安全
- 再追求真正收益

这使得 semantic layer 目前是：

- 安全
- 可执行
- 但收益还不稳定

## 7. 当前结果概览

### Internal deterministic baseline

目前 internal baseline 很强。

关键指标：

- physical completeness: `1.0000`
- physical accuracy: `0.9815`
- logical accuracy: `0.9444`
- semantic accuracy: `1.0000`

这意味着 deterministic baseline 已经解决了问题的大部分。

### Retrieval

在当前 `16-file / 10-target` 的 retrieval pool 上：

- `metadata_only recall_at_1 = 0.6000`
- `readme_only recall_at_1 = 0.5000`
- `schema_enhanced recall_at_1 = 0.8000`

这说明：

- schema-enhanced 表示在更大的 Dryad+Zenodo pool 上依然明显领先

### Semantic merge

目前 semantic merge 的状态是：

- 已经存在 accepted merge
- 没有观察到 regression
- 但 internal 已评估样本上还没有明确的 metric-level gain

这很重要，因为它说明：

- semantic layer 不是空的
- semantic layer 也还没被证明已经稳定“有用”

## 8. 当前的限制是什么

### 1. semantic execution 可靠性

有些 semantic task 失败，不是因为没数据，而是因为：

- timeout
- endpoint 不稳定
- context 压力

这仍然是当前最大的工程瓶颈。

### 2. semantic yield 还偏低

semantic layer 已经能产生 accepted merge，但仍然存在：

- 很多输出没有足够 supporting evidence
- 很多 semantic claim 仍然只能被安全拒绝
- accepted merge 还太少，难以稳定带来 metric gain

### 3. benchmark 规模还不够最终化

我们现在有：

- 强 internal pilot
- 有意义的 external retrieval pool

但还不是最终冻结的大 benchmark。

### 4. 人工复核还没做完

gold 仍然需要第二轮人工 review，如果目标是论文发表，这一步不能省。

## 9. 现在还需要人工做什么

目前已经不太需要继续手工补数据。

更需要的人工工作将是：

- benchmark freeze 决策
- gold 二次复核
- paper-level 结果解释与写作

## 10. 下一步最该做什么

当前最值得做的事是：

1. 提高 semantic annotation 的 evidence 产出率。

也就是：

- 继续把 task 切小
- 保持 evidence-first prompt
- 优先跑字段级或小字段组级请求
- 目标是找到第一个能带来 measurable gain 的 accepted semantic merge

## 11. 如何收敛

项目还没有收敛到最终科学终态。

### 已经接近收敛的部分

- deterministic extraction 主干
- baseline evaluation 主干
- retrieval comparison 主干
- external corpus ingestion 主干

### 还没有收敛的部分

- semantic layer 的净收益
- 最终 benchmark freeze
- paper-ready final reporting

从这里往下，最清晰的收敛条件是：

- 至少有一个 accepted semantic merge
- 在不止一个样例上
- 能稳定带来 gold-aligned 指标提升

在这之前，semantic layer 最准确的状态描述仍然是：

- **safe but not yet proven beneficial**

## 12. Bottom Line

当前阶段可以概括为：

- deterministic extraction：工作正常
- field-level evaluation：工作正常
- larger external retrieval pool：工作正常
- retrieval 上 schema-enhanced 优势：已经证明
- semantic execution path：工作正常
- semantic merge safety：已经证明
- semantic net gain：还没有证明
- final benchmark：还没冻结
- paper stage：还没到

项目现在处于一个很强的实验系统阶段。

下一步真正的关键里程碑，不再是增加更多基础设施，而是：

**让 safe semantic augmentation 变成 consistently useful semantic augmentation。**
