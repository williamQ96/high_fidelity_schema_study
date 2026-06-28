import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const artifactToolUrl = pathToFileURL(require.resolve("@oai/artifact-tool")).href;
const { Presentation, PresentationFile } = await import(artifactToolUrl);

const OUT_DIR = path.resolve("docs/presentation");
const SCRATCH_DIR = path.resolve("tmp/slides/current-schema-pipeline-en");
const PPTX_PATH = path.join(OUT_DIR, "current_schema_extraction_pipeline_en.pptx");

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

const FONT = "Arial";

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
  text(slide, `Current schema extraction pipeline | ${index}/16`, 58, 682, 380, 20, {
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
    text(slide, "From Raw Data to Trusted Schema Output", 70, 78, 910, 72, {
      size: 40,
      bold: true,
    });
    text(slide, "Current repository pipeline, grounded in inspected code", 74, 154, 760, 34, {
      size: 20,
      color: COLORS.muted,
    });
    note(
      slide,
      "Canonical stance: deterministic-first extraction, evidence-backed claims, explicit unknown/conflict/abstention states.",
      78,
      252,
      680,
      92,
      COLORS.teal,
    );
    card(slide, 820, 84, 330, 112, "Primary API", "extractors/registry.py::extract_path(ExtractionRequest)", COLORS.blue, COLORS.blueFill);
    card(slide, 820, 224, 330, 112, "Output Forms", "ExtractionOutcome.to_dict() and unified_schema.py::build_unified_schema_envelope()", COLORS.green, COLORS.greenFill);
    card(slide, 820, 364, 330, 112, "Optional Semantic Layer", "semantic_annotate.py and merge_semantic_annotations.py; downstream, evidence-constrained", COLORS.amber, COLORS.amberFill);
    pill(slide, "No LLM-first schema guessing", 78, 396, 242, COLORS.red, COLORS.redFill);
    pill(slide, "Registered extractors only", 338, 396, 218, COLORS.blue, COLORS.blueFill);
    pill(slide, "Traceable claims", 574, 396, 168, COLORS.teal, COLORS.tealFill);
    text(slide, "Inspected code: CLI, registry, extractors, dataclasses, validators, semantic annotation, merge policy, provenance builder, GUI path, tests, docs.", 80, 604, 1040, 36, {
      size: 14,
      color: COLORS.muted,
    });
    notes(slide, "Open by emphasizing that this is not an invented architecture. The deck is grounded in the actual repository: cli.py, extractors/registry.py, each extractor module, semantic_layer.py, unified_schema.py, provenance/test files, and README/docs.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "What Problem Schema Extraction Solves", "Turn heterogeneous scientific files into auditable structure without unsupported invention.", 2);
    card(slide, 78, 190, 342, 210, "Input Reality", "CSV tables, HDF5 hierarchies, NetCDF/CF variables, Zarr directory stores, Parquet footers, JSON/XML structures, and opaque files all expose schema differently.", COLORS.blue, COLORS.blueFill);
    card(slide, 470, 190, 342, 210, "Needed Output", "A structured schema with fields, paths, dtypes, shapes, units, logical roles, temporal properties, claim states, evidence, issues, and provenance.", COLORS.teal, COLORS.tealFill);
    card(slide, 862, 190, 342, 210, "Trust Requirement", "The code prefers unknown, conflicted, partial, failed, or abstained states over hallucinated fields or silent promotion of weak evidence.", COLORS.green, COLORS.greenFill);
    note(slide, "README.md states the canonical job narrowly: establish the strongest schema supported by file structure, explicit metadata, deterministic validators, and recorded evidence.", 112, 468, 1010, 78, COLORS.teal);
    notes(slide, "The repository frames schema extraction as a controlled substrate for later use by retrieval or agents. The goal is not broad autonomous interpretation; it is a strong, defensible schema surface.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Real Entry Points and Output Contracts", "The current code exposes both legacy format-specific commands and the registry-backed generic path.", 3);
    card(slide, 78, 178, 360, 160, "CLI", "cli.py::main()\n\nCommands: extract, extract-csv, extract-hdf5, evaluate, agent-export.\n\nGeneric extract supports --output-shape legacy|envelope|both.", COLORS.blue, COLORS.white);
    card(slide, 460, 178, 360, 160, "Programmatic API", "extractors/registry.py::extract_path(request)\n\nInput: ExtractionRequest(path, format_hint, sample_limit, resource_kind).\n\nOutput: ExtractionOutcome(status, format_decision, extractor, schema, issues).", COLORS.teal, COLORS.white);
    card(slide, 842, 178, 360, 160, "GUI/API Upload", "gui_demo/server.py::extract_uploaded_schema()\n\nRoutes uploads through extract_path, preserves legacy schema, adds extraction_outcome and unified_schema_envelope.", COLORS.green, COLORS.white);
    card(slide, 78, 398, 360, 130, "Legacy Schema", "models.py::DatasetSchema and FieldSchema hold physical/logical/semantic fields plus EvidenceRecord lists.", COLORS.purple, COLORS.purpleFill);
    card(slide, 460, 398, 360, 130, "Unified Envelope", "unified_schema.py::build_unified_schema_envelope() normalizes claims, evidence, conflicts, abstentions, provenance, and evaluation metadata.", COLORS.amber, COLORS.amberFill);
    card(slide, 842, 398, 360, 130, "Agent Export", "agent_exports.py::export_agent_bundle() creates read-only bundles with canonical_mutation_allowed=false.", COLORS.red, COLORS.redFill);
    notes(slide, "This slide names the real hooks. For most technical audiences, the important point is that the generic path is extract_path, while older CSV/HDF5 commands remain for backward compatibility.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Input Data: Sources, Formats, Assumptions", "Accepted input forms are registered explicitly in EXTRACTOR_CAPABILITIES.", 4);
    const rows = [
      ["CSV/TSV", "file", "headers + sampled rows; sample_limit default 200"],
      ["HDF5", "file", "groups/datasets/attrs via h5py"],
      ["NetCDF/CF", "file", "classic magic or HDF5-backed .nc with NetCDF4 markers"],
      ["Zarr v2", "directory_store", "local metadata docs only; no chunk payload reads"],
      ["Parquet", "file", "footer and Arrow schema via pyarrow; no row reads"],
      ["JSON/JSONL", "file", "bounded observed paths or declared JSON Schema"],
      ["XML/XSD", "file", "bounded instance paths or lightweight XSD declarations"],
      ["Raw/unknown", "file or directory", "structured abstention; file-level evidence only"],
    ];
    let y = 178;
    for (const [fmt, kind, assumption] of rows) {
      rect(slide, 78, y, 1124, 46, y % 92 === 0 ? COLORS.grayFill : COLORS.white, COLORS.line);
      text(slide, fmt, 96, y + 12, 150, 22, { size: 15, bold: true, color: COLORS.blue });
      text(slide, kind, 270, y + 12, 160, 22, { size: 14, color: COLORS.ink });
      text(slide, assumption, 470, y + 12, 700, 22, { size: 14, color: COLORS.ink });
      y += 48;
    }
    note(slide, "Unsupported or unregistered formats are not coerced into schemas; registry.py returns abstained with an issue code and raw_binary schema shell.", 124, 592, 1030, 62, COLORS.red);
    notes(slide, "This is the concrete accepted-format list from registry.py. The deck should make clear that Zarr is a directory store, while most formats are single files.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "High-Level Pipeline Overview", "The core path is parser-led; semantic annotation is downstream and optional.", 5);
    arrow(slide, 70, 214, 170, 70, "Raw input\nfile/store", COLORS.red, COLORS.redFill);
    arrow(slide, 252, 214, 182, 70, "detect_format\nsignals", COLORS.blue, COLORS.blueFill);
    arrow(slide, 446, 214, 184, 70, "capability\nregistry", COLORS.teal, COLORS.tealFill);
    arrow(slide, 642, 214, 190, 70, "format-specific\nextractor", COLORS.green, COLORS.greenFill);
    arrow(slide, 844, 214, 182, 70, "validators +\nnormalizers", COLORS.amber, COLORS.amberFill);
    arrow(slide, 1038, 214, 172, 70, "schema\noutput", COLORS.purple, COLORS.purpleFill);
    rect(slide, 165, 352, 950, 98, COLORS.white, COLORS.line, true);
    text(slide, "Canonical output path", 194, 368, 260, 24, { size: 18, bold: true, color: COLORS.teal });
    text(slide, "ExtractionOutcome -> DatasetSchema/FieldSchema/EvidenceRecord -> Unified Schema Envelope claims/evidence/provenance", 194, 402, 850, 28, { size: 18, color: COLORS.ink });
    rect(slide, 310, 500, 660, 78, COLORS.amberFill, COLORS.amber, true);
    text(slide, "Optional downstream semantic augmentation", 330, 514, 600, 24, { size: 17, bold: true, color: COLORS.amber });
    text(slide, "Grounding task -> LLM JSON result -> validation -> merge policy -> semantic_merged artifacts", 330, 546, 600, 20, { size: 14, color: COLORS.ink });
    notes(slide, "Use this slide as the broad map. The key clarification is that the LLM path is not in the canonical extraction spine; it is optional augmentation over deterministic artifacts.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Intake, Detection, and Trust Boundary", "Format decisions use multiple signals and explicitly abstain on conflicts.", 6);
    card(slide, 78, 178, 350, 180, "Validation", "extract_path() checks path existence and resource kind: auto, file, or directory_store. Bad paths and mismatches return failed outcomes.", COLORS.blue, COLORS.blueFill);
    card(slide, 465, 178, 350, 180, "Signals", "detect_format() collects magic bytes, directory markers, explicit hints, suffixes, and delimited text probes.", COLORS.teal, COLORS.tealFill);
    card(slide, 852, 178, 350, 180, "Selection", "Priority: strong magic/directory signal, then hint, suffix, text probe. HDF5 .nc can upgrade to NetCDF when markers are present.", COLORS.green, COLORS.greenFill);
    rect(slide, 118, 438, 1040, 92, COLORS.white, COLORS.red, true);
    text(slide, "Trust boundary", 146, 456, 190, 24, { size: 18, bold: true, color: COLORS.red });
    text(slide, "If strong signals conflict, no parser is selected. _abstention_issue() emits codes such as unknown_conflicting_format_signals, unknown_no_signature, or unknown_no_spec_backed_extractor.", 146, 492, 970, 28, { size: 16, color: COLORS.ink });
    notes(slide, "Mention tests/test_extractor_registry.py: conflicting HDF5 magic and CSV hint abstains; unknown binary returns a raw_binary schema with field_claim_policy set to abstain.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Loading and Parsing by Extractor", "Each registered runner produces DatasetSchema fields with source evidence.", 7);
    card(slide, 58, 176, 280, 134, "CSV", "csv_extractor.py::extract_csv_schema()\nHeaders, sample rows, conservative type inference, leading-zero protection, units from suffixes.", COLORS.blue, COLORS.blueFill);
    card(slide, 358, 176, 280, 134, "HDF5", "hdf5_extractor.py::extract_hdf5_schema()\nTraverses groups/datasets, reads dtype, shape, attrs, and records recoverable extraction_errors.", COLORS.teal, COLORS.tealFill);
    card(slide, 658, 176, 280, 134, "NetCDF/CF", "netcdf_extractor.py::extract_netcdf_schema()\nClassic scipy path or HDF5-backed path; dimensions, variables, attributes, CF coordinates.", COLORS.green, COLORS.greenFill);
    card(slide, 958, 176, 280, 134, "Zarr", "zarr_extractor.py::extract_zarr_schema()\nLocal v2 metadata only; validates .zarray docs, dimensions, CF/Xarray attributes; v3 abstains.", COLORS.amber, COLORS.amberFill);
    card(slide, 58, 362, 280, 134, "Parquet", "parquet_extractor.py::extract_parquet_schema()\nParquet footer + Arrow schema, row groups, encodings, statistics; row_values_not_read.", COLORS.purple, COLORS.purpleFill);
    card(slide, 358, 362, 280, 134, "JSON", "json_extractor.py::extract_json_schema()\n16 MB limit; JSON Schema declarations or bounded observed paths, type sets, missing/null.", COLORS.blue, COLORS.white);
    card(slide, 658, 362, 280, 134, "XML/XSD", "xml_extractor.py::extract_xml_schema()\n16 MB limit; bounded XML path observation or XSD element/attribute declarations.", COLORS.teal, COLORS.white);
    card(slide, 958, 362, 280, 134, "Raw", "registry.py::build_raw_binary_schema()\nNo field claims; preserves byte size/prefix or directory entry count with abstention policy.", COLORS.red, COLORS.redFill);
    text(slide, "All parsers converge on models.py::DatasetSchema, FieldSchema, and EvidenceRecord.", 180, 578, 920, 28, { size: 18, bold: true, color: COLORS.ink, align: "center" });
    notes(slide, "This slide is meant to be a compact catalog. The audience does not need code details for every parser, but the function names and boundaries are concrete.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Preprocessing and Normalization", "The pipeline enriches parser outputs without erasing uncertainty.", 8);
    card(slide, 78, 178, 344, 220, "Temporal Semantics", "temporal_semantics.py::analyze_temporal_semantics()\n\nScores candidates by datetime type, strong names, semantic/logical hints. Selects only when support is strong; ties produce ambiguous_time_axis_candidates.", COLORS.blue, COLORS.blueFill);
    card(slide, 468, 178, 344, 220, "Unit Normalization", "unit_normalization.py::normalize_unit_claim()\n\nMaps known aliases to canonical units and UCUM codes; records evidence_basis such as explicit_metadata, name_pattern, or not_evidence_backed.", COLORS.teal, COLORS.tealFill);
    card(slide, 858, 178, 344, 220, "Dataset Profile", "deterministic_profile.py::attach_dataset_profile()\n\nAdds missingness and identifier quality. Multi-file relationships are deterministic candidates, not asserted joins.", COLORS.green, COLORS.greenFill);
    note(slide, "Normalization adds claim state and reason codes such as supported, derived, unknown, conflicted, sampling_insufficient, and conservative fallback to string.", 126, 480, 1028, 78, COLORS.amber);
    notes(slide, "Describe this as controlled enrichment: the code calculates time grids, unit mappings, missingness, and identifier quality, but it records uncertainty where support is weak.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Extraction Core: How Schema Candidates Are Produced", "The concrete model is layered but stored in explicit dataclasses.", 9);
    rect(slide, 84, 184, 322, 318, COLORS.redFill, COLORS.red, true);
    text(slide, "Raw/untrusted input", 112, 206, 260, 24, { size: 18, bold: true, color: COLORS.red });
    text(slide, "Bytes, text rows, XML/JSON trees, HDF5/NetCDF containers, Parquet footers, Zarr metadata directories.\n\nNot trusted to imply semantics by itself.", 112, 248, 250, 138, { size: 15 });
    rect(slide, 474, 184, 322, 318, COLORS.blueFill, COLORS.blue, true);
    text(slide, "Intermediate representation", 502, 206, 260, 24, { size: 18, bold: true, color: COLORS.blue });
    text(slide, "models.py::FieldSchema\nfield_name, field_path, physical_type, shape, nullable, examples, source_evidence, confidence, uncertainty_reason.\n\nmodels.py::DatasetSchema groups fields + metadata.", 502, 248, 250, 168, { size: 15 });
    rect(slide, 864, 184, 322, 318, COLORS.greenFill, COLORS.green, true);
    text(slide, "Controlled schema", 892, 206, 260, 24, { size: 18, bold: true, color: COLORS.green });
    text(slide, "Logical roles, semantic hints, units, temporal analysis, format-specific analysis, claim states, evidence records.\n\nOnly promoted when the extractor or validator supports the claim.", 892, 248, 250, 154, { size: 15 });
    arrow(slide, 406, 306, 62, 56, "", COLORS.blue, COLORS.blueFill);
    arrow(slide, 796, 306, 62, 56, "", COLORS.green, COLORS.greenFill);
    note(slide, "Final trustworthy output is either the legacy ExtractionOutcome or the versioned unified envelope with claims/evidence/provenance.", 194, 568, 900, 62, COLORS.teal);
    notes(slide, "This fulfills the requested distinction: raw input, intermediate structured representation, controlled schema, and validated output.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Prompt, Model, and Rule Logic", "Canonical extraction is rule/parser based; LLM use is downstream semantic augmentation.", 10);
    card(slide, 78, 180, 346, 236, "Canonical Path", "No prompt is used by extract_path(). Registered extractors use deterministic parsing, bounded sampling, metadata inspection, explicit aliases, and validators.", COLORS.green, COLORS.greenFill);
    card(slide, 468, 180, 346, 236, "Prompt Construction", "build_semantic_grounding.py writes task bundles.\nsemantic_layer.py::build_prompt_payload() includes SYSTEM_RULES, deterministic_schema, grounding snippets, and expected output schema.", COLORS.amber, COLORS.amberFill);
    card(slide, 858, 180, 346, 236, "LLM Runner", "semantic_annotate.py sends compact tasks to chat/completions with strict JSON instructions. It may annotate only listed targets and must cite available evidence IDs.", COLORS.blue, COLORS.blueFill);
    note(slide, "If the mechanism is missing: there is no cryptographic proof, formal proof system, or fully validating XML/XSD/JSON engine. The trust controls are deterministic routing, bounded parsers, validators, tests, issue states, and evidence/provenance records.", 112, 492, 1058, 88, COLORS.red);
    notes(slide, "Be precise: do not imply the LLM is part of the canonical extraction flow. It is a downstream enrichment path guarded by validation and merge rules.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Controlled Vocabulary and Schema Constraints", "The code constrains both outputs and how uncertainty is represented.", 11);
    card(slide, 78, 176, 340, 178, "Allowed Logical Types", "semantic_layer.py::ALLOWED_LOGICAL_TYPES:\nidentifier, time_axis, measurement, coordinate, label, attribute, relationship, unknown.", COLORS.blue, COLORS.blueFill);
    card(slide, 470, 176, 340, 178, "Claim States", "unified_schema.py::CLAIM_STATES:\nobserved, declared, derived, supported, conflicted, unknown, unsupported, abstained.", COLORS.teal, COLORS.tealFill);
    card(slide, 862, 176, 340, 178, "Extractor Capabilities", "registry.py::EXTRACTOR_CAPABILITIES declares extractor_id, version, formats, suffixes, operations, determinism_class, evidence_types, resource_kinds.", COLORS.green, COLORS.greenFill);
    card(slide, 78, 410, 340, 138, "Units", "UNIT_ALIASES maps supported units to canonical names and UCUM-like codes; unmapped units stay explicit rather than normalized falsely.", COLORS.amber, COLORS.amberFill);
    card(slide, 470, 410, 340, 138, "Evidence Tiers", "docs/target_schema.md: explicit_metadata > structural > statistical > llm_inference. Lower-tier evidence may not silently overwrite stronger evidence.", COLORS.purple, COLORS.purpleFill);
    card(slide, 862, 410, 340, 138, "Merge Policy", "merge_annotation_result() rejects unsupported annotations and records logical/semantic/unit conflicts rather than hiding them.", COLORS.red, COLORS.redFill);
    notes(slide, "This slide gathers the major control surfaces: dataclass fields, allowed logical types, claim-state vocabulary, declared extractor capabilities, unit aliases, and merge policy.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Validation and Consistency Loop", "Validation happens during intake, extraction, normalization, envelope projection, and regression tests.", 12);
    arrow(slide, 116, 190, 190, 66, "Input\nvalidation", COLORS.blue, COLORS.blueFill);
    arrow(slide, 328, 190, 190, 66, "Extractor\nvalidation", COLORS.teal, COLORS.tealFill);
    arrow(slide, 540, 190, 190, 66, "Normalizer\nclaims", COLORS.green, COLORS.greenFill);
    arrow(slide, 752, 190, 190, 66, "Envelope\naudit", COLORS.purple, COLORS.purpleFill);
    arrow(slide, 964, 190, 190, 66, "Tests +\nreports", COLORS.amber, COLORS.amberFill);
    rect(slide, 178, 330, 920, 142, COLORS.white, COLORS.line, true);
    text(slide, "Loop behavior", 210, 350, 180, 24, { size: 18, bold: true, color: COLORS.teal });
    text(slide, "Any stage can return success, partial, abstained, or failed. Issues are carried forward instead of being collapsed into a single opaque score.", 210, 386, 860, 28, { size: 17 });
    text(slide, "Examples: dependency_unavailable, parser_error, partial_extraction, sampling_insufficient, declared_observed_type_conflict, unsupported_zarr_version.", 210, 430, 860, 28, { size: 15, color: COLORS.muted });
    card(slide, 126, 538, 310, 78, "Registry Tests", "tests/test_extractor_registry.py", COLORS.blue, COLORS.white);
    card(slide, 486, 538, 310, 78, "Envelope Tests", "tests/test_unified_schema.py", COLORS.purple, COLORS.white);
    card(slide, 846, 538, 310, 78, "Semantic/PROV Tests", "test_semantic_annotate_payload.py; test_provenance_manifest.py", COLORS.green, COLORS.white);
    notes(slide, "Use this as the validation loop diagram. Emphasize that failure modes are first-class statuses and issue codes, not exceptions hidden from users.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Provenance, Traceability, and Auditability", "Every supported claim is expected to point back to concrete evidence.", 13);
    card(slide, 78, 178, 344, 238, "Field-Level Evidence", "Each FieldSchema has source_evidence: EvidenceRecord(tier, evidence_type, source, detail, confidence).\n\nExamples: csv_header, sample_rows, hdf5_attribute, netcdf_variable, zarr_array_metadata.", COLORS.teal, COLORS.tealFill);
    card(slide, 468, 178, 344, 238, "Unified Claim Graph", "build_unified_schema_envelope() deduplicates evidence into e0001... and emits c0001... claims with evidence_refs.\n\nConflicts and abstentions are projected separately.", COLORS.blue, COLORS.blueFill);
    card(slide, 858, 178, 344, 238, "PROV-Like Manifest", "build_provenance_manifest.py creates lightweight_prov_v1 over source files, derived schemas, fields, evidence, semantic annotations, merges, reports, agents, activities, relations.", COLORS.green, COLORS.greenFill);
    note(slide, "Content trust comes from traceability and bounded claim policy, not from a single confidence number. Confidence fields exist, but issue states and evidence links are the stronger control mechanism.", 136, 508, 1008, 74, COLORS.amber);
    notes(slide, "Mention tests/test_unified_schema.py checks that all supported claims have evidence_refs and that evidence IDs resolve.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Final Schema Output Format", "The final output can be consumed as legacy JSON, envelope JSON, or both.", 14);
    card(slide, 70, 176, 360, 266, "Legacy ExtractionOutcome", "status\nformat_decision\nextractor\nschema\nissues\n\nschema contains DatasetSchema fields, groups, metadata, notes.", COLORS.blue, COLORS.blueFill);
    card(slide, 460, 176, 360, 266, "Unified Envelope v1.0.0", "identity\nformat_detection\nextractor_capability\noutcome\nphysical_structure\nlogical_roles\nsemantic_hints\nunits\ntemporal_semantics\nclaims/evidence/provenance", COLORS.teal, COLORS.tealFill);
    card(slide, 850, 176, 360, 266, "Agent Bundle", "agent_export_version\npolicy\nschema_summary\nclaim_records\nevidence_records\nprovenance_graph\nretrieval_context\nrequestable_actions", COLORS.green, COLORS.greenFill);
    text(slide, "CLI examples", 106, 506, 160, 24, { size: 17, bold: true, color: COLORS.ink });
    rect(slide, 106, 538, 1028, 58, COLORS.ink, COLORS.ink, true);
    text(slide, "python -m high_fidelity_schema_study.cli extract --input path/to/file --output-shape both", 130, 555, 980, 22, { size: 18, color: COLORS.white });
    notes(slide, "The legacy schema is still authoritative and unchanged. The envelope is additive, which the tests assert.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Error Handling, Failure Cases, and Limitations", "The code surfaces limits instead of pretending they are solved.", 15);
    card(slide, 58, 172, 280, 170, "Abstentions", "Unknown binary, conflicted strong signals, unregistered formats, Zarr v3, missing Zarr metadata, over-limit JSON/XML can abstain.", COLORS.red, COLORS.redFill);
    card(slide, 358, 172, 280, 170, "Partial / Failed", "Recoverable extraction_errors become partial outcomes. Parser errors and missing dependencies become structured failed outcomes.", COLORS.amber, COLORS.amberFill);
    card(slide, 658, 172, 280, 170, "Bounded Samples", "CSV/JSON/XML profiles are bounded by sample_limit; sample-derived properties are not universal proofs.", COLORS.blue, COLORS.blueFill);
    card(slide, 958, 172, 280, 170, "Metadata Only", "Parquet rows and Zarr chunks are not read; footer stats and metadata are not independently validated against payload values.", COLORS.teal, COLORS.tealFill);
    card(slide, 58, 398, 280, 146, "Format Scope", "NetCDF4 path is conservative; XML/XSD is lightweight; JSON Schema handling is not a full validator.", COLORS.purple, COLORS.purpleFill);
    card(slide, 358, 398, 280, 146, "LLM Scope", "LLM annotations are downstream and may fail, conflict, or remain unknown. They do not create physical fields.", COLORS.green, COLORS.greenFill);
    card(slide, 658, 398, 280, 146, "Evaluation Scope", "Challenge packs show declared-case behavior, not broad ecosystem robustness.", COLORS.amber, COLORS.white);
    card(slide, 958, 398, 280, 146, "Missing Controls", "No cryptographic signing, no formal proof checker, no full external schema/entity loading, no automatic broad compatibility guarantee.", COLORS.red, COLORS.white);
    notes(slide, "This is the limitation slide. Say explicitly that missing controls are missing; this is part of the trust model.");
  }

  {
    const slide = deck.slides.add();
    background(slide);
    title(slide, "Recommended Next Improvements", "Strengthen coverage and trust without weakening the deterministic-first contract.", 16);
    card(slide, 78, 176, 344, 178, "Broader Compatibility", "Expand external/multi-producer validation for Parquet, JSON, XML, NetCDF/CF, and Zarr, with each corpus kept separate from frozen benchmark claims.", COLORS.blue, COLORS.blueFill);
    card(slide, 468, 176, 344, 178, "Stronger Validators", "Add fuller JSON Schema and XML/XSD validation modes behind explicit capability flags; keep observed vs declared claims separate.", COLORS.teal, COLORS.tealFill);
    card(slide, 858, 176, 344, 178, "Payload Verification", "Optionally validate Parquet footer statistics and Zarr chunk-derived properties with bounded payload reads and explicit cost controls.", COLORS.green, COLORS.greenFill);
    card(slide, 78, 410, 344, 138, "Provenance Hardening", "Add artifact hashes, run manifests, version pins, and optional signing for generated schemas and envelopes.", COLORS.purple, COLORS.purpleFill);
    card(slide, 468, 410, 344, 138, "LLM Governance", "Keep LLM augmentation noncanonical by default; improve evidence IDs, prompt regression tests, and conflict dashboards.", COLORS.amber, COLORS.amberFill);
    card(slide, 858, 410, 344, 138, "User-Facing QA", "Expose issue codes, sample limits, abstention reasons, and evidence drill-down more clearly in CLI and GUI outputs.", COLORS.red, COLORS.redFill);
    note(slide, "Do not relax the central rule: unsupported evidence should remain unknown, conflicted, partial, failed, or abstained.", 180, 602, 920, 50, COLORS.teal);
    notes(slide, "End by reinforcing the research posture: the pipeline is already controlled and auditable, and next work should improve coverage and verification rather than convert it into an LLM-first guesser.");
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
