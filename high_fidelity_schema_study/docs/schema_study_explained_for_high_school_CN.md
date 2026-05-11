# 高中生也能读懂的 Schema 提取研究说明

## 一句话说明

我们在做一件事：**让电脑可靠地读懂科学数据文件里有哪些字段、每个字段是什么意思、哪些说法有证据、哪些地方还不确定。**

这里的 `schema` 可以理解成数据文件的“说明书”或“目录”。

比如一个天气 CSV 文件里有这些列：

- `station_id`
- `temperature`
- `humidity`
- `dateTime`

只看到这些名字，人类大概能猜到含义。但研究里不能只靠猜。我们要让系统回答：

- 这个字段在文件里是什么类型？字符串、整数、小数、时间？
- 它在逻辑上是什么角色？编号、时间轴、测量值、坐标、标签？
- 它在现实世界里是什么意思？气温、湿度、经度、纬度？
- 单位是什么？
- 这个判断来自哪里？文件名、列名、样例值、README、HDF5 属性？
- 我们有多确定？

这就是整个项目的核心。

## 为什么不能直接让大模型猜

如果直接把文件名和几行数据丢给大模型，让它生成 schema，问题是：

- 它可能猜对。
- 它也可能编出文件里没有的字段。
- 它可能把不确定的东西说得很确定。
- 它很难告诉我们“我这个判断的证据在哪里”。

科学数据处理不适合这种黑箱方式。我们需要的是：

- 能复现
- 能审查
- 能指出证据
- 不知道就说不知道

所以这个项目采用 **deterministic-first** 的路线。

意思是：**先用确定性的程序从文件本身提取结构，再让 LLM 只做有证据的语义补充。**

## 整体流程

可以把整个系统想成一条生产线：

```text
原始数据文件
  ->
确定文件类型
  ->
确定性提取器读取结构
  ->
生成初始 schema
  ->
记录每个判断的证据
  ->
和 gold 答案对比
  ->
让 LLM 做有证据的语义补充
  ->
合并通过验证的补充
  ->
评估是否真的变好
  ->
用于检索实验和最终报告
```

这条线的设计原则是：

- 文件里能确定的东西，程序先提取。
- 文件里不确定的东西，不强行猜。
- LLM 只能补充有证据支持的内容。
- 所有结果都要能评估。

## 关键 component 是什么

### 1. Raw Dataset：原始数据文件

这是最开始的材料。可能是：

- CSV 表格
- HDF5 层级文件
- 时间序列数据

它们就像实验材料。没有原始文件，后面的 schema、评估、检索都没有来源。

为什么重要：

- schema 必须从真实文件来。
- 不能脱离文件凭空写说明。

### 2. Pilot：小规模试验集

`pilot` 是一个小而可控的数据集集合。

这里有 9 个内部 pilot 数据集：

- CSV：easy、medium、hard
- HDF5：easy、medium、hard
- time-series：easy、medium、hard

它的作用类似“先做小实验”。

为什么要有 pilot：

- 一开始不应该直接处理几百个复杂文件。
- 小数据集方便看清系统哪里对、哪里错。
- easy / medium / hard 可以测试系统是否只会处理简单情况。

为什么起作用：

- 如果系统在 pilot 上都跑不通，就没有必要马上扩大规模。
- 如果系统在 hard case 上出错，我们能快速定位原因。

### 3. Gold：人工参考答案

`gold` 是人工写的标准答案。

比如一个字段 `temperature`，gold 里会写：

- physical type：float
- logical type：measurement
- semantic type：air_temperature
- unit：Celsius

Gold 不是模型预测出来的，而是我们用来评估模型和程序的答案。

为什么要有 gold：

- 没有标准答案，就不知道系统做得好不好。
- 只看输出“像不像”不够科学。
- 我们要算准确率、错误类型和改进幅度。

为什么起作用：

- 系统输出可以逐字段和 gold 对比。
- 可以知道错误发生在哪一层：物理类型、逻辑角色、语义含义还是单位。

### 4. Deterministic Extractor：确定性提取器

这是最基础的自动程序。

它做的事情包括：

- 读 CSV header。
- 看每一列样例值。
- 判断整数、小数、字符串、时间。
- 读 HDF5 的 group、dataset、attribute。
- 检查时间序列是否有时间轴。

它的特点是：同一个输入，每次运行结果一样。

为什么要先用它：

- 它稳定。
- 它不会幻想文件里不存在的字段。
- 它能直接记录证据，比如 `header='dateTime'`。

为什么起作用：

- 很多 schema 信息其实就在文件结构里。
- 比如列名、数据类型、HDF5 路径、单位后缀，本来就可以用程序提取。

### 5. Derived Schema：程序生成的 schema

`derived schema` 是确定性提取器生成的结果。

它记录每个字段：

- 字段名
- 字段路径
- 物理类型
- 逻辑类型
- 语义类型
- 单位
- 样例值
- 证据
- 置信度

为什么要保存它：

- 后续评估要用。
- 后续 LLM 语义补充要基于它。
- 检索实验也会用 schema 文本。

为什么起作用：

- 它把原始文件变成可比较、可查询、可评估的结构化对象。

### 6. Evidence：证据

每个 schema 判断都应该有证据。

证据可能来自：

- CSV header
- 样例行
- HDF5 attribute
- README 文档
- 文件名
- source record metadata

比如：

```text
字段：temperature
判断：measurement / air_temperature
证据：header='temperature'
证据：README 写了 weather station data
```

为什么要证据：

- 没有证据，schema 就只是猜测。
- 有证据，别人可以审查这个判断。
- 有证据，LLM 的输出才能被限制。

为什么起作用：

- 它让系统从“我觉得”变成“我根据这个证据判断”。

### 7. Evaluation：评估

评估就是把 derived schema 和 gold 对比。

当前内部 baseline 指标包括：

- physical completeness
- physical accuracy
- logical accuracy
- semantic accuracy
- unit accuracy
- necessary-field coverage
- uncertainty behavior
- error modes

简单说：

- completeness 看有没有漏字段。
- accuracy 看判断对不对。
- error modes 看错在哪里。

为什么要评估：

- 没有评估，就不知道系统是否真的进步。
- 只说“看起来不错”不够。

为什么起作用：

- 可以看到具体问题，比如 `logical_unknown`、`time_axis_mismatch`。
- 可以知道改动之后指标是否提升。

### 8. Semantic Layer：语义增强层

确定性程序擅长读结构，但不总是擅长理解含义。

比如字段 `val`：

- 程序看到它是字符串。
- README 说它是 numeric observations mixed with non-detect markers。
- 所以物理类型应该保留 string。
- 但逻辑上它是 measurement。

这类地方可以让 LLM 帮忙。

但 LLM 不能自由发挥。它必须：

- 只处理指定字段。
- 只能基于 evidence。
- 没证据就写 unknown。
- 输出 structured JSON。
- 通过 validation。
- merge 时还要经过 safety checks。

为什么起作用：

- LLM 可以读懂 README 和字段上下文。
- 但 merge safety 防止它乱改。

目前已经证明的效果：

- `csv_hard_field_campaign` logical accuracy 从 `0.6667` 提到 `1.0000`。
- `csv_easy_weather_stations` logical accuracy 从 `0.8333` 提到 `1.0000`。
- Semantic merge report 目前覆盖 3 个内部任务，其中 2 个有可测量提升。

### 9. External Corpus：外部真实数据

内部 pilot 是小实验。外部数据来自 Dryad 和 Zenodo。

现在外部状态：

- 当前有 16 个外部 retrieval pool 文件。
- 其中 10 个是 promoted targets。
- 6 个是 hard distractors。
- Dryad 和 Zenodo 都有真实 payload。

为什么要外部数据：

- 内部 pilot 太干净，可能过于理想。
- 真实科学数据会有更多混乱情况。
- 检索实验需要真实数据标题、元数据和字段。

为什么起作用：

- 它让系统从 toy example 走向真实研究场景。

### 10. Retrieval Experiment：检索实验

这里的问题是：

如果用户问“我要找一个有天气站温度、湿度、气压的数据集”，系统能不能找到正确文件？

我们比较几种检索方式：

- metadata_only：只用数据源元数据
- readme_only：用 README-like 文本
- schema_enhanced_deterministic：加入确定性 schema
- schema_enhanced_semantic_merged：加入 semantic merge 后的 schema

为什么做 retrieval：

- schema 不只是为了好看。
- 好 schema 应该能帮助别人找到数据。

为什么起作用：

- 字段名、逻辑类型、单位、时间轴都能变成检索信号。
- 比如用户问 “wind speed”，schema 里有 `Wind_Speed_m_s` 和 unit，就更容易匹配。

当前结果：

- `metadata_only recall_at_1 = 0.7000`
- `readme_only recall_at_1 = 0.5000`
- `schema_enhanced recall_at_1 = 1.0000`
- `schema_enhanced_semantic_merged recall_at_1 = 1.0000`

注意：

这不是说系统已经解决所有检索问题。当前 query 是 planted queries，意思是我们故意设计了有明确答案的问题。它证明当前机制有效，但还不能代表所有真实用户问题。

### 11. Schema Source Comparison：schema 来源对比

我们现在不只看一个 schema-enhanced 版本，而是明确区分：

- deterministic schema
- semantic-merged schema

为什么要区分：

- 如果 semantic-merged 版本提升了检索，我们要知道。
- 如果它加入太多通用词导致检索变差，也要知道。

为什么起作用：

- 它让实验更公平。
- 不会把所有 schema-enhanced 结果混在一起。

### 12. Slice Disambiguation：切片区分

有些文件属于同一个数据集家族，只是不同年份、学校或月份。

比如：

- Greenland cod year1
- Greenland cod year2
- school_5
- school_6
- Data 01 Jan 2019
- Data 03 Mar 2019

它们字段很像，只靠 generic schema 很难区分。

所以我们加入了：

- `year1`
- `year2`
- `school5`
- `jan`
- `first-year`

这些 file-slice / time-slice 信号。

为什么起作用：

- 用户如果问 year1，系统需要知道哪个文件是 year1。
- 这不是语义猜测，而是文件身份的一部分。

### 13. Benchmark Freeze：冻结当前 benchmark slice

现在项目已经从“继续随便试”进入“要能守住当前结果”的阶段。

所以我们冻结了当前 slice：

- 9 个 internal pilot datasets
- 16 个 external retrieval-pool files
- 10 个 promoted targets
- 6 个 distractors
- 当前 retrieval systems
- 当前 regression subsets

冻结文件：

- `docs/benchmark_freeze_2026-05-04.md`
- `docs/benchmark_freeze_2026-05-04.json`

为什么要 freeze：

- 不然今天和明天的实验对象可能不一样。
- 指标变化可能只是因为数据池变了。
- 写论文或报告时必须知道到底评估了哪些文件。

为什么起作用：

- freeze JSON 可以被测试检查。
- 如果以后有人改了 pool，但没更新 freeze，测试会发现。

### 14. Regression Tests：回归测试

回归测试就是防止已经做对的东西以后被改坏。

我们现在新增了 external field-subset tests。

不是给所有外部文件做完整 gold，而是锁住高价值字段，比如：

Greenland cod year1：

- `Hourbin`
- `COA_Lat`
- `COA_Lon`
- `Tag`
- `Transplant`
- `Cove`

functional_traits：

- `Species`
- `Mass.g`

weatherMQ：

- `dateTime`
- `temperature`
- `relativeHumidity`
- `barometricPressure`
- `rainfall`
- `windSpeed`

为什么只测 subset：

- 外部真实数据太多，完整 gold 很贵。
- 但关键字段必须稳定。
- 这是一种实用的中间方案。

为什么起作用：

- 后续改 extractor、semantic merge 或 retrieval 时，如果这些关键字段漂移，测试会失败。

## 我们现在做到哪里了

当前已经完成：

- 内部 pilot corpus 建好。
- Gold reference 建好。
- CSV / HDF5 / time-series deterministic extractor 能跑。
- 内部 baseline evaluation 能生成报告。
- Dryad 和 Zenodo 外部语料已接入。
- 外部 derived schemas 已生成。
- Semantic annotation 和 merge-back 管线已实现。
- Semantic layer 已经在内部样本上产生可测量收益。
- Retrieval artifacts 已经支持 deterministic vs semantic-merged 对比。
- 同族文件的 year/school/month slice disambiguation 已加入。
- 当前 benchmark slice 已冻结。
- External field-subset regression tests 已加入。
- 当前测试通过：`32 passed`。

## 现在最重要的结论

### 结论 1：deterministic-first 是对的

大部分结构信息可以从文件本身稳定提取。

### 结论 2：LLM 有用，但必须被限制

LLM 最适合补充：

- README 里说明的含义
- 字段上下文里的逻辑角色
- 不容易靠程序判断的语义

但它不能自由改 schema。

### 结论 3：schema 能帮助检索

当前 planted retrieval set 上，schema-enhanced retrieval 明显强于 metadata/readme baseline。

### 结论 4：当前结果已经需要保护

所以我们 freeze 了当前 benchmark slice，并加了 regression tests。

## 还没有完成什么

### 1. Gold 还需要二次人工 review

Gold 是标准答案，所以它本身也要检查一致性。

### 2. Time-axis accuracy gap 还需要处理

目前有一些 time-axis 相关评估 gap。

下一步要判断：

- 是 extractor 没提好？
- 是 evaluation 定义不合适？
- 还是 gold/reference 表达方式需要调整？

不建议直接用 semantic layer 强行修这个，因为时间轴更像结构问题。

### 3. External semantic merges 还不是 gold

外部 semantic merge 是高置信工作注释，但还不是最终人工 gold。

如果要写论文或做正式 benchmark，仍然需要人工检查或更多文档证据。

### 4. Retrieval 还需要 harder queries

当前 10 个 query 是 planted set。它们适合验证机制，但还不等于真实用户检索鲁棒性。

后续需要：

- 非 planted queries
- 更难的 same-family distractors
- 更自然语言化的问题

## 下一步应该做什么

现在不要马上扩大数据集。应该先收敛。

推荐下一步：

### Step 1：处理 time-axis accuracy gap

目标：

判断 time-axis 问题到底属于：

- deterministic extractor
- evaluation logic
- gold definition

输出应该是一个小报告或 patch：

- 哪些 dataset 有 time-axis mismatch
- mismatch 的原因
- 应该改代码还是改评估

### Step 2：生成 paper-ready result tables

从当前 frozen benchmark slice 生成表格：

- 内部 baseline 表
- semantic merge gain 表
- retrieval comparison 表
- corpus summary 表
- limitation 表

这些表可以直接进入论文、报告或 presentation。

### Step 3：决定 semantic-merged retrieval 是否成为默认

现在我们有两个 schema-source：

- deterministic
- semantic_merged

下一步要决定：

- 论文里是否都展示
- 默认系统用哪个
- semantic_merged 是否只作为 ablation

目前更稳妥的做法：

**两个都保留，作为对比实验。**

### Step 4：做 gold 二次 review

尤其是内部 pilot gold。

因为 gold 是评估基础，gold 如果不一致，指标就会误导我们。

## 最后总结

这个项目不是在做“让大模型猜 schema”。

它真正做的是：

1. 用确定性程序从文件里提取可靠结构。
2. 用证据记录每个判断。
3. 用 gold 做字段级评估。
4. 让 LLM 只在有证据时补充语义。
5. 用 retrieval 实验证明 schema 对找数据有帮助。
6. 用 freeze 和 regression tests 把当前成果保护起来。

现在项目已经从“探索能不能做”进入了“把结果固定、解释清楚、准备写作”的阶段。
