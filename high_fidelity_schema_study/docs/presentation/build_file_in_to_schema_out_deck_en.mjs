import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const artifactToolUrl = pathToFileURL(require.resolve("@oai/artifact-tool")).href;
const { Presentation, PresentationFile } = await import(artifactToolUrl);

const OUT_DIR = path.resolve("high_fidelity_schema_study/docs/presentation");
const SCRATCH_DIR = path.resolve("high_fidelity_schema_study/tmp/slides/file-in-to-schema-out-en");
const PPTX_PATH = path.join(OUT_DIR, "file_in_to_schema_out_process_en.pptx");

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
  title: "Arial",
  body: "Arial",
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
  addText(slide, `File In -> Schema Out Pipeline Details · ${index}/9`, 64, 678, 600, 24, {
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

  // Slide 1: Cover
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addText(slide, "From File Input to Unified Schema Envelope", 74, 86, 950, 86, {
      size: 42,
      bold: true,
      color: COLORS.ink,
      typeface: FONT.title,
    });
    addText(slide, "High-Fidelity Schema Extraction Pipeline: Architecture & Details", 78, 170, 850, 40, {
      size: 22,
      color: COLORS.muted,
    });
    addText(slide, "Extract objective structures and facts programmatically, then enrich semantics under strict evidence constraints.", 80, 260, 660, 130, {
      size: 28,
      bold: true,
      color: COLORS.teal,
    });
    addCard(slide, 810, 94, 330, 118, "Physical First", "Deterministic extractors parse objective file headers and metadata.", COLORS.blue, COLORS.blueLight);
    addCard(slide, 810, 244, 330, 142, "Graph Projection", "Claims and evidence are decoupled, deduplicated, and linked in a trace graph.", COLORS.teal, COLORS.tealLight);
    addPill(slide, "Deterministic-first", 80, 430, 200, COLORS.blue, COLORS.blueLight);
    addPill(slide, "Evidence-constrained", 296, 430, 220, COLORS.teal, COLORS.tealLight);
    addPill(slide, "Unified Schema Envelope", 532, 430, 230, COLORS.amber, COLORS.amberLight);
    addFooter(slide, 1);
  }

  // Slide 2: Philosophy
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Core Philosophy: Deterministic-First", "Overcoming the lack of reproducibility, hallucinations, and un-auditability of black-box LLM guessing.");
    addCard(slide, 78, 202, 330, 200, "Program-Led Ingestion", "Dedicated deterministic extractors parse structural layout, column headers, shape, and types as the source of truth.", COLORS.blue, COLORS.blueLight);
    addCard(slide, 474, 202, 330, 200, "Capture Physical Evidence", "Automatically logs the exact file offsets, attributes, or line numbers for each decision into an EvidenceRecord pool.", COLORS.teal, COLORS.tealLight);
    addCard(slide, 870, 202, 330, 200, "Constrained Semantic Merger", "LLM-inferred properties are merged only when backed by documented evidence and after passing compatibility checks.", COLORS.amber, COLORS.amberLight);
    addText(slide, "Boundary Rule: Inferred semantic attributes can never overwrite explicit physical and structural evidence.", 108, 468, 1060, 48, {
      size: 24,
      bold: true,
      color: COLORS.red,
      align: "center",
    });
    addFooter(slide, 2);
  }

  // Slide 3: Phase 1: File Intake
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Phase 1: File Intake & Format Detection", "Smart parser routing with multi-tiered fallback and conflict adjudication.");
    addCard(slide, 70, 192, 260, 210, "1. Resource Validation", "Validates input as file or directory_store (e.g., Zarr) via _actual_resource_kind. Mismatches halt execution immediately.", COLORS.blue, COLORS.white);
    addCard(slide, 355, 192, 260, 210, "2. Multi-Signal Probing", "● Magic bytes matching\n● Directory structure checks\n● Filename suffix parsing\n● Delimiter Sniffer text probe", COLORS.teal, COLORS.white);
    addCard(slide, 640, 192, 260, 210, "3. Priority & Override", "● Magic > Hint > Suffix > Text\n● HDF5 signals are auto-upgraded to netcdf if NetCDF4 attribute markers are detected in .nc/.cdf files.", COLORS.green, COLORS.white);
    addCard(slide, 925, 192, 280, 210, "4. Conflict Handling", "Conflicts between strong signals (e.g., magic vs hint) trigger automatic abstention, falling back to a raw_binary schema.", COLORS.red, COLORS.redLight);
    addText(slide, "This phase guarantees robust, zero-guess routing from raw datasets to matching deterministic extractors.", 120, 470, 1040, 60, {
      size: 20,
      color: COLORS.muted,
      align: "center",
    });
    addFooter(slide, 3);
  }

  // Slide 4: Phase 2: CSV & JSON
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Phase 2: Deterministic Extraction - CSV & JSON", "Applying conservative profiling and nested traversal strategies for structured text files.");
    addCard(slide, 78, 190, 520, 280, "CSV Profiler: Conservative Typing & Zero Protection", "● Reads column headers and samples up to 200 rows.\n● int/float/datetime require 100% uniformity in samples.\n● Leading zero detection (_has_leading_zero): forces columns with leading zeros (e.g., '0123') to string to preserve codes.\n● Falls back to string on any parsing conflict to avoid over-claiming physical structures.", COLORS.teal, COLORS.tealLight);
    addCard(slide, 678, 190, 520, 280, "JSON Profiler: Traversal & Declared Schemas", "● Bounds file ingestion (16MB) to ensure memory safety.\n● Declared Mode: Crawls standard JSON Schema properties to generate declared claims; validates samples.\n● Observed Mode: Flattens dynamic trees using a recursive visit(val, path, index) to track paths (e.g., $.store.book[]).\n● Records column nullability without guessing semantics.", COLORS.blue, COLORS.blueLight);
    addText(slide, "Physical schemas represent objective fingerprints; extractors abstain from guessing semantic meanings.", 120, 510, 1040, 36, {
      size: 18,
      color: COLORS.muted,
      bold: true,
      align: "center",
    });
    addFooter(slide, 4);
  }

  // Slide 5: Phase 2: Zarr & Multidimensional
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Phase 2: Deterministic Extraction - Zarr & High-Dim Data", "Metadata-only, high-performance schema harvesting for multi-dimensional scientific files.");
    addCard(slide, 78, 190, 520, 280, "Zarr Extractor: Consolidated Metadata & Version Check", "● Prioritizes reading consolidated .zmetadata for fast I/O; falls back to crawling .zgroup/.zarray config files.\n● Automatically aborts and abstains on Zarr v3 (zarr_format == 3), as the current engine is optimized for Zarr v2.\n● Inspects configuration metadata only, never reading chunk data payloads for zero-I/O overhead.", COLORS.teal, COLORS.tealLight);
    addCard(slide, 678, 190, 520, 280, "Coordinate & Dimension Mapping (CF & Xarray)", "● Dimension mapping: resolves shape and axis sizes via _ARRAY_DIMENSIONS declarations.\n● Coordinates mapping: identifies coordinate roles (dimension_coordinate, auxiliary_coordinate) and axes (X/Y/Z/T) based on CF conventions and units.", COLORS.blue, COLORS.blueLight);
    addText(slide, "Climate and Forecast (CF) conventions provide a standardized dictionary to discover high-dimensional data grids.", 120, 510, 1040, 36, {
      size: 18,
      color: COLORS.muted,
      bold: true,
      align: "center",
    });
    addFooter(slide, 5);
  }

  // Slide 6: Phase 3: Profiling & Normalization
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Phase 3: Data Profiling & Normalization", "Enriching physical descriptions with calculated timelines and standardized physical scales.");
    addCard(slide, 78, 190, 342, 260, "Time Axis Analysis (analyze_temporal_semantics)", "Scores columns based on physical type, name patterns, and semantics. Selects the highest-scoring candidate (>=0.7) as the time_axis. Emits warnings if multiple candidates tie (score delta <= 0.05).", COLORS.teal, COLORS.white);
    addCard(slide, 470, 190, 342, 260, "Temporal Grid Properties", "● Timezone detection: checks naive/aware offsets.\n● Frequency: identifies the dominant interval (e.g., 60s -> 1 minute).\n● Regularity: requires the dominant frequency to describe >=95% of intervals.\n● Missing intervals: calculates gaps based on frequency.", COLORS.blue, COLORS.white);
    addCard(slide, 862, 190, 342, 260, "Unit Normalization", "● Extracts unit tags from column suffixes or metadata attributes.\n● Queries UNIT_ALIASES to normalize units (e.g., Celsius, mm) to canonical names and UCUM codes (Cel, mm, mg/L).\n● Tracks evidence_basis (e.g. explicit_metadata).", COLORS.green, COLORS.white);
    addText(slide, "This phase adds calculated timelines and normalized physical scales to the physical layout.", 120, 500, 1040, 36, {
      size: 18,
      color: COLORS.muted,
      align: "center",
    });
    addFooter(slide, 6);
  }

  // Slide 7: Phase 4: Semantic Layer
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Phase 4: Semantic Integration & Safety Merger", "How the pipeline safely integrates LLM README interpretations without breaking structural truth.");
    addCard(slide, 78, 190, 520, 280, "1. Grounding Bundles & System Prompt Constraints", "● Combines the physical schema and external README context into a prioritized GroundingSnippet context.\n● Injects strict SYSTEM_RULES: prohibits inventing physical fields, requires citing source lines in supporting_evidence, and forces unknown when uncertain.", COLORS.teal, COLORS.tealLight);
    addCard(slide, 678, 190, 520, 280, "2. Validator & Merger Adjudication", "● No Evidence Rejection: discards proposed changes immediately if supporting_evidence is empty.\n● Compatibility Checks: flags incompatible logical-semantic pairs (e.g., latitude mapped as a measurement).\n● Deterministic Protection: LLM cannot overwrite explicit metadata unless compatible and confidence >= 0.85.", COLORS.amber, COLORS.amberLight);
    addText(slide, "Safety Rule: It is always better to claim unknown due to lack of evidence than to output unsupported guesses.", 120, 510, 1040, 36, {
      size: 18,
      color: COLORS.red,
      bold: true,
      align: "center",
    });
    addFooter(slide, 7);
  }

  // Slide 8: Phase 5: Envelope
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Phase 5: Unified Schema Envelope Projection", "Projecting outcomes into a standardized, decoupled Claims-Evidence graph structure.");
    addCard(slide, 78, 190, 520, 280, "Global Evidence Registry (evidence)", "Contains a deduplicated pool of physical observations. Each record is assigned an ID (e.g., e0001, e0002) and captures its provenance (structural, statistical, explicit_metadata), file source path, description, and confidence.", COLORS.blue, COLORS.blueLight);
    addCard(slide, 678, 190, 520, 280, "Unified Claims Registry (claims)", "Abstracts physical type, logical role, semantic type, and units into claims. Each claim is assigned a claim_id, defines its subject (field_path), and maps back to its evidence sources via evidence_refs.", COLORS.teal, COLORS.tealLight);
    addText(slide, "The unified envelope ensures that every metadata property in the output is fully auditable and traceable.", 120, 500, 1040, 60, {
      size: 20,
      color: COLORS.ink,
      bold: true,
      align: "center",
    });
    addFooter(slide, 8);
  }

  // Slide 9: Walkthrough
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Walkthrough: Buoy Sensor Data Ingestion", "Tracking a buoy CSV file from raw ingestion to the unified schema envelope.");
    const steps = [
      ["1", "Intake & Routing", "Buoy CSV is ingested. Sniffer detects comma delimiters and routes to csv_conservative_profiler."],
      ["2", "Physical Inference", "ts_utc is mapped to datetime, water_temp_c to float, buoy_id (with leading zero '0052') is forced to string."],
      ["3", "Profiling & Normalization", "ts_utc is selected as time_axis (frequency: 60s, regular); water_temp_c unit normalized to Celsius."],
      ["4", "LLM Semantic Integration", "LLM interprets README context, proposes quality_flag semantic type for flag. Validator merges it with evidence."],
      ["5", "Envelope Projection", "Outputs unified JSON. Schema claims are mapped to e0001 (headers) and e0002 (README citation)."],
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
    addText(slide, "Conclusion: Combining deterministic foundations with evidence-constrained LLM semantics delivers safe, auditable search metadata.", 166, 618, 940, 36, {
      size: 21,
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
