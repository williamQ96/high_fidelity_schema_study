import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT_DIR = path.resolve("high_fidelity_schema_study/docs/presentation");
const SCRATCH_DIR = path.resolve("high_fidelity_schema_study/tmp/slides/schema-study-high-school-en");
const PPTX_PATH = path.join(OUT_DIR, "schema_extraction_study_high_school_EN.pptx");

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
  title: "Poppins",
  body: "Lato",
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
  addText(slide, title, 64, 44, 940, 62, {
    size: 34,
    bold: true,
    color: COLORS.ink,
    typeface: FONT.title,
  });
  if (subtitle) {
    addText(slide, subtitle, 66, 104, 990, 36, {
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
  slide.shapes.add({
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
    typeface: FONT.title,
  });
  addText(slide, body, x + 22, y + 58, w - 44, h - 76, {
    size: 17,
    color: COLORS.ink,
  });
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
    typeface: FONT.title,
  });
  addText(slide, value, x + 22, y + 50, 296, 48, {
    size: 38,
    color,
    bold: true,
    typeface: FONT.title,
  });
  addText(slide, note, x + 22, y + 104, 296, 24, {
    size: 14,
    color: COLORS.muted,
  });
}

function addFooter(slide, index) {
  addText(slide, `High-Fidelity Schema Extraction Study - ${index}/9`, 64, 678, 520, 24, {
    size: 12,
    color: COLORS.muted,
  });
}

function addBackground(slide) {
  slide.background.fill = COLORS.paper;
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: W, height: H },
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

function addNumberedStep(slide, num, title, body, y) {
  const circle = slide.shapes.add({
    geometry: "ellipse",
    position: { left: 100, top: y + 10, width: 48, height: 48 },
    fill: COLORS.teal,
    line: { fill: COLORS.teal, width: 0 },
  });
  circle.text = num;
  circle.text.typeface = FONT.title;
  circle.text.fontSize = 20;
  circle.text.bold = true;
  circle.text.color = COLORS.white;
  circle.text.alignment = "center";
  circle.text.verticalAlignment = "middle";
  addText(slide, title, 172, y, 470, 30, {
    size: 22,
    bold: true,
    color: COLORS.ink,
    typeface: FONT.title,
  });
  addText(slide, body, 172, y + 34, 900, 26, {
    size: 17,
    color: COLORS.muted,
  });
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
    addText(slide, "Stop letting AI guess data fields", 74, 86, 800, 86, {
      size: 42,
      bold: true,
      color: COLORS.ink,
      typeface: FONT.title,
    });
    addText(slide, "A high-school-readable introduction to a schema extraction study", 78, 170, 790, 40, {
      size: 22,
      color: COLORS.muted,
    });
    addText(slide, "Core idea: first prove what is actually inside the file, then let the LLM explain only what the evidence supports.", 80, 272, 680, 106, {
      size: 28,
      bold: true,
      color: COLORS.teal,
    });
    addCard(slide, 820, 94, 330, 118, "Not this", "Send a file to an LLM and ask it to guess the schema.", COLORS.red, COLORS.redLight);
    addCard(slide, 820, 244, 330, 142, "This", "Use a deterministic parser first, then an evidence-grounded semantic layer.", COLORS.teal, COLORS.tealLight);
    addPill(slide, "Study, not product", 80, 430, 190, COLORS.blue, COLORS.blueLight);
    addPill(slide, "Field-level evaluation", 288, 430, 220, COLORS.teal, COLORS.tealLight);
    addPill(slide, "No unsupported guessing", 526, 430, 240, COLORS.amber, COLORS.amberLight);
    addFooter(slide, 1);
  }

  // Slide 2
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "The problem: data files often hide meaning", "A file may have column names, paths, or numbers, but that does not mean the meaning is obvious.");
    addCard(slide, 78, 202, 330, 180, "Looks numeric", "00123 may be an ID, not a number you should average or multiply.", COLORS.amber, COLORS.amberLight);
    addCard(slide, 474, 202, 330, 180, "Looks tabular", "HDF5 can be a tree. Flattening it into one table can destroy structure.", COLORS.blue, COLORS.blueLight);
    addCard(slide, 870, 202, 330, 180, "Looks like time", "Frequency, missing intervals, and time zones must be computed, not guessed.", COLORS.teal, COLORS.tealLight);
    addText(slide, "If an LLM guesses directly, it can invent fields, assign the wrong unit, or give a confident explanation with no evidence.", 108, 464, 1060, 82, {
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
    addTitle(slide, "The decision: prove structure, then explain meaning", "This is the core boundary: the LLM cannot invent schema elements.");
    addCard(slide, 96, 210, 470, 250, "What does the parser do?", "It reads what is really present: column names, data types, HDF5 paths, shapes, attributes, missingness, and time intervals.", COLORS.teal, COLORS.tealLight);
    addCard(slide, 714, 210, 470, 250, "What does the LLM do?", "It explains within the evidence: abbreviations, field descriptions, semantic types, and low-risk metadata. If evidence is missing, output unknown.", COLORS.amber, COLORS.amberLight);
    addSimpleArrow(slide, 560, 300, 145, "then", COLORS.muted, COLORS.white);
    addText(slide, "Rule: an LLM inference cannot override explicit metadata from the file.", 146, 520, 990, 42, {
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
    addTitle(slide, "The method: evidence-grounded schema extraction", "Every step keeps evidence, so the schema is traced back to the file.");
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
    addCard(slide, 92, 390, 320, 126, "Physical", "What exists: columns, dtype, path, shape, missingness.", COLORS.teal, COLORS.tealLight);
    addCard(slide, 480, 390, 320, 126, "Logical", "How data is organized: time axis, ID, measurement, relationship.", COLORS.blue, COLORS.blueLight);
    addCard(slide, 868, 390, 320, 126, "Semantic", "Human meaning: temperature, unit, station, research use.", COLORS.amber, COLORS.amberLight);
    addFooter(slide, 4);
  }

  // Slide 5
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Key terms", "These words explain how the experiment is designed.");
    addCard(slide, 70, 192, 250, 178, "Pilot", "A small controlled dataset set used to check whether the pipeline works.", COLORS.blue, COLORS.blueLight);
    addCard(slide, 370, 192, 250, 178, "Gold", "A human-written answer key. System outputs are judged against it.", COLORS.green, COLORS.greenLight);
    addCard(slide, 670, 192, 250, 178, "External", "Real public data from Dryad and Zenodo, not hand-built examples.", COLORS.teal, COLORS.tealLight);
    addCard(slide, 970, 192, 250, 178, "Distractor", "A file placed in retrieval to see whether the system picks the wrong one.", COLORS.amber, COLORS.amberLight);
    addText(slide, "Same-family distractors are harder: they come from the same data bundle and share words, context, and field patterns.\nCross-domain distractors are broader: they come from different topics and test general robustness.", 110, 448, 1060, 92, {
      size: 21,
      color: COLORS.ink,
      align: "center",
    });
    addFooter(slide, 5);
  }

  // Slide 6
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "What has been built", "The project has moved from a scaffold to a working research prototype.");
    addMetricCard(slide, "Internal pilot", "9", "CSV / HDF5 / time-series", 86, 194, COLORS.blue, COLORS.blueLight);
    addMetricCard(slide, "External files", "16", "Dryad + Zenodo, all derived", 470, 194, COLORS.teal, COLORS.tealLight);
    addMetricCard(slide, "Retrieval pool", "10 + 6", "targets + distractors", 854, 194, COLORS.amber, COLORS.amberLight);
    addCard(slide, 92, 410, 330, 122, "Deterministic baseline", "Field-level evaluation, uncertainty, and error modes now exist.", COLORS.teal, COLORS.white);
    addCard(slide, 474, 410, 330, 122, "Retrieval evaluation", "metadata, README, and schema-enhanced artifacts can be compared.", COLORS.blue, COLORS.white);
    addCard(slide, 856, 410, 330, 122, "Semantic layer", "Annotation, validation, and merge-back work, but gains are not stable yet.", COLORS.amber, COLORS.white);
    addFooter(slide, 6);
  }

  // Slide 7
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Current result: schema helps retrieval", "Comparison over 16 real external files and 10 planted target queries.");
    addMetricCard(slide, "metadata_only", "0.6000", "recall@1", 95, 208, COLORS.muted, COLORS.white);
    addMetricCard(slide, "readme_only", "0.5000", "recall@1", 470, 208, COLORS.blue, COLORS.blueLight);
    addMetricCard(slide, "schema_enhanced", "0.8000", "recall@1", 845, 208, COLORS.green, COLORS.greenLight);
    addText(slide, "Meaning: file descriptions alone are not enough. Adding real fields, units, time axes, and evidence makes the right dataset easier to find.", 120, 424, 1040, 76, {
      size: 24,
      bold: true,
      color: COLORS.ink,
      align: "center",
    });
    addText(slide, "Caveat: this is the current expanded Dryad + Zenodo pool, not the final frozen benchmark.", 220, 526, 840, 36, {
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
    addTitle(slide, "Current limits: the semantic layer needs more stability", "The corpus is no longer the main blocker; execution reliability is.");
    addCard(slide, 86, 190, 342, 210, "Limit 1: Endpoint timeout", "Greenland cod year1 and functional_traits are already split into field groups, but the remote model still times out.", COLORS.red, COLORS.redLight);
    addCard(slide, 470, 190, 342, 210, "Limit 2: Safe but low-yield", "Semantic merge is conservative and does not pollute schemas, but accepted gains are still rare.", COLORS.amber, COLORS.amberLight);
    addCard(slide, 854, 190, 342, 210, "Limit 3: Benchmark not frozen", "The external corpus is integrated, but final target and distractor roles still need hardening.", COLORS.blue, COLORS.blueLight);
    addText(slide, "Fix path: retry/backoff, group-level resume, smaller field chunks, more regression tests, and a frozen benchmark.", 132, 478, 1016, 52, {
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
    addTitle(slide, "How the work converges", "The final goal is a trustworthy study result, not a guessing demo.");
    const items = [
      ["1", "Stabilize the semantic runner", "Add retry, resume, and field-group caching."],
      ["2", "Find measurable gain", "At least one semantic merge should improve gold alignment."],
      ["3", "Freeze the benchmark", "Make target, distractor, keep, and excluded roles explicit."],
      ["4", "Prepare paper artifacts", "Method, experiments, failure modes, and limits should be reproducible."],
    ];
    let y = 178;
    for (const [num, title, body] of items) {
      addNumberedStep(slide, num, title, body, y);
      y += 96;
    }
    addText(slide, "Final message: AI explanations should stand on evidence, not on guessing.", 166, 590, 940, 42, {
      size: 26,
      bold: true,
      color: COLORS.teal,
      align: "center",
    });
    addFooter(slide, 9);
  }

  for (const slide of presentation.slides.items) {
    if (slide.speakerNotes?.setText) {
      slide.speakerNotes.setText("Explain this slide in plain language. Keep the central contrast clear: evidence first, LLM interpretation second.");
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

