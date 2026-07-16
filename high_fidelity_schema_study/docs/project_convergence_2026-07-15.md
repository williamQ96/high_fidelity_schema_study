# Project Convergence Contract

Date: 2026-07-15
Status: active

The project now converges on two separate final deliverables. They share a deterministic substrate but have different success criteria and evidence levels.

## Deliverable 1: deterministic dataset-to-schema product

Input:

- one supported local dataset resource;
- an optional format hint and bounded extraction settings.

Output:

- a deterministic, evidence-grounded schema;
- physical fields, paths, hierarchy, dtypes, shapes, and explicit metadata;
- deterministic logical, semantic, unit, and temporal claims when supported;
- evidence, provenance, uncertainty, conflict, partial, abstained, or failed states.

The canonical API remains `extract_path(ExtractionRequest(...))`; the canonical CLI remains `python -m high_fidelity_schema_study.cli extract <path>`. This product does not require a model. A semantic model must never create physical fields or silently replace explicit deterministic metadata.

Product convergence means that supported inputs produce reproducible schemas, unsupported inputs produce structured abstention/failure, and the output remains independently useful even if the semantic architecture study finds no model benefit.

## Deliverable 2: semantic architecture research study

The research input is the frozen deterministic observation/task bundle, not an unconstrained raw-file prompt. The architecture remains exactly:

- A: deterministic only;
- B: deterministic plus at most one dataset-level semantic response;
- C: exact B-response replay plus deterministic identity, relevance, and conflict verification;
- D: historical per-field/manual-group scheduler and merge behavior.

The study asks:

> On independently annotated blind scientific datasets, what causal contribution do dataset-level semantic reasoning and deterministic verification make to verified claim coverage, selective risk, unsupported claim rate, and resource cost?

Retrieval, new extractor formats, GUI work, agent orchestration, and time-axis research are outside this study. The frozen Artifact Paper and Phases 12-20 remain historical engineering/artifact evidence; they are not promoted into blind research evidence.

## Shared trust boundary

```text
dataset
  -> deterministic extraction product
  -> immutable observation/task bundle
  -> optional A/B/C/D semantic study
  -> claim-level evaluation against sealed independent gold
```

The product may ship without the study. The study cannot bypass the product's physical-schema boundary.

## Stop rules

The project does not add new architecture variants to rescue a result. It converges by accepting one of four outcomes:

1. B adds useful semantic coverage at bounded risk;
2. C reduces risk at an acceptable coverage cost;
3. D retains a measurable advantage that justifies its extra complexity;
4. deterministic-only extraction is sufficient, or current semantic backends add no reliable value.

Any of these is a valid final result. Missing gold coverage, replay failure, contract-invalid output, or underpowered semantic opportunities block the affected comparison rather than trigger post-hoc redesign.

## Current convergence ledger

Code-complete and locally validated:

- exactly four architecture variants, including byte-identical B/C response replay;
- evaluator invariants, controlled vocabulary, evidence verification, and
  dataset-level paired comparison rows;
- two-annotator independent annotation, disagreement, consensus, and calibration
  gate hash chain;
- non-blind backend operational qualification and registry preflight;
- calibration-derived power calculation with frozen dataset-level assumptions;
- a blind-only inference boundary with a pre-execution analysis plan and a
  post-run, exactly recalculable Holm/paired-t/sign-flip/bootstrap artifact.
- a pre-call blind execution guard binding the manifest's registry hash, selected
  backend record, model identifier, endpoint, and decoding configuration into
  every report; gold-only content is regression-tested never to enter a model
  request.
- a bounded blind candidate-frame and sampling chain that excludes every known
  non-blind resource by byte hash when bytes exist and by stable source identity
  otherwise, freezes frame scope and eligibility rules, requires an externally
  registered powered stratum design, and deterministically binds case order into
  the blind manifest without inspecting model output or gold;
- a checked-in, self-validating pre-frame exclusion registry with 25 system-visible
  records: nine internal byte hashes and 16 historical external identities whose
  original bytes are not present in the workspace. Missing hashes are explicitly
  absent rather than reconstructed from URLs, sizes, or task derivatives.
- an executable acquisition-log boundary that binds enumerator code and raw API
  pages, rejects page gaps and non-reproducible counts, retains exclusions and
  download failures, and requires the candidate frame to cover every acquired
  resource exactly once.

The blind inference plan is specified in
`docs/semantic_blind_inference_protocol_v1.md`. It is frozen separately from the
post-run manifest to avoid the impossible requirement that a pre-execution plan
already contain hashes of future outcome reports.

External work that remains before protocol freeze:

1. register the existing round-1 annotator-calibration design hash in an
   append-only external record before annotation starts;
2. have the two non-developer annotators independently complete the registered
   nine-case round and pass the preregistered gate;
3. qualify the exact local GLM5.2, Qwen3.6, and Llama 3.3 quantized checkpoints on
   the fixed non-blind operational manifest;
4. freeze the eligible backend registry and designate the primary backend without
   using architecture accuracy to choose it;
5. derive and freeze the final power artifact; acquire and enumerate the bounded
   blind candidate frame; externally register and execute its sampling design;
6. freeze the selected blind corpus, blind vocabulary, gold hash chain, and blind
   analysis plan;
7. pass final preflight before any blind A/B/C/D outcome is inspected.

The existing Qwen3.5-35B one-case run is an infrastructure smoke only. It is not a
candidate qualification, power input, or architecture result. No annotator
receipt, completed human calibration, candidate backend qualification, frozen
blind corpus, or blind result currently exists; none may be simulated to make the
project appear complete.
