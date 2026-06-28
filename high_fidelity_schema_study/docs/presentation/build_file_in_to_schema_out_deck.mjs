import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const artifactToolUrl = pathToFileURL(require.resolve("@oai/artifact-tool")).href;
const { Presentation, PresentationFile } = await import(artifactToolUrl);

const OUT_DIR = path.resolve("high_fidelity_schema_study/docs/presentation");
const SCRATCH_DIR = path.resolve("high_fidelity_schema_study/tmp/slides/file-in-to-schema-out");
const PPTX_PATH = path.join(OUT_DIR, "file_in_to_schema_out_process.pptx");

const W = 1280;
const H = 720;

const COLORS = {
  paper: "#F7F3EA",
  ink: "#18212B",
  muted: "#64717C",
  teal: "#0F766E",
  tealLight: "#D7F0EA",
  amber: "#B7791F",
  amberLight: "#FCE7C4",
  red: "#B42318",
  redLight: "#FDE1DE",
  green: "#256C43",
  greenLight: "#DDEEDC",
  blue: "#245B8F",
  blueLight: "#DCEAF7",
  line: "#D7D0C4",
  white: "#FFFFFF",
};

const FONT = {
  title: "Microsoft YaHei",
  body: "Microsoft YaHei",
};

function addText(slide, text, x, y, w, h, options = {}) {
  const shape = slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: w, height: h },
    fill: options.fill ?? "#FFFFFF00",
    line: { fill: "#FFFFFF00", width: 0 },
  });
  shape.text = text;
  shape.text.typeface = options.typeface ?? FONT.body;
  shape.text.fontSize = options.size ?? 28;
  shape.text.color = options.color ?? COLORS.ink;
  shape.text.bold = options.bold ?? false;
  shape.text.alignment = options.align ?? "left";
  shape.text.verticalAlignment = options.valign ?? "top";
  shape.text.insets = options.insets ?? { left: 0, right: 0, top: 0, bottom: 0 };
  shape.text.autoFit = options.autoFit ?? "shrinkText";
  return shape;
}

function addTitle(slide, title, subtitle) {
  addText(slide, title, 64, 44, 900, 62, {
    size: 34,
    bold: true,
    color: COLORS.ink,
    typeface: FONT.title,
  });
  if (subtitle) {
    addText(slide, subtitle, 66, 104, 900, 36, {
      size: 17,
      color: COLORS.muted,
    });
  }
  slide.shapes.add({
    geometry: "rect",
    position: { left: 64, top: 146, width: 1120, height: 2 },
    fill: COLORS.line,
    line: { fill: COLORS.line, width: 0 },
  });
}

function addCard(slide, x, y, w, h, title, body, color = COLORS.teal, fill = COLORS.white) {
  const card = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { fill: COLORS.line, width: 1 },
    adjustmentList: [{ name: "adj", formula: "val 10000" }],
  });
  addText(slide, title, x + 22, y + 18, w - 44, 30, {
    size: 20,
    bold: true,
    color,
  });
  addText(slide, body, x + 22, y + 58, w - 44, h - 76, {
    size: 17,
    color: COLORS.ink,
  });
  return card;
}

function addPill(slide, text, x, y, w, color, fill) {
  const pill = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: 36 },
    fill,
    line: { fill: color, width: 1 },
    adjustmentList: [{ name: "adj", formula: "val 50000" }],
  });
  pill.text = text;
  pill.text.typeface = FONT.body;
  pill.text.fontSize = 15;
  pill.text.bold = true;
  pill.text.color = color;
  pill.text.alignment = "center";
  pill.text.verticalAlignment = "middle";
  pill.text.insets = { left: 10, right: 10, top: 3, bottom: 3 };
  pill.text.autoFit = "shrinkText";
  return pill;
}

function addMetricCard(slide, label, value, note, x, y, color, fill) {
  slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: 340, height: 142 },
    fill,
    line: { fill: color, width: 1.5 },
    adjustmentList: [{ name: "adj", formula: "val 9000" }],
  });
  addText(slide, label, x + 22, y + 18, 296, 28, {
    size: 17,
    color,
    bold: true,
  });
  addText(slide, value, x + 22, y + 50, 296, 48, {
    size: 38,
    color,
    bold: true,
  });
  addText(slide, note, x + 22, y + 104, 296, 24, {
    size: 14,
    color: COLORS.muted,
  });
}

function addFooter(slide, index) {
  addText(slide, `从文件输入到模式输出 (File In -> Schema Out) · ${index}/9`, 64, 678, 600, 24, {
    size: 12,
    color: COLORS.muted,
  });
}

function addBackground(slide) {
  slide.background.fill = COLORS.paper;
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 1280, height: 720 },
    fill: COLORS.paper,
    line: { fill: COLORS.paper, width: 0 },
  });
}

function addSimpleArrow(slide, x, y, w, label, color, fill) {
  const arrow = slide.shapes.add({
    geometry: "rightArrow",
    position: { left: x, top: y, width: w, height: 70 },
    fill,
    line: { fill: color, width: 1 },
  });
  arrow.text = label;
  arrow.text.typeface = FONT.body;
  arrow.text.fontSize = 16;
  arrow.text.bold = true;
  arrow.text.color = color;
  arrow.text.alignment = "center";
  arrow.text.verticalAlignment = "middle";
  arrow.text.insets = { left: 18, right: 28, top: 6, bottom: 6 };
  arrow.text.autoFit = "shrinkText";
}

async function buildDeck() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  await fs.mkdir(SCRATCH_DIR, { recursive: true });

  const presentation = Presentation.create({
    slideSize: { width: W, height: H },
  });

  // Slide 1: 封面
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addText(slide, "从文件输入到统一模式信封输出", 74, 86, 900, 86, {
      size: 42,
      bold: true,
      color: COLORS.ink,
      typeface: FONT.title,
    });
    addText(slide, "高保真 Schema 提取全生命周期流程详解与设计落地", 78, 170, 850, 40, {
      size: 22,
      color: COLORS.muted,
    });
    addText(slide, "先用程序证明结构与客观事实，再让 LLM 在证据约束下补充语义理解。", 80, 272, 660, 96, {
      size: 28,
      bold: true,
      color: COLORS.teal,
    });
    addCard(slide, 810, 94, 330, 118, "物理主导", "解析器读取绝对客观的结构与内秉元数据。", COLORS.blue, COLORS.blueLight);
    addCard(slide, 810, 244, 330, 142, "图谱投影", "主张与证据分离，全局去重并支持图谱化关联追溯。", COLORS.teal, COLORS.tealLight);
    addPill(slide, "Deterministic-first", 80, 430, 200, COLORS.blue, COLORS.blueLight);
    addPill(slide, "Evidence-constrained", 296, 430, 220, COLORS.teal, COLORS.tealLight);
    addPill(slide, "Unified Schema Envelope", 532, 430, 230, COLORS.amber, COLORS.amberLight);
    addFooter(slide, 1);
  }

  // Slide 2: 核心哲学
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "设计哲学：确定性优先 (Deterministic-First)", "克服传统的“端到端 LLM 盲猜”模式所带来的不可审计、幻觉和无法复现等致命缺陷。");
    addCard(slide, 78, 202, 330, 200, "程序主导物理提取", "用高度稳定的专属解析器读取物理结构，包括列名、dtype、shape和属性，确保底座绝对客观准确。", COLORS.blue, COLORS.blueLight);
    addCard(slide, 474, 202, 330, 200, "过程捕捉过程证据", "在提取中自动保留物理决策对应的文件片断或行号，建立不可篡改的 EvidenceRecord 池。", COLORS.teal, COLORS.tealLight);
    addCard(slide, 870, 202, 330, 200, "受限语义增强合并", "LLM 只能修改特定语义字段，所有修改必须有证据文本支撑，且必须通过系统兼容性校验校验。", COLORS.amber, COLORS.amberLight);
    addText(slide, "核心边界规则：任何高级的语义推断都不能覆盖底层明确的物理/结构证据。", 108, 468, 1060, 48, {
      size: 24,
      bold: true,
      color: COLORS.red,
      align: "center",
    });
    addFooter(slide, 2);
  }

  // Slide 3: 第一阶段 - 文件摄入与智能识别
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "第一阶段：文件摄入与类型检测 (File Intake)", "智能匹配解析器并提供多级降级防冲突机制。");
    addCard(slide, 70, 192, 260, 210, "1. 资源边界校验", "通过 _actual_resource_kind 判定是 file 还是 directory_store (如 Zarr)。若与指定预期不符，立即拦截报错。", COLORS.blue, COLORS.white);
    addCard(slide, 355, 192, 260, 210, "2. 多重信号探测", "● 魔数优先 (HDF5/Parquet/NetCDF)\n● 目录元数据探测 (Zarr)\n● 后缀解析\n● csv.Sniffer 文本分列探针", COLORS.teal, COLORS.white);
    addCard(slide, 640, 192, 260, 210, "3. 优先级决策与重写", "● Magic > Hint > Suffix > Text\n● 特殊重写：若 HDF5 包含 NetCDF4 特征且后缀为 .nc/.cdf，自动升级为 netcdf 信号。", COLORS.green, COLORS.white);
    addCard(slide, 925, 192, 280, 210, "4. 冲突判定与安全回退", "若 Magic 信号与用户 Hint 强冲突，系统将判定为 conflicted 并主动弃权，回退输出通用的 raw_binary 模式。", COLORS.red, COLORS.redLight);
    addText(slide, "通过此模块，系统实现了多模态原始文件与专属确定性提取器（Extractor）的精准、安全路由。", 120, 470, 1040, 60, {
      size: 20,
      color: COLORS.muted,
      align: "center",
    });
    addFooter(slide, 3);
  }

  // Slide 4: 第二阶段 - CSV & JSON 确定性提取
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "第二阶段：确定性结构提取 - CSV & JSON Extractor", "对半结构化与结构化文本实施“保守提取”与“路径遍历”策略。");
    addCard(slide, 78, 190, 520, 280, "CSV 提取器：保守类型推断与前导零保护", "● 读取表头，截取前 N 行（默认 200 行）作为样本。\n● int/float/datetime 必须在样本中获得 100% 成功解析。\n● 导入前导零检测 (_has_leading_zero)：如 '0123' 的纯数字字段强制推断为 string，避免邮编/电话丢失首字符。\n● 类型冲突时保守回退到 string，防止产生误导性物理主张。", COLORS.teal, COLORS.tealLight);
    addCard(slide, 678, 190, 520, 280, "JSON 提取器：单文档/多行模式与扁平树遍历", "● 限制读取大小（16MB）以获得内存级保护。\n● 声明模式：若含有 properties，递归遍历解析标准定义，生成 declared claims；若有 values 则校验兼容性。\n● 观察模式：对于动态文档，启动递归遍历 visit(val, path, index)，将嵌套路径展开为扁平结构（例如 $.a.b[].c）。\n● 统计多级路径的空值率，不对语义进行猜测。", COLORS.blue, COLORS.blueLight);
    addText(slide, "物理属性是数据集的基础指纹，确定性提取器只抓取客观可见的字段类型与形状。", 120, 510, 1040, 36, {
      size: 18,
      color: COLORS.muted,
      bold: true,
      align: "center",
    });
    addFooter(slide, 4);
  }

  // Slide 5: 第二阶段 - Zarr & NetCDF 确定性提取
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "第二阶段：确定性结构提取 - Zarr & 多维元数据", "多维科学数据的目录级只读元数据（Metadata-Only）高速提取。");
    addCard(slide, 78, 190, 520, 280, "Zarr 提取器：合并元数据检索与版本检测", "● 深度扫描存储目录，优先读取合并元数据文档 .zmetadata 提升 I/O 效率；若缺失则降级遍历 .zgroup/.zarray。\n● 检测到 zarr_format == 3（Zarr v3）时，由于只支持 v2，抛出结构化错误并直接以 abstained 状态弃权。\n● 仅解析元数据，不下载或读取任何分片 chunk 载荷，保持极其高效的零 I/O 损耗。", COLORS.teal, COLORS.tealLight);
    addCard(slide, 678, 190, 520, 280, "坐标与多维关系解析 (Xarray & CF 约定)", "● 维度计算：解析 _ARRAY_DIMENSIONS 获取高维数组大小。\n● 坐标系判定：基于 CF 约定，检测 axis(X/Y/Z/T)、units(degrees_north) 和 standard_name，识别为坐标系角色。\n● 物理类型直接由 dtype (如 float64) 投影，值域范围/空值等直接置为 unknown 记录元数据只读边界。", COLORS.blue, COLORS.blueLight);
    addText(slide, "对于科学数据集（NetCDF/HDF5/Zarr），利用 CF 约定能极大地加速数据空间组织维度的发现。", 120, 510, 1040, 36, {
      size: 18,
      color: COLORS.muted,
      bold: true,
      align: "center",
    });
    addFooter(slide, 5);
  }

  // Slide 6: 第三阶段 - 数据概要分析与标准化
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "第三阶段：数据剖析与时间/单位标准化", "通过计算方法论补充数据的外生语义，提供跨域标准化检索物料。");
    addCard(slide, 78, 190, 342, 260, "时间轴分析 (analyze_temporal_semantics)", "对所有 datetime 与 组合的 year-month-day 字段打分，最高分者设为数据集唯一 Time Axis，更新逻辑类型为 time_axis。若存在分差 <= 0.05 的双重候选，输出 Ambiguous Time Axis 警告。", COLORS.teal, COLORS.white);
    addCard(slide, 470, 190, 342, 260, "时间特性计算", "● 时区提取：检查 Naive/Aware 混合冲突。\n● 频率 (Frequency)：统计间隔 delta 众数（如 60s -> 1 minute）。\n● 规律性 (Regularity)：主频占比 >=95% 则标记为 regular。\n● 缺失区间：估计理论步长差得出漏检数。", COLORS.blue, COLORS.white);
    addCard(slide, 862, 190, 342, 260, "物理单位归一化 (normalize_unit)", "● 提取表头后缀或元数据中的单位（如 Celsius, mm）。\n● 通过 UNIT_ALIASES 字典投影出标准的 canonical_unit 与符合国际规范的 UCUM 编码。\n● 标记证据基础（hdf5_attr -> explicit_metadata）。", COLORS.green, COLORS.white);
    addText(slide, "此阶段在纯物理描述的基础上，建立起具备科学检索意义的“时间网格”与“归一化单位”。", 120, 500, 1040, 36, {
      size: 18,
      color: COLORS.muted,
      align: "center",
    });
    addFooter(slide, 6);
  }

  // Slide 7: 第四阶段 - 受约束的 LLM 语义增强层
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "第四阶段：语义增强与安全合并 (Semantic Layer)", "如何安全引入 LLM 对无结构 README 进行解读并合入确定性 Schema。");
    addCard(slide, 78, 190, 520, 280, "1. 受限任务包构建与系统规则约束", "● 将物理 Schema 与外部 README 片段（GroundingSnippet）一起打包成 Context。\n● 注入 SYSTEM_RULES：严禁编造物理字段，推断必须附带 README 原文作为 supporting_evidence，无把握必须填 unknown。\n● 模型只能提议 semantic_type, logical_type, unit 以及 文本描述 description。", COLORS.teal, COLORS.tealLight);
    addCard(slide, 678, 190, 520, 280, "2. 强校验与安全合并规则 (Validator & Merger)", "● 无证据拒绝：提议修改但 supporting_evidence 为空，触发 unsupported_annotation 冲突并抛弃。\n● 兼容性拦截：校验逻辑与语义分类兼容性（如 latitude 不允许设为 measurement）。\n● 确定性保护：若物理引擎已获取明确信息，直接冲突者一律予以拒绝，仅在完全兼容且 LLM 置信度 >= 0.85 时，允许精细化覆写。", COLORS.amber, COLORS.amberLight);
    addText(slide, "安全规则核心：宁可由于缺乏证据选择 unknown，也绝不无端猜测 (Prefer unknown over unsupported guessing)。", 120, 510, 1040, 36, {
      size: 18,
      color: COLORS.red,
      bold: true,
      align: "center",
    });
    addFooter(slide, 7);
  }

  // Slide 8: 第五阶段 - 统一信封投影
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "第五阶段：统一信封投影 - 证据与主张图谱", "将处理结果投影为全局唯一、主张与证据分离的 Schema Envelope。");
    addCard(slide, 78, 190, 520, 280, "全局去重证据库 (evidence)", "信封顶层包含全局 evidence 列表。每一个证据均分配有唯一的 ID（如 e0001, e0002），记录它的获取层级（tier: structural/statistical/explicit_metadata）、来源文件路径、详情细节以及记录时的置信度度量。", COLORS.blue, COLORS.blueLight);
    addCard(slide, 678, 190, 520, 280, "模式主张列表 (claims)", "信封将物理、逻辑、语义和单位都抽象为原子主张。每个主张包含 claim_id，规定它的主体（field_path）、属性类别、推断值，并最关键地通过 evidence_refs 指向对应的 evidence_id（可复数），完成完整证据图谱绑定。", COLORS.teal, COLORS.tealLight);
    addText(slide, "投影模型使得最终输出不再是一个无解释的属性列表，而是一个“每一项推断均可向下溯源至具体事实”的证据图谱。", 120, 500, 1040, 60, {
      size: 20,
      color: COLORS.ink,
      bold: true,
      align: "center",
    });
    addFooter(slide, 8);
  }

  // Slide 9: 全流程实例串联 (Walkthrough)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "全流程实例串联：Buoy Sensor Data Ingestion", "展示一份浮标 CSV 数据是如何变成规范化模式信封的。");
    const steps = [
      ["1", "探测与路由", "Buoy CSV 文件被送入，魔数无，后缀匹配，Sniffer 解析判定为 csv 格式。"],
      ["2", "确定性物理推断", "ts_utc 为 datetime，water_temp_c 为 float，buoy_id (带 0 开头) 强制判定为 string 防止丢失 ID 精度。"],
      ["3", "概要特征分析", "ts_utc 设为 time_axis；判定间隔为 60s/regular；表头 water_temp_c 转换并归一化为 Celsius。"],
      ["4", "LLM 语义注入与合并", "根据 README 提示，LLM 提议将 flag 字段的语义设为 quality_flag。提供证据，检查兼容性后安全合入。"],
      ["5", "模式信封统一生成", "输出统一 Envelope。生成 claims，关联对应的 e0001 (表头名) 和 e0002 (README 引用)。"],
    ];
    let y = 178;
    for (const [num, title, body] of steps) {
      slide.shapes.add({
        geometry: "ellipse",
        position: { left: 100, top: y + 5, width: 44, height: 44 },
        fill: COLORS.teal,
        line: { fill: COLORS.teal, width: 0 },
      }).text = num;
      const circle = slide.shapes.items[slide.shapes.items.length - 1];
      circle.text.typeface = FONT.body;
      circle.text.fontSize = 18;
      circle.text.bold = true;
      circle.text.color = COLORS.white;
      circle.text.alignment = "center";
      circle.text.verticalAlignment = "middle";
      addText(slide, title, 172, y, 420, 26, {
        size: 20,
        bold: true,
        color: COLORS.ink,
      });
      addText(slide, body, 172, y + 28, 920, 24, {
        size: 15,
        color: COLORS.muted,
      });
      y += 92;
    }
    addText(slide, "结论：通过确定性打底与受约束的 LLM 语义充实，实现了安全、可溯源的高保真元数据检索基础。", 166, 618, 940, 36, {
      size: 22,
      bold: true,
      color: COLORS.teal,
      align: "center",
    });
    addFooter(slide, 9);
  }

  for (const slide of presentation.slides.items) {
    if (slide.speakerNotes?.setText) {
      slide.speakerNotes.setText("Explain the high-fidelity schema extraction pipeline stages: Intake, Extractor, Profiler, Semantics, and Envelope.");
    }
  }

  for (let i = 0; i < presentation.slides.count; i += 1) {
    const png = await presentation.export({
      slide: presentation.slides.getItem(i),
      format: "png",
      scale: 1,
    });
    const buffer = Buffer.from(await png.arrayBuffer());
    await fs.writeFile(path.join(SCRATCH_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`), buffer);
  }

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(PPTX_PATH);
  console.log(JSON.stringify({ pptx: PPTX_PATH, slides: presentation.slides.count }, null, 2));
}

await buildDeck();
