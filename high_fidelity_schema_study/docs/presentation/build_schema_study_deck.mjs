import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT_DIR = path.resolve("high_fidelity_schema_study/docs/presentation");
const SCRATCH_DIR = path.resolve("high_fidelity_schema_study/tmp/slides/schema-study-high-school");
const PPTX_PATH = path.join(OUT_DIR, "schema_extraction_study_high_school_CN.pptx");

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
  addText(slide, `High-Fidelity Schema Extraction Study · ${index}/9`, 64, 678, 500, 24, {
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

  // Slide 1
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addText(slide, "让 AI 不再乱猜数据字段", 74, 86, 780, 86, {
      size: 42,
      bold: true,
      color: COLORS.ink,
      typeface: FONT.title,
    });
    addText(slide, "一个高中生也能听懂的 schema extraction study 介绍", 78, 170, 760, 40, {
      size: 22,
      color: COLORS.muted,
    });
    addText(slide, "核心想法：先用程序证明文件里真的有什么，再让 LLM 只解释有证据的内容。", 80, 272, 660, 96, {
      size: 28,
      bold: true,
      color: COLORS.teal,
    });
    addCard(slide, 810, 94, 330, 118, "不是", "把文件丢给 LLM，然后让它猜 schema。", COLORS.red, COLORS.redLight);
    addCard(slide, 810, 244, 330, 142, "而是", "先 deterministic parser，再 evidence-grounded semantic layer。", COLORS.teal, COLORS.tealLight);
    addPill(slide, "Study, not product", 80, 430, 190, COLORS.blue, COLORS.blueLight);
    addPill(slide, "Field-level evaluation", 288, 430, 220, COLORS.teal, COLORS.tealLight);
    addPill(slide, "No unsupported guessing", 526, 430, 240, COLORS.amber, COLORS.amberLight);
    addFooter(slide, 1);
  }

  // Slide 2
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "问题：科学数据常常没有清楚说明", "CSV、HDF5、时间序列和二进制文件里，字段可能有名字，但不一定有清楚意义。");
    addCard(slide, 78, 202, 330, 180, "看起来像数字", "00123 可能是 ID，不是可以做加减乘除的数字。", COLORS.amber, COLORS.amberLight);
    addCard(slide, 474, 202, 330, 180, "看起来像表格", "HDF5 其实有层级结构。把它压平成一张表会丢信息。", COLORS.blue, COLORS.blueLight);
    addCard(slide, 870, 202, 330, 180, "看起来像时间", "频率、缺失时间段、时区都需要计算，不能凭感觉猜。", COLORS.teal, COLORS.tealLight);
    addText(slide, "如果直接让 LLM 猜，它可能编出不存在的字段、猜错单位，或者给出听起来合理但没有证据的解释。", 108, 464, 1060, 82, {
      size: 25,
      bold: true,
      color: COLORS.red,
      align: "center",
    });
    addFooter(slide, 2);
  }

  // Slide 3
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "决定：先证明结构，再解释意义", "这是一条方法论边界：LLM 不能凭空创造 schema。");
    addCard(slide, 96, 210, 470, 250, "Deterministic parser 做什么？", "读取真实存在的结构：列名、数据类型、HDF5 path、shape、attributes、缺失值、时间间隔。", COLORS.teal, COLORS.tealLight);
    addCard(slide, 714, 210, 470, 250, "LLM 做什么？", "在已有证据范围内解释：缩写、字段描述、语义类型、低风险 metadata。证据不足就输出 unknown。", COLORS.amber, COLORS.amberLight);
    addSimpleArrow(slide, 560, 300, 145, "再交给", COLORS.muted, COLORS.white);
    addText(slide, "规则：Tier 4 的 LLM 推断不能覆盖 Tier 1 的显式 metadata。", 146, 520, 990, 42, {
      size: 22,
      bold: true,
      color: COLORS.ink,
      align: "center",
    });
    addFooter(slide, 3);
  }

  // Slide 4
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "方法：Evidence-Grounded Schema Extraction", "每一步都保留证据，让 schema 不是猜出来的。");
    const steps = [
      ["Raw data", COLORS.muted, COLORS.white],
      ["Detect type", COLORS.blue, COLORS.blueLight],
      ["Extract structure", COLORS.teal, COLORS.tealLight],
      ["Capture evidence", COLORS.teal, COLORS.tealLight],
      ["Add semantics", COLORS.amber, COLORS.amberLight],
      ["Evaluate", COLORS.green, COLORS.greenLight],
    ];
    let x = 50;
    for (const [label, color, fill] of steps) {
      addSimpleArrow(slide, x, 238, 185, label, color, fill);
      x += 196;
    }
    addCard(slide, 92, 390, 320, 126, "Physical", "真实结构：列、dtype、path、shape、missingness。", COLORS.teal, COLORS.tealLight);
    addCard(slide, 480, 390, 320, 126, "Logical", "组织方式：时间轴、ID、measurement、relationship。", COLORS.blue, COLORS.blueLight);
    addCard(slide, 868, 390, 320, 126, "Semantic", "人类意义：温度、单位、站点、研究用途。", COLORS.amber, COLORS.amberLight);
    addFooter(slide, 4);
  }

  // Slide 5
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "几个必须听懂的词", "这些词决定了我们怎么设计实验和解释结果。");
    addCard(slide, 70, 192, 250, 178, "Pilot", "小规模试点数据。先用它检查 pipeline 是否跑通。", COLORS.blue, COLORS.blueLight);
    addCard(slide, 370, 192, 250, 178, "Gold", "人工写的标准答案。系统输出要和它比较。", COLORS.green, COLORS.greenLight);
    addCard(slide, 670, 192, 250, 178, "External", "来自 Dryad / Zenodo 的真实公开数据。", COLORS.teal, COLORS.tealLight);
    addCard(slide, 970, 192, 250, 178, "Distractor", "检索时故意放进去的干扰文件，测试系统会不会选错。", COLORS.amber, COLORS.amberLight);
    addText(slide, "same-family distractor 更难：它和目标来自同一个数据包，描述和字段都很像。\ncross-domain distractor 更广：它来自不同主题，用来测试泛化。", 120, 448, 1040, 86, {
      size: 22,
      color: COLORS.ink,
      align: "center",
    });
    addFooter(slide, 5);
  }

  // Slide 6
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "现在已经做到了什么", "项目已经从 scaffold 走到可运行的研究原型。");
    addMetricCard(slide, "Internal pilot", "9", "CSV / HDF5 / time-series", 86, 194, COLORS.blue, COLORS.blueLight);
    addMetricCard(slide, "External files", "16", "Dryad + Zenodo, all derived", 470, 194, COLORS.teal, COLORS.tealLight);
    addMetricCard(slide, "Retrieval pool", "10 + 6", "targets + distractors", 854, 194, COLORS.amber, COLORS.amberLight);
    addCard(slide, 92, 410, 330, 122, "Deterministic baseline", "字段级评估、uncertainty、error modes 都已经生成。", COLORS.teal, COLORS.white);
    addCard(slide, 474, 410, 330, 122, "Retrieval evaluation", "metadata / README / schema-enhanced 三种方式可比较。", COLORS.blue, COLORS.white);
    addCard(slide, 856, 410, 330, 122, "Semantic layer", "能跑 annotation、validation、merge-back，但收益还不稳定。", COLORS.amber, COLORS.white);
    addFooter(slide, 6);
  }

  // Slide 7
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "当前结果：schema 帮检索更准", "在 16 个真实外部文件、10 个目标 query 的池子里比较。");
    addMetricCard(slide, "metadata_only", "0.6000", "recall@1", 95, 208, COLORS.muted, COLORS.white);
    addMetricCard(slide, "readme_only", "0.5000", "recall@1", 470, 208, COLORS.blue, COLORS.blueLight);
    addMetricCard(slide, "schema_enhanced", "0.8000", "recall@1", 845, 208, COLORS.green, COLORS.greenLight);
    addText(slide, "解释：只看文件描述不够；把真实字段、单位、时间轴和 evidence 放进检索材料后，更容易找到正确数据。", 120, 424, 1040, 76, {
      size: 24,
      bold: true,
      color: COLORS.ink,
      align: "center",
    });
    addText(slide, "注意：这还不是最终 benchmark，只是当前扩大后的 Dryad + Zenodo pool。", 220, 526, 840, 36, {
      size: 17,
      color: COLORS.muted,
      align: "center",
    });
    addFooter(slide, 7);
  }

  // Slide 8
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "当前限制：不是数据不够，而是语义层还要更稳", "限制要写清楚，因为这是 study，不是演示魔法。");
    addCard(slide, 86, 190, 342, 210, "Limit 1: Endpoint timeout", "Greenland cod year1 和 functional_traits 已切成字段组，但远端模型仍会超时。", COLORS.red, COLORS.redLight);
    addCard(slide, 470, 190, 342, 210, "Limit 2: Safe but low-yield", "semantic merge 很保守，不会乱改 schema；但真正带来指标增益的例子还少。", COLORS.amber, COLORS.amberLight);
    addCard(slide, 854, 190, 342, 210, "Limit 3: Benchmark not frozen", "external corpus 已经进来，但最终 target / distractor 还要继续 hardening。", COLORS.blue, COLORS.blueLight);
    addText(slide, "解决方向：retry/backoff、group-level resume、更小字段块、更多 regression tests、冻结 benchmark。", 132, 478, 1016, 52, {
      size: 23,
      bold: true,
      color: COLORS.ink,
      align: "center",
    });
    addFooter(slide, 8);
  }

  // Slide 9
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "如何收敛：从可运行到可发表", "最终目标是一个可信的研究结论，而不是一个会猜的 demo。");
    const items = [
      ["1", "稳定 semantic runner", "支持重试、断点续跑、字段组级缓存。"],
      ["2", "找到 measurable gain", "至少一个 semantic merge 能提高 gold 对齐。"],
      ["3", "冻结 benchmark", "明确 target、distractor、keep、excluded。"],
      ["4", "形成论文材料", "方法、实验、失败模式、限制都可复现。"],
    ];
    let y = 178;
    for (const [num, title, body] of items) {
      slide.shapes.add({
        geometry: "ellipse",
        position: { left: 100, top: y + 10, width: 48, height: 48 },
        fill: COLORS.teal,
        line: { fill: COLORS.teal, width: 0 },
      }).text = num;
      const circle = slide.shapes.items[slide.shapes.items.length - 1];
      circle.text.typeface = FONT.body;
      circle.text.fontSize = 20;
      circle.text.bold = true;
      circle.text.color = COLORS.white;
      circle.text.alignment = "center";
      circle.text.verticalAlignment = "middle";
      addText(slide, title, 172, y, 420, 30, {
        size: 22,
        bold: true,
        color: COLORS.ink,
      });
      addText(slide, body, 172, y + 34, 920, 26, {
        size: 17,
        color: COLORS.muted,
      });
      y += 96;
    }
    addText(slide, "最终一句话：让 AI 的解释站在证据上，而不是站在猜测上。", 166, 590, 940, 42, {
      size: 26,
      bold: true,
      color: COLORS.teal,
      align: "center",
    });
    addFooter(slide, 9);
  }

  for (const slide of presentation.slides.items) {
    if (slide.speakerNotes?.setText) {
      slide.speakerNotes.setText("Use this slide to explain the study in plain language. Keep focus on evidence first, LLM second.");
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

