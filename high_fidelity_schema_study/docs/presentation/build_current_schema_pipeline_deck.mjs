import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const artifactToolUrl = pathToFileURL(require.resolve("@oai/artifact-tool")).href;
const { Presentation, PresentationFile } = await import(artifactToolUrl);

const OUT_DIR = path.resolve("docs/presentation");
const SCRATCH_DIR = path.resolve("tmp/slides/current-schema-pipeline");
const PPTX_PATH = path.join(OUT_DIR, "current_schema_extraction_pipeline.pptx");

const W = 1280;
const H = 720;

const COLORS = {
  bg: "#F6F7F4",
  ink: "#16202A",
  muted: "#5E6B75",
  line: "#CBD3D8",
  white: "#FFFFFF",
  blue: "#245B8F",
  blueFill: "#E2EEF8",
  teal: "#0F766E",
  tealFill: "#DDF1EC",
  green: "#256C43",
  greenFill: "#E1EFDF",
  amber: "#A56315",
  amberFill: "#F7E7C8",
  red: "#B42318",
  redFill: "#FADFDA",
  purple: "#5D4B8C",
  purpleFill: "#ECE8F5",
  grayFill: "#EEF1F2",
};

const FONT = "Microsoft YaHei";

function rect(slide, x, y, w, h, fill = COLORS.white, line = COLORS.line, radius = false) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { fill: line, width: line === "#FFFFFF00" ? 0 : 1 },
    adjustmentList: radius ? [{ name: "adj", formula: "val 9000" }] : undefined,
  });
}

function text(slide, value, x, y, w, h, opts = {}) {
  const box = rect(slide, x, y, w, h, opts.fill ?? "#FFFFFF00", "#FFFFFF00");
  box.text = value;
  box.text.typeface = opts.typeface ?? FONT;
  box.text.fontSize = opts.size ?? 18;
  box.text.color = opts.color ?? COLORS.ink;
  box.text.bold = opts.bold ?? false;
  box.text.alignment = opts.align ?? "left";
  box.text.verticalAlignment = opts.valign ?? "top";
  box.text.insets = opts.insets ?? { left: 0, right: 0, top: 0, bottom: 0 };
  box.text.autoFit = opts.autoFit ?? "shrinkText";
  return box;
}

function background(slide) {
  slide.background.fill = COLORS.bg;
  rect(slide, 0, 0, W, H, COLORS.bg, COLORS.bg);
}

function title(slide, heading, subheading, index) {
  text(slide, heading, 58, 42, 900, 52, { size: 30, bold: true });
  if (subheading) {
    text(slide, subheading, 60, 94, 1000, 34, { size: 15, color: COLORS.muted });
  }
  rect(slide, 58, 136, 1116, 2, COLORS.line, COLORS.line);
  text(slide, `当前模式提取管道 | ${index}/16`, 58, 682, 380, 20, {
    size: 11,
    color: COLORS.muted,
  });
}

function card(slide, x, y, w, h, heading, body, color = COLORS.blue, fill = COLORS.white) {
  rect(slide, x, y, w, h, fill, color, true);
  text(slide, heading, x + 18, y + 14, w - 36, 26, { size: 17, bold: true, color });
  text(slide, body, x + 18, y + 48, w - 36, h - 62, { size: 14.2, color: COLORS.ink });
}

function pill(slide, value, x, y, w, color, fill) {
  const p = rect(slide, x, y, w, 32, fill, color, true);
  p.text = value;
  p.text.typeface = FONT;
  p.text.fontSize = 13;
  p.text.bold = true;
  p.text.color = color;
  p.text.alignment = "center";
  p.text.verticalAlignment = "middle";
  p.text.insets = { left: 8, right: 8, top: 2, bottom: 2 };
  p.text.autoFit = "shrinkText";
}

function arrow(slide, x, y, w, h, value, color, fill) {
  const a = slide.shapes.add({
    geometry: "rightArrow",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { fill: color, width: 1 },
  });
  a.text = value;
  a.text.typeface = FONT;
  a.text.fontSize = 13.2;
  a.text.bold = true;
  a.text.color = color;
  a.text.alignment = "center";
  a.text.verticalAlignment = "middle";
  a.text.insets = { left: 14, right: 24, top: 3, bottom: 3 };
  a.text.autoFit = "shrinkText";
}

function note(slide, value, x, y, w, h, color = COLORS.teal) {
  rect(slide, x, y, w, h, COLORS.white, color, true);
  rect(slide, x, y, 8, h, color, color);
  text(slide, value, x + 22, y + 14, w - 38, h - 22, {
    size: 16,
    color: COLORS.ink,
    bold: true,
  });
}

function notes(slide, value) {
  if (slide.speakerNotes?.setText) {
    slide.speakerNotes.setText(value);
  }
}

async function buildDeck() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  await fs.mkdir(SCRATCH_DIR, { recursive: true });

  const deck = Presentation.create({ slideSize: { width: W, height: H } });

  {
    const slide = deck.slides.add();
    background(slide);
    text(slide, "从原始数据到可信模式输出", 70, 78, 910, 72, {
      size: 40,
      bold: true,
    });
    text(slide, "基于代码走读的当前仓库数据处理管道", 74, 154, 760, 34, {
      size: 20,
      color: COLORS.muted,
    });
    note(
      slide,
      "规范性立场：确定性优先提取、基于证据的主张、显式的未知/冲突/弃权状态。",
      78,
      252,
      680,
      92,
      COLORS.teal,
    );
    card(slide, 820, 84, 330, 112, "主入口 API", "extractors/registry.py::extract_path(ExtractionRequest)", COLORS.blue, COLORS.blueFill);
    card(slide, 820, 224, 330, 112, "输出格式", "ExtractionOutcome.to_dict() 与 unified_schema.py::build_unified_schema_envelope()", COLORS.green, COLORS.greenFill);
    card(slide, 820, 364, 330, 112, "可选语义层", "semantic_annotate.py 与 merge_semantic_annotations.py；下游处理，受证据约束", COLORS.amber, COLORS.amberFill);
    pill(slide, "拒绝 LLM 盲猜模式", 78, 396, 242, COLORS.red, COLORS.redFill);
    pill(slide, "仅限已注册的提取器", 338, 396, 218, COLORS.blue, COLORS.blueFill);
    pill(slide, "属性可追溯绑定", 574, 396, 168, COLORS.teal, COLORS.tealFill);
    text(slide, "已走读代码：CLI、注册表、提取器、数据类、验证器、语义标注、合并策略、溯源生成器、GUI 路径、测试及文档。", 80, 604, 1040, 36, {
      size: 14,
      color: COLORS.muted,
    });
    notes(slide, "开场强调：这不是凭空设计的架构。本 PPT 完全基于代码库的真实实现：cli.py、extractors/registry.py、各个具体的 extractor 模块、semantic_layer.py、unified_schema.py、provenance 测试文件以及相关文档。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "模式提取解决的问题", "在不凭空捏造字段的前提下，将异构的科学数据文件转化为可审计的结构。", 2);
    card(slide, 78, 190, 342, 210, "输入现状", "CSV 表格、HDF5 层级、NetCDF/CF 变量、Zarr 目录存储、Parquet 页脚、JSON/XML 结构以及不透明文件以不同的方式暴露模式信息。", COLORS.blue, COLORS.blueFill);
    card(slide, 470, 190, 342, 210, "期望输出", "一个包含字段、路径、dtype、shape、单位、逻辑角色、时间轴特征、主张状态、证据链、issue 和溯源信息的结构化 Schema。", COLORS.teal, COLORS.tealFill);
    card(slide, 862, 190, 342, 210, "可信度要求", "相比于幻觉出的字段或对微弱证据的默认采纳，代码更倾向于输出 unknown（未知）、conflicted（冲突）、partial（部分成功）、failed（失败）或 abstained（弃权）状态。", COLORS.green, COLORS.greenFill);
    note(slide, "README.md 明确指出核心任务：基于文件结构、显式元数据、确定性验证器和留存的证据，构建可获得的最强 Schema 支撑。", 112, 468, 1010, 78, COLORS.teal);
    notes(slide, "仓库将模式提取定位为后续检索或智能体使用的受控基底。其目标不是进行宽泛的自主解读，而是提供一个高保真、可辩护的 Schema 层。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "真实入口点与输出契约", "当前代码既保留了针对特定格式的传统命令，也提供了基于注册表的通用路径。", 3);
    card(slide, 78, 178, 360, 160, "命令行接口 (CLI)", "cli.py::main()\n\n子命令：extract、extract-csv、extract-hdf5、evaluate、agent-export。\n\n通用 extract 支持 --output-shape legacy|envelope|both。", COLORS.blue, COLORS.white);
    card(slide, 460, 178, 360, 160, "编程式 API", "extractors/registry.py::extract_path(request)\n\n输入：ExtractionRequest(path, format_hint, sample_limit, resource_kind)。\n\n输出：ExtractionOutcome(status, format_decision, extractor, schema, issues)。", COLORS.teal, COLORS.white);
    card(slide, 842, 178, 360, 160, "GUI/API 上传", "gui_demo/server.py::extract_uploaded_schema()\n\n通过 extract_path 进行路由，保留传统 Schema，并增加 extraction_outcome 和 unified_schema_envelope。", COLORS.green, COLORS.white);
    card(slide, 78, 398, 360, 130, "传统 Schema", "models.py::DatasetSchema 和 FieldSchema，持有物理/逻辑/语义字段以及 EvidenceRecord 列表。", COLORS.purple, COLORS.purpleFill);
    card(slide, 460, 398, 360, 130, "统一信封", "unified_schema.py::build_unified_schema_envelope()，归一化主张、证据、冲突、弃权、溯源及评估元数据。", COLORS.amber, COLORS.amberFill);
    card(slide, 842, 398, 360, 130, "智能体导出", "agent_exports.py::export_agent_bundle() 生成只读包，并将 canonical_mutation_allowed 设为 false。", COLORS.red, COLORS.redFill);
    notes(slide, "本页罗列了真实的入口函数。对于技术受众，重点在于 extract_path 是通用的路由路径，而旧的 CSV/HDF5 命令主要是为了向下兼容。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "输入数据：数据源、格式与核心假设", "系统所支持的输入格式显式声明在 EXTRACTOR_CAPABILITIES 中。", 4);
    const rows = [
      ["CSV/TSV", "file", "表头 + 样本行；sample_limit 默认值为 200"],
      ["HDF5", "file", "通过 h5py 遍历 groups/datasets/attrs 属性"],
      ["NetCDF/CF", "file", "传统 magic 魔数或含有 NetCDF4 标记 of HDF5 格式 .nc 文件"],
      ["Zarr v2", "directory_store", "仅读取本地元数据配置；不读取分片 chunk 的数据载荷"],
      ["Parquet", "file", "通过 pyarrow 读取页脚和 Arrow schema；不读取数据行"],
      ["JSON/JSONL", "file", "限制路径树深度遍历或解析已声明的 JSON Schema"],
      ["XML/XSD", "file", "限制实例路径遍历或轻量级 XSD 声明解析"],
      ["原始/未知", "file or directory", "结构化弃权；仅记录文件层级的证据"],
    ];
    let y = 178;
    for (const [fmt, kind, assumption] of rows) {
      rect(slide, 78, y, 1124, 46, y % 92 === 0 ? COLORS.grayFill : COLORS.white, COLORS.line);
      text(slide, fmt, 96, y + 12, 150, 22, { size: 15, bold: true, color: COLORS.blue });
      text(slide, kind, 270, y + 12, 160, 22, { size: 14, color: COLORS.ink });
      text(slide, assumption, 470, y + 12, 700, 22, { size: 14, color: COLORS.ink });
      y += 48;
    }
    note(slide, "对于不支持或未注册的格式，系统绝不强行推断 Schema；registry.py 将以弃权状态返回，并附带错误 issue 代码和空的 raw_binary 模式壳。", 124, 592, 1030, 62, COLORS.red);
    notes(slide, "这是来自 registry.py 的具体支持格式列表。需要阐明 Zarr 是目录存储（directory_store），而大部分其他格式是单文件。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "高层流水线概述", "核心路径由解析器（Parser）主导；语义标注处于下游，是可选的增强步骤。", 5);
    arrow(slide, 70, 214, 170, 70, "原始文件/存储输入", COLORS.red, COLORS.redFill);
    arrow(slide, 252, 214, 182, 70, "detect_format\n格式识别", COLORS.blue, COLORS.blueFill);
    arrow(slide, 446, 214, 184, 70, "能力注册表\n路由器", COLORS.teal, COLORS.tealFill);
    arrow(slide, 642, 214, 190, 70, "特定格式\n提取器", COLORS.green, COLORS.greenFill);
    arrow(slide, 844, 214, 182, 70, "验证器与\n归一化", COLORS.amber, COLORS.amberFill);
    arrow(slide, 1038, 214, 172, 70, "模式输出\n成果", COLORS.purple, COLORS.purpleFill);
    rect(slide, 165, 352, 950, 98, COLORS.white, COLORS.line, true);
    text(slide, "规范输出路径", 194, 368, 260, 24, { size: 18, bold: true, color: COLORS.teal });
    text(slide, "ExtractionOutcome -> DatasetSchema/FieldSchema/EvidenceRecord -> 统一模式信封 (主张/证据/溯源)", 194, 402, 850, 28, { size: 18, color: COLORS.ink });
    rect(slide, 310, 500, 660, 78, COLORS.amberFill, COLORS.amber, true);
    text(slide, "可选的下游语义增强", 330, 514, 600, 24, { size: 17, bold: true, color: COLORS.amber });
    text(slide, "Grounding 任务包 -> LLM JSON 成果 -> 兼容性校验 -> 合并策略 -> semantic_merged 构件", 330, 546, 600, 20, { size: 14, color: COLORS.ink });
    notes(slide, "用这张图说明整体流水线。要明确指出，LLM 并不处于规范提取的主干流程中，它只是在确定性成果之上的可选辅助增强。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "摄入、识别与信任边界", "格式决策收集多维度信号，且在信号冲突时显式弃权。", 6);
    card(slide, 78, 178, 350, 180, "输入验证", "extract_path() 检查路径是否存在，并校验资源类别（auto、file 或 directory_store）。路径非法或类型不匹配直接返回失败。", COLORS.blue, COLORS.blueFill);
    card(slide, 465, 178, 350, 180, "信号收集", "detect_format() 收集文件魔数（magic bytes）、目录元数据标识、显式 Hint、后缀名以及分隔符嗅探探针。", COLORS.teal, COLORS.tealFill);
    card(slide, 852, 178, 350, 180, "匹配决策", "优先级排序：强魔数/目录标识 > Hint > 后缀名 > 文本探测。含 NetCDF4 标记的 HDF5 文件会自动识别为 netcdf。", COLORS.green, COLORS.greenFill);
    rect(slide, 118, 438, 1040, 92, COLORS.white, COLORS.red, true);
    text(slide, "信任边界", 146, 456, 190, 24, { size: 18, bold: true, color: COLORS.red });
    text(slide, "若强信号之间发生冲突，系统将不选择任何解析器。_abstention_issue() 会抛出诸如 unknown_conflicting_format_signals（冲突信号）、unknown_no_signature（无特征）或 unknown_no_spec_backed_extractor（无支持提取器）等 issue 代码。", 146, 492, 970, 28, { size: 16, color: COLORS.ink });
    notes(slide, "结合 tests/test_extractor_registry.py 进行讲解：例如 HDF5 魔数与 CSV Hint 冲突时会选择弃权；未知二进制文件返回 raw_binary，并将字段主张策略设为 abstain。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "提取器装载与解析", "各个已注册的提取器分别产出包含源证据的 DatasetSchema。", 7);
    card(slide, 58, 176, 280, 134, "CSV", "csv_extractor.py::extract_csv_schema()\n解析表头、取样行、保守的类型推断、前导零保护、通过后缀提取单位。", COLORS.blue, COLORS.blueFill);
    card(slide, 358, 176, 280, 134, "HDF5", "hdf5_extractor.py::extract_hdf5_schema()\n遍历组与数据集，读取 dtype、shape、属性，记录可恢复的提取错误。", COLORS.teal, COLORS.tealFill);
    card(slide, 658, 176, 280, 134, "NetCDF/CF", "netcdf_extractor.py::extract_netcdf_schema()\n传统 scipy 路径或基于 HDF5 路径；解析维度、变量、属性以及 CF 坐标。", COLORS.green, COLORS.greenFill);
    card(slide, 958, 176, 280, 134, "Zarr", "zarr_extractor.py::extract_zarr_schema()\n仅限本地 v2 元数据；验证 .zarray 配置、维度、CF/Xarray 属性；遇 v3 弃权。", COLORS.amber, COLORS.amberFill);
    card(slide, 58, 362, 280, 134, "Parquet", "parquet_extractor.py::extract_parquet_schema()\n读取 Parquet 页脚和 Arrow 模式、行组、编码、统计指标；不读取具体行数据。", COLORS.purple, COLORS.purpleFill);
    card(slide, 358, 362, 280, 134, "JSON", "json_extractor.py::extract_json_schema()\n大小限制 16MB；支持 JSON Schema 属性遍历或限制深度的动态路径遍历、空值统计。", COLORS.blue, COLORS.white);
    card(slide, 658, 362, 280, 134, "XML/XSD", "xml_extractor.py::extract_xml_schema()\n大小限制 16MB；限制深度的 XML 实例路径遍历或轻量级 XSD 声明解析。", COLORS.teal, COLORS.white);
    card(slide, 958, 362, 280, 134, "Raw", "registry.py::build_raw_binary_schema()\n不作出任何字段主张；保留文件大小、二进制前缀或目录项数，采用弃权策略。", COLORS.red, COLORS.redFill);
    text(slide, "所有解析器最终收敛到 models.py 中定义的 DatasetSchema、FieldSchema 和 EvidenceRecord 数据结构。", 180, 578, 920, 28, { size: 18, bold: true, color: COLORS.ink, align: "center" });
    notes(slide, "本页作为一个密集的格式目录。听众不需要每个解析器的代码细节，但要明确函数的命名 and 提取的边界。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "数据预处理与标准化", "流水线对解析器的输出进行丰富，但不抹除不确定性。", 8);
    card(slide, 78, 178, 344, 220, "时间语义", "temporal_semantics.py::analyze_temporal_semantics()\n\n根据时间类型、强特征名称、语义/逻辑线索对候选者打分。只在置信度高时做出选择；平局会抛出 ambiguous_time_axis_candidates。", COLORS.blue, COLORS.blueFill);
    card(slide, 468, 178, 344, 220, "单位归一化", "unit_normalization.py::normalize_unit_claim()\n\n将已知单位映射到标准名称与 UCUM 编码；记录 evidence_basis 证据链（如显式元数据、名称模式或无证据支撑）。", COLORS.teal, COLORS.tealFill);
    card(slide, 858, 178, 344, 220, "数据剖析属性", "deterministic_profile.py::attach_dataset_profile()\n\n分析空值率和标识符质量。跨文件关系作为确定性候选关联保留，而不强行断言 JOIN。", COLORS.green, COLORS.greenFill);
    note(slide, "标准化阶段会赋予主张状态和原因码，例如 supported（支持）、derived（派生）、unknown（未知）、conflicted（冲突）、sampling_insufficient（采样不足）以及保守回退到 string。", 126, 480, 1028, 78, COLORS.amber);
    notes(slide, "说明这是一种“受控的富化”：代码计算时间网格、单位映射、缺失率和标识符质量，但在证据薄弱的地方诚实地记录不确定性。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "提取核心：Schema 候选如何产生", "具体数据模型分层设计，但均存储在显式的数据类中。", 9);
    rect(slide, 84, 184, 322, 318, COLORS.redFill, COLORS.red, true);
    text(slide, "原始/不受信的输入", 112, 206, 260, 24, { size: 18, bold: true, color: COLORS.red });
    text(slide, "字节流、文本行、XML/JSON 树、HDF5/NetCDF 容器、Parquet 页脚、Zarr 元数据目录。\n\n本身不足以推断语义。", 112, 248, 250, 138, { size: 15 });
    rect(slide, 474, 184, 322, 318, COLORS.blueFill, COLORS.blue, true);
    text(slide, "中间表示 (IR)", 502, 206, 260, 24, { size: 18, bold: true, color: COLORS.blue });
    text(slide, "models.py::FieldSchema\nfield_name, field_path, physical_type, shape, nullable, examples, source_evidence, confidence, uncertainty_reason。\n\nmodels.py::DatasetSchema 归类字段与元数据。", 502, 248, 250, 168, { size: 15 });
    rect(slide, 864, 184, 322, 318, COLORS.greenFill, COLORS.green, true);
    text(slide, "受控 Schema", 892, 206, 260, 24, { size: 18, bold: true, color: COLORS.green });
    text(slide, "逻辑角色、语义线索、单位、时间轴分析、特定格式分析、主张状态、证据记录。\n\n仅在解析器或验证器支持时提升。", 892, 248, 250, 154, { size: 15 });
    arrow(slide, 406, 306, 62, 56, "", COLORS.blue, COLORS.blueFill);
    arrow(slide, 796, 306, 62, 56, "", COLORS.green, COLORS.greenFill);
    note(slide, "最终的可信输出要么是传统的 ExtractionOutcome，要么是包含主张/证据/溯源的统一版本化信封。", 194, 568, 900, 62, COLORS.teal);
    notes(slide, "这契合了对三层结构的区分：原始输入、中间结构化表示、受控 Schema 以及验证后的最终输出。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "提示词、模型与规则逻辑", "规范提取基于确定性的规则与解析器；LLM 仅用于下游语义增强。", 10);
    card(slide, 78, 180, 346, 236, "规范提取路径", "extract_path() 不使用任何 prompt。已注册的提取器采用确定性解析、受限取样、元数据审查、显式别名和验证器。", COLORS.green, COLORS.greenFill);
    card(slide, 468, 180, 346, 236, "提示词构建", "build_semantic_grounding.py 生成任务包；semantic_layer.py::build_prompt_payload() 整合 SYSTEM_RULES、确定性 Schema、上下文片段和目标输出格式。", COLORS.amber, COLORS.amberFill);
    card(slide, 858, 180, 346, 236, "LLM 执行器", "semantic_annotate.py 向聊天补全接口发送严格 of JSON 任务。它只能对指定的字段进行标注，且必须引用已有的证据 ID。", COLORS.blue, COLORS.blueFill);
    note(slide, "安全控制说明：本系统并不包含密码学签名、形式化证明系统或完整的 XML/XSD/JSON 校验引擎。其安全控制主要依赖于确定性路由、受限解析器、验证器、测试套件、明确的 issue 状态以及证据/溯源链条。", 112, 492, 1058, 88, COLORS.red);
    notes(slide, "务必准确：不要让听众误以为 LLM 是规范提取流水线的一部分。它是一个在确定性结果之上的、被验证和合并规则所守护的下游富化路径。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "受控词表与 Schema 约束", "代码对输出表达以及不确定性的记录进行了严格限制。", 11);
    card(slide, 78, 176, 340, 178, "允许的逻辑类型", "semantic_layer.py::ALLOWED_LOGICAL_TYPES:\nidentifier, time_axis, measurement, coordinate, label, attribute, relationship, unknown。", COLORS.blue, COLORS.blueFill);
    card(slide, 470, 176, 340, 178, "主张状态", "unified_schema.py::CLAIM_STATES:\nobserved, declared, derived, supported, conflicted, unknown, unsupported, abstained。", COLORS.teal, COLORS.tealFill);
    card(slide, 862, 176, 340, 178, "提取器能力", "registry.py::EXTRACTOR_CAPABILITIES 声明了 extractor_id、版本、支持格式、后缀名、操作、确定性级别、证据类型和资源类别。", COLORS.green, COLORS.greenFill);
    card(slide, 78, 410, 340, 138, "单位字典", "UNIT_ALIASES 将支持的单位名投影到 canonical_unit 和类似 UCUM 的编码；未匹配的单位保留原样，防止误导性的映射。", COLORS.amber, COLORS.amberFill);
    card(slide, 470, 410, 340, 138, "证据等级", "docs/target_schema.md 定义：explicit_metadata > structural > statistical > llm_inference。低等级证据不得随意覆盖高等级证据。", COLORS.purple, COLORS.purpleFill);
    card(slide, 862, 410, 340, 138, "合并策略", "merge_annotation_result() 拒绝不支持的标注，并在信封中忠实记录逻辑/语义/单位冲突，不予隐瞒。", COLORS.red, COLORS.redFill);
    notes(slide, "本页汇总了主要的受控面：数据类字段、允许的逻辑类型、主张状态词汇、显式声明的提取器能力、单位别名表以及合并策略。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "验证与一致性闭环", "验证工作贯穿于摄入、提取、标准化、信封投影以及回归测试中。", 12);
    arrow(slide, 116, 190, 190, 66, "输入验证\nInput validation", COLORS.blue, COLORS.blueFill);
    arrow(slide, 328, 190, 190, 66, "提取器验证\nExtractor validation", COLORS.teal, COLORS.tealFill);
    arrow(slide, 540, 190, 190, 66, "归一化主张\nNormalizer claims", COLORS.green, COLORS.greenFill);
    arrow(slide, 752, 190, 190, 66, "信封审计\nEnvelope audit", COLORS.purple, COLORS.purpleFill);
    arrow(slide, 964, 190, 190, 66, "测试与报告\nTests + reports", COLORS.amber, COLORS.amberFill);
    rect(slide, 178, 330, 920, 142, COLORS.white, COLORS.line, true);
    text(slide, "闭环表现", 210, 350, 180, 24, { size: 18, bold: true, color: COLORS.teal });
    text(slide, "任何阶段都可以返回 success、partial、abstained 或 failed。Issue 码会被向后传递，而不是合并为一个模糊的得分。", 210, 386, 860, 28, { size: 17 });
    text(slide, "例如：dependency_unavailable、parser_error、partial_extraction、sampling_insufficient、declared_observed_type_conflict、unsupported_zarr_version。", 210, 430, 860, 28, { size: 15, color: COLORS.muted });
    card(slide, 126, 538, 310, 78, "注册表测试", "tests/test_extractor_registry.py", COLORS.blue, COLORS.white);
    card(slide, 486, 538, 310, 78, "信封测试", "tests/test_unified_schema.py", COLORS.purple, COLORS.white);
    card(slide, 846, 538, 310, 78, "语义与 PROV 测试", "test_semantic_annotate_payload.py; test_provenance_manifest.py", COLORS.green, COLORS.white);
    notes(slide, "用此图讲解验证闭环。强调错误模式是系统的一等公民状态和 issue 码，而不是对用户隐藏的异常。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "溯源、可追踪性与可审计性", "每一个获得支持的主张都必须指向明确的客观证据。", 13);
    card(slide, 78, 178, 344, 238, "字段级证据", "每一个 FieldSchema 均带有 source_evidence: EvidenceRecord(tier, evidence_type, source, detail, confidence)。\n\n例如：csv_header、sample_rows、hdf5_attribute、netcdf_variable、zarr_array_metadata。", COLORS.teal, COLORS.tealFill);
    card(slide, 468, 178, 344, 238, "统一主张图谱", "build_unified_schema_envelope() 对证据库去重（赋予 e0001 等 ID），生成包含 evidence_refs 的 c0001 等主张。冲突和弃权会独立投影。", COLORS.blue, COLORS.blueFill);
    card(slide, 858, 178, 344, 238, "仿 PROV 清单", "build_provenance_manifest.py 在源文件、派生 Schema、字段、证据、语义标注、合并记录、报告、智能体、活动和关联关系上建立起轻量级的 prov_v1 溯源关系图。", COLORS.green, COLORS.greenFill);
    note(slide, "信任源自可追踪性以及严谨的主张策略，而非单一的置信度分值。置信度字段存在，但 issue 状态和证据引用是更强的控制。", 136, 508, 1008, 74, COLORS.amber);
    notes(slide, "提到 tests/test_unified_schema.py 验证了所有支持的主张都包含有效的 evidence_refs，且对应的证据 ID 均能被成功解析。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "最终模式输出格式", "最终产出可作为传统 JSON、统一信封 JSON，或两者兼具。", 14);
    card(slide, 70, 176, 360, 266, "传统 ExtractionOutcome", "status\nformat_decision\nextractor\nschema\nissues\n\nschema 包含 DatasetSchema 字段、分组、元数据和备注。", COLORS.blue, COLORS.blueFill);
    card(slide, 460, 176, 360, 266, "统一信封 v1.0.0 (Unified Envelope)", "identity\nformat_detection\nextractor_capability\noutcome\nphysical_structure\nlogical_roles\nsemantic_hints\nunits\ntemporal_semantics\nclaims/evidence/provenance", COLORS.teal, COLORS.tealFill);
    card(slide, 850, 176, 360, 266, "智能体包 (Agent Bundle)", "agent_export_version\npolicy\nschema_summary\nclaim_records\nevidence_records\nprovenance_graph\nretrieval_context\nrequestable_actions", COLORS.green, COLORS.greenFill);
    text(slide, "CLI 运行实例", 106, 506, 160, 24, { size: 17, bold: true, color: COLORS.ink });
    rect(slide, 106, 538, 1028, 58, COLORS.ink, COLORS.ink, true);
    text(slide, "python -m high_fidelity_schema_study.cli extract --input path/to/file --output-shape both", 130, 555, 980, 22, { size: 18, color: COLORS.white });
    notes(slide, "传统 Schema 仍然作为权威且不受影响。统一信封是增量合入的，测试套件对此进行了严格校验。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "错误处理、失败模式与局限性", "代码诚实地暴露了系统的限制，而不是假装问题已经解决。", 15);
    card(slide, 58, 172, 280, 170, "弃权情形", "未知二进制文件、强信号冲突、未注册格式、Zarr v3、缺失 Zarr 元数据、JSON/XML 超过大小限制都会导致系统主动弃权。", COLORS.red, COLORS.redFill);
    card(slide, 358, 172, 280, 170, "部分成功/失败", "可恢复的解析错误转为 partial。致命错误或缺失环境依赖返回 structured failed 结果。", COLORS.amber, COLORS.amberFill);
    card(slide, 658, 172, 280, 170, "样本限制", "CSV/JSON/XML 剖析基于有限的样本（sample_limit）；源自样本的特征不应作为普适 of 物理证明。", COLORS.blue, COLORS.blueFill);
    card(slide, 958, 172, 280, 170, "局限于元数据", "不读取 Parquet 实体行和 Zarr 数据块；页脚统计及配置元数据不对实际的 Payload 数据值做交叉校验。", COLORS.teal, COLORS.tealFill);
    card(slide, 58, 398, 280, 146, "格式解析范围", "NetCDF4 路径较保守；XML/XSD 较轻量；JSON Schema 解析不等同于完整的校验引擎。", COLORS.purple, COLORS.purpleFill);
    card(slide, 358, 398, 280, 146, "LLM 增强范围", "LLM 标注处于下游，可能失败、冲突或返回未知。它绝对无法自行创造任何物理字段。", COLORS.green, COLORS.greenFill);
    card(slide, 658, 398, 280, 146, "测试集局限", "挑战包反映的是显式设计的特例表现，并不代表在整个现实生态中具有无漏洞的强壮性。", COLORS.amber, COLORS.white);
    card(slide, 958, 398, 280, 146, "缺失的控制安全", "缺少密码学签名、没有形式化证明校验器、不支持自动加载远程实体或模式定义、不提供全自动的兼容性担保。", COLORS.red, COLORS.white);
    notes(slide, "这是局限性说明页。诚实地指出我们缺失的控制机制；这是本项目的信任模型的核心部分。");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "推荐的后续改进", "在不削弱确定性优先这一契约的前提下，扩展提取的覆盖面和可信度。", 16);
    card(slide, 78, 176, 344, 178, "宽泛兼容性", "扩展针对 Parquet、JSON、XML、NetCDF/CF 和 Zarr 的多源校验能力，每个测试语料库与冻结的基准测试主张保持物理隔离。", COLORS.blue, COLORS.blueFill);
    card(slide, 468, 176, 344, 178, "强模式验证器", "在显式能力标识后加入更完整的 JSON Schema 与 XML/XSD 验证模式；严格分离观察主张与声明主张。", COLORS.teal, COLORS.tealFill);
    card(slide, 858, 176, 344, 178, "物理数据校验", "引入可选的 Parquet 页脚统计与 Zarr 数据块属性的采样读取校验，并提供显式的开销控制。", COLORS.green, COLORS.greenFill);
    card(slide, 78, 410, 344, 138, "溯源安全加固", "为生成的模式和信封加入构件哈希、执行清单、依赖版本锁定以及可选的电子签名。", COLORS.purple, COLORS.purpleFill);
    card(slide, 468, 410, 344, 138, "LLM 治理机制", "默认保持 LLM 增强为非权威属性；优化证据 ID 关联、提升 prompt 回归测试并建设冲突监控面板。", COLORS.amber, COLORS.amberFill);
    card(slide, 858, 410, 344, 138, "用户端质检", "在 CLI 和 GUI 输出中更清晰地展示 issue 代码、样本限制、弃权原因以及深入的证据链下钻。", COLORS.red, COLORS.redFill);
    note(slide, "绝不放宽核心原则：没有足够证据支持的推断应始终保持 unknown、conflicted、partial、failed 或 abstained 状态。", 180, 602, 920, 50, COLORS.teal);
    notes(slide, "结尾再次强调研究态度：当前管道已经是受控且可审计的，后续工作应当专注于提升覆盖面和验证精度，而不是将其变成一个“端到端 LLM 盲猜器”。");
  }

  for (let i = 0; i < deck.slides.count; i += 1) {
    const png = await deck.export({
      slide: deck.slides.getItem(i),
      format: "png",
      scale: 1,
    });
    await fs.writeFile(path.join(SCRATCH_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`), Buffer.from(await png.arrayBuffer()));
  }

  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(PPTX_PATH);
  console.log(JSON.stringify({ pptx: PPTX_PATH, slides: deck.slides.count, scratch: SCRATCH_DIR }, null, 2));
}

await buildDeck();
