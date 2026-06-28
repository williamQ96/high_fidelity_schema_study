import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT_DIR = path.resolve("docs/presentation");
const SCRATCH_DIR = path.resolve("tmp/slides/phases-summary");
const PPTX_PATH = path.join(OUT_DIR, "phases_1_to_20_summary.pptx");

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
    adjustmentList: [{ name: "adj", formula: "val 8000" }],
  });
  addText(slide, title, x + 18, y + 16, w - 36, 30, {
    size: 18,
    bold: true,
    color,
  });
  addText(slide, body, x + 18, y + 52, w - 36, h - 68, {
    size: 14,
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

function addFooter(slide, index) {
  addText(slide, `High-Fidelity Schema Extraction Study · Phases 1-20 Summary · Slide ${index}/10`, 64, 678, 600, 24, {
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

  // Slide 1: Title Slide
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addText(slide, "High-Fidelity Schema Extraction Study", 74, 120, 1100, 86, {
      size: 44,
      bold: true,
      color: COLORS.teal,
      typeface: FONT.title,
    });
    addText(slide, "A Detailed Overview of Study Phases 1-20: Purpose & Implementation", 78, 214, 1100, 48, {
      size: 24,
      color: COLORS.ink,
    });
    addText(slide, "Establishing a deterministic-first, evidence-grounded substrate for scientific datasets.", 80, 310, 850, 96, {
      size: 20,
      color: COLORS.muted,
    });
    addPill(slide, "Phases 1-11: Frozen Baseline", 80, 450, 260, COLORS.blue, COLORS.blueLight);
    addPill(slide, "Phases 12-20: Extensions", 360, 450, 260, COLORS.teal, COLORS.tealLight);
    addFooter(slide, 1);
  }

  // Slide 2: Foundation & Pilot Setup (Phases 1-3)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Foundation & Pilot Setup (Phases 1-3)", "Establishing the repository workspace, pilot files, and human-verified schemas.");

    addCard(slide, 64, 180, 360, 460, "Phase 1: Repository Scaffolding",
      "Purpose:\nBootstrap codebase, models, CLI, and automated builders.\n\nImplementation:\n- Created package files, models.py (field claims, evidence, requests), and cli.py.\n- Setup scripts for pilot and derived schema compilation.",
      COLORS.blue, COLORS.white);

    addCard(slide, 460, 180, 360, 460, "Phase 2: Internal Pilot Corpus",
      "Purpose:\nConstruct a multi-format pilot testbed across different structure difficulties.\n\nImplementation:\n- Created a 3x3 pilot layout: CSV, HDF5, Time-Series across Easy, Medium, Hard tiers.\n- Generated 9 pilot files under data/raw/.\n- Added sidecar READMEs and pilot manifest.",
      COLORS.teal, COLORS.white);

    addCard(slide, 856, 180, 360, 460, "Phase 3: Gold Reference Construction",
      "Purpose:\nEstablish a human-verified reference truth for scoring validation.\n\nImplementation:\n- Authored 9 reference JSONs under data/gold/ detailing physical/logical types, units, and necessity.\n- Ran a consistency review on 50 fields to lock labels.",
      COLORS.green, COLORS.white);

    addFooter(slide, 2);
  }

  // Slide 3: Deterministic Base & External Ingestion (Phases 4-5)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Deterministic Base & External Ingestion (Phases 4-5)", "Parsing file structures deterministically and staging a real-world validation corpus.");

    addCard(slide, 80, 180, 520, 460, "Phase 4: Deterministic Extraction Baseline",
      "Purpose:\nEstablish baseline schemas and diagnostics without LLM guesswork.\n\nImplementation:\n- Implemented CSV and HDF5 engines with string dtype normalization.\n- Built a shared time-series analysis module.\n- Added profiling for missingness, ID quality, and multi-file relationship candidates.\n- Saved derived output schemas inside data/derived/.",
      COLORS.teal, COLORS.white);

    addCard(slide, 680, 180, 520, 460, "Phase 5: External Corpus Preparation",
      "Purpose:\nIngest diverse real-world datasets from Dryad and Zenodo to test generalizability.\n\nImplementation:\n- Authored import_external_corpus.py using public file stream paths to bypass API auth blocks.\n- Staged 16 external candidate files.\n- Generated deterministic derived schemas under data/external/derived/.\n- Classified candidates into targets and distractors.",
      COLORS.blue, COLORS.white);

    addFooter(slide, 3);
  }

  // Slide 4: Testing & Evaluation Pipeline (Phases 6-7)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Testing & Evaluation Pipeline (Phases 6-7)", "Protecting extraction code against regressions and measuring field-level schema accuracy.");

    addCard(slide, 80, 180, 520, 460, "Phase 6: Validation & Regression Protection",
      "Purpose:\nEnsure code modifications do not break or degrade parser performance.\n\nImplementation:\n- Added pytest unit tests checking CSV parsing, HDF5, and time-series regularity.\n- Coded regression assertions matching derived attributes against known reference schema subsets.",
      COLORS.blue, COLORS.white);

    addCard(slide, 680, 180, 520, 460, "Phase 7: Evaluation Pipeline",
      "Purpose:\nQuantify schema completeness and accuracy across physical/logical/semantic dimensions.\n\nImplementation:\n- Created evaluate_internal_baseline.py to score derived schemas field-by-field.\n- Summarized errors by failure type (e.g., incorrect type, unparsed column).\n- Compiled confidence-bucket calibration statistics.",
      COLORS.green, COLORS.white);

    addFooter(slide, 4);
  }

  // Slide 5: Semantic Augmentation & Retrieval (Phases 8-9)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Semantic Augmentation & Retrieval (Phases 8-9)", "Refining schema semantics using constrained LLMs and testing retrieval performance.");

    addCard(slide, 80, 180, 520, 460, "Phase 8: Semantic Augmentation Layer",
      "Purpose:\nResolve domain meaning via LLMs without modifying physical schemas.\n\nImplementation:\n- Coded semantic_annotate.py to run field-sliced prompt runs.\n- Formed grounding bundles under data/semantic_grounding/.\n- Programmed merge_semantic_annotations.py with validation constraints to prevent ungrounded claims.\n- Added conflict tracking for explicit vs inferred metadata.",
      COLORS.amber, COLORS.white);

    addCard(slide, 680, 180, 520, 460, "Phase 9: Retrieval Experiment",
      "Purpose:\nCompare schema-enhanced dataset search against metadata or README baselines.\n\nImplementation:\n- Built search indexes for README-only, metadata-only, and schema-enhanced schemas.\n- Coded evaluate_retrieval_artifacts.py to test 10 queries.\n- Demonstrated schema metadata significantly boosts search Recall@1.",
      COLORS.blue, COLORS.white);

    addFooter(slide, 5);
  }

  // Slide 6: Hardening & Benchmark Release (Phases 10-11)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Hardening & Benchmark Release (Phases 10-11)", "Locking the evaluation slice, drafting the paper, and building the reviewer workspace.");

    addCard(slide, 80, 180, 520, 460, "Phase 10: Scale-Up & Corpus Hardening",
      "Purpose:\nStandardize benchmark criteria and define rules for raw binary files.\n\nImplementation:\n- Defined dataset promotion/exclusion guidelines.\n- Enforced raw binary policy: abstain from schema field claims, record file-level evidence only.",
      COLORS.blue, COLORS.white);

    addCard(slide, 680, 180, 520, 460, "Phase 11: Paper Draft & GUI Demo",
      "Purpose:\nCompile tables and charts, write the draft, and construct an interactive demo.\n\nImplementation:\n- Wrote paper_draft.md using frozen metrics.\n- Coded build_paper_tables.py and build_paper_figures.py (generating SVG charts).\n- Built gui_demo web server (server.py) with live scratch upload extraction.",
      COLORS.teal, COLORS.white);

    addFooter(slide, 6);
  }

  // Slide 7: Substrate Refactoring & NetCDF/CF (Phases 12-13)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Substrate Refactoring & NetCDF/CF (Phases 12-13)", "Overhauling architecture with registries, routing, and adding NetCDF/CF scientific support.");

    addCard(slide, 80, 180, 520, 460, "Phase 12: Deterministic Substrate Upgrade",
      "Purpose:\nIntroduce typed contracts, routing, and a temporal validator.\n\nImplementation:\n- Added central capability registry and signature-based routing.\n- Standardized typed ExtractionRequest and ExtractionOutcome.\n- Developed timezone-aware temporal semantics module for calendar regularity and coord conflicts.\n- Tested on a 13-case challenge pack.",
      COLORS.teal, COLORS.white);

    addCard(slide, 680, 180, 520, 460, "Phase 13: NetCDF/CF Scientific Format",
      "Purpose:\nSupport NetCDF coordinates and CF conventions under the registry.\n\nImplementation:\n- Built classic (scipy) and NetCDF4 (h5py) metadata extractors.\n- Decoded CF coordinates, calendars, dimensions, and units.\n- Shared temporal validation.\n- Verified against a 14-case challenge pack.",
      COLORS.blue, COLORS.white);

    addFooter(slide, 7);
  }

  // Slide 8: Zarr Array Integration (Phase 14A-C)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Zarr Array Integration (Phases 14A-C)", "Enabling directory-store inputs and validating compatibility against third-party Zarr output.");

    addCard(slide, 64, 180, 360, 460, "Phase 14A: Zarr Directory Intake",
      "Purpose:\nSupport multi-file local directory stores and extract Zarr v2 array hierarchies.\n\nImplementation:\n- Extended intake to support directory stores.\n- Coded light Zarr v2 metadata extractor parsing .zarray/.zgroup files and _ARRAY_DIMENSIONS.\n- Tested on a 14-case challenge pack.",
      COLORS.blue, COLORS.white);

    addCard(slide, 460, 180, 360, 460, "Phase 14B: Layout Compatibility",
      "Purpose:\nValidate the extractor against diverse producer-shaped Zarr configurations.\n\nImplementation:\n- Tested a 17-case local compatibility corpus.\n- Implemented chunk-directory path pruning and group-scoped coordinate references.\n- Handled NumPy structured dtypes.",
      COLORS.teal, COLORS.white);

    addCard(slide, 856, 180, 360, 460, "Phase 14C: External Conformance",
      "Purpose:\nMatch outputs against official zarr-python and Xarray load behavior.\n\nImplementation:\n- Curated 12 conformance cases from official test suites.\n- Evaluated cross-parser differences in fill value representations and default behaviors.",
      COLORS.green, COLORS.white);

    addFooter(slide, 8);
  }

  // Slide 9: Structured Formats: Parquet, JSON, XML (Phases 15-16)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Structured Formats: Parquet, JSON, XML (Phases 15-16)", "Extracting schemas from Parquet footers, JSON documents, and XML element trees.");

    addCard(slide, 64, 180, 360, 460, "Phase 15A: Parquet / Arrow",
      "Purpose:\nExtract PyArrow schema and Parquet footer metadata without reading values.\n\nImplementation:\n- Mapped Arrow logical schema paths to Parquet columns.\n- Extracted row group counts, definitions, repetition levels, and column stats.",
      COLORS.blue, COLORS.white);

    addCard(slide, 460, 180, 360, 460, "Phase 16A: JSON Structure",
      "Purpose:\nExtract observed structures and declared JSON Schema definitions.\n\nImplementation:\n- Coded sample-bounded recursive path traversal.\n- Parsed declared fields from schema sidecars.\n- Flagged conflicts when samples deviated from schema definitions.",
      COLORS.teal, COLORS.white);

    addCard(slide, 856, 180, 360, 460, "Phase 16B: XML / XSD Structure",
      "Purpose:\nExtract namespace coordinates and structures from XML and XSD schemas.\n\nImplementation:\n- Namespace-aware tag and attribute path observation.\n- Tracked repeated elements, XSD declarations, and xsi:type conflicts.",
      COLORS.green, COLORS.white);

    addFooter(slide, 9);
  }

  // Slide 10: Unified Envelope, Evaluator & Workbench (Phases 17-20)
  {
    const slide = presentation.slides.add();
    addBackground(slide);
    addTitle(slide, "Unified Envelope, Evaluator & Workbench (Phases 17-20)", "Projecting outcomes into a single model, unifying evaluation, and completing release prep.");

    addCard(slide, 64, 180, 270, 460, "Phase 17: Unified Envelope",
      "Purpose:\nProject outcomes into a cross-format envelope.\n\nImplementation:\n- Coded extract_unified() for identity, physical, logical, semantic, evidence, and provenance.\n- Kept legacy APIs immutable.",
      COLORS.blue, COLORS.white);

    addCard(slide, 350, 180, 270, 460, "Phase 18: Evaluation Harness",
      "Purpose:\nProvide a single entrypoint for all validation tracks.\n\nImplementation:\n- Created unified evaluator running 11 distinct test tracks.\n- Kept track metrics separate to preserve transparency.",
      COLORS.teal, COLORS.white);

    addCard(slide, 636, 180, 270, 460, "Phase 19: Agent-Ready Exports",
      "Purpose:\nProvide read-only context for downstream AI coding agents.\n\nImplementation:\n- Exported structured JSON with claims, evidence, and search context.\n- Enforced read-only mutation guards.",
      COLORS.amber, COLORS.white);

    addCard(slide, 922, 180, 290, 460, "Phase 20: Release Readiness",
      "Purpose:\nValidate final codebase cleanliness and path hygiene.\n\nImplementation:\n- Wrote gui_demo/DESIGN.md.\n- Cleared local absolute paths from code and artifacts.\n- Passed final release audit with ready=true.",
      COLORS.green, COLORS.white);

    addFooter(slide, 10);
  }

  for (const slide of presentation.slides.items) {
    if (slide.speakerNotes?.setText) {
      slide.speakerNotes.setText("Use this slide to outline study phases. Explain Purpose and Implementation method clearly.");
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
