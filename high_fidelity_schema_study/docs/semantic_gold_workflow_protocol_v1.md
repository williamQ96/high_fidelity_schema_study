# Semantic gold artifact workflow v1

Status: executable calibration workflow; blind corpus not yet sampled

## Trust boundary

Gold is authored by two independent non-developers. Code may validate structure,
hash identity, vocabulary membership, evidence existence, catalog provenance, field
relevance, slot coverage, and agreement arithmetic. Code may not decide whether a
source semantically entails a label and may not adjudicate a disagreement. No model,
agent, judge, or A/B/C/D output participates.

The artifact chain is:

```text
neutral annotation packet + frozen vocabulary + approved source bundle
  -> independent submission A (frozen SHA-256)
  -> independent submission B (frozen SHA-256)
  -> deterministic disagreement worksheet
  -> human resolutions
  -> consensus artifact bound to A, B, and worksheet hashes
  -> blind-manifest preflight
```

## Inputs

- Neutral packet: complete field scope, physical/structural observations, bounded
  examples, and approved evidence; no deterministic logical/semantic/unit prediction,
  confidence, model output, gold path, or absolute source path.
- Vocabulary: frozen physical, logical, semantic, and canonical unit values; unit
  aliases and bounded reference-time patterns; JSON null is the only unknown form.
- Source bundle: content-addressed approved sources and evidence catalog. Each catalog
  item has a stable identity and explicit applicable field paths.
- Handbook: the exact frozen annotation and adjudication rules.

## Independent submission

Each submission records the hashes of all three inputs, a pseudonymous annotator id,
a unique submission id, `model_outputs_visible=false`, and
`developer_participation=false`. Every packet field has four applicability decisions,
four property-level rationales, values, and evidence for each known value.

Validate before revealing the other submission:

```text
python -m high_fidelity_schema_study.semantic_gold_workflow validate-independent \
  --artifact annotator-a.json \
  --packet packet.json \
  --source-bundle source-bundle.json \
  --vocabulary vocabulary.json
```

The coordinator freezes the valid file's SHA-256. Corrections are allowed only before
the other annotation or any disagreement is revealed; every superseded artifact is
retained.

## Disagreement worksheet

Only after both independent validators return `ready`:

```text
python -m high_fidelity_schema_study.semantic_gold_workflow compare \
  --artifact-a annotator-a.json \
  --artifact-b annotator-b.json \
  --packet packet.json \
  --source-bundle source-bundle.json \
  --vocabulary vocabulary.json \
  --output disagreement.json
```

The report computes exact state/value agreement by property and separately reports
evidence-reference agreement. Every difference remains
`pending_human_adjudication`; the command never chooses a label.

## Consensus validation

Human adjudicators fill exactly one resolution and rationale for every disagreement.
Agreed slots remain immutable. The final consensus binds the exact A/B artifact hashes
and disagreement hash, then is validated with:

```text
python -m high_fidelity_schema_study.semantic_gold_workflow validate-consensus \
  --artifact consensus.json \
  --artifact-a annotator-a.json \
  --artifact-b annotator-b.json \
  --disagreement-report disagreement.json \
  --packet packet.json \
  --source-bundle source-bundle.json \
  --vocabulary vocabulary.json
```

Any post-reveal edit, missing resolution, unlogged change to an agreed slot, source
identity mismatch, out-of-vocabulary label, alias unit, or evidence from the wrong
field makes the artifact blocked.

## Calibration versus blind evidence

The checked-in nine-case workflow is explicitly non-blind and previously developed.
It tests annotator instructions, agreement calculations, vocabulary adequacy, and
artifact mechanics only. Its labels, agreement, or timing are not architecture
effects, power evidence, or external-validity evidence.

Corpus-level readiness, preregistration separation, threshold floors, same-pair
identity, and the no-reuse rule for failed rounds are enforced by
`docs/semantic_annotator_calibration_protocol_v1.md` and
`semantic_annotator_calibration.py`.

For blind evaluation, a new vocabulary and source bundles are frozen from the sampled
corpus and approved documentation without inspecting any model output. Independent
files and consensus remain sealed from system developers until protocol, backends,
prompts, execution order, and all other freeze artifacts are immutable.

After unsealing for scoring, gold is loaded only by deterministic evaluator code.
Neither independent annotations, disagreement records, consensus fields, nor any
gold-only marker may enter a B, C, or D model request. The harness has an explicit
sentinel regression test for this boundary. A model-request artifact containing
gold invalidates the affected run rather than permitting selective repair.

The same frozen vocabulary is supplied to the B/C dataset-level request so exact
semantic and unit scoring does not measure unconstrained label spelling. Unit
comparison applies the deterministic product's canonical normalization equally
across variants while retaining raw values in traces. D's historical prompt remains
unchanged; lack of the controlled vocabulary is a documented legacy boundary.
