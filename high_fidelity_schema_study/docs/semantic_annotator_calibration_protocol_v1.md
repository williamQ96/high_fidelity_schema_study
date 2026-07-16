# Two-annotator calibration gate protocol v1

Status: executable gate complete; human submissions pending
Scope: semantic gold annotation only; no architecture outcomes

## Purpose

Before blind annotation, the same two non-developer annotators must demonstrate
that they can apply one frozen handbook and vocabulary consistently across the
nine non-blind calibration datasets. This gate evaluates annotation-process
readiness. It is not an A/B/C/D result, a measure of external validity, or an
automatic adjudicator.

## Temporal separation

The workflow uses three separate artifacts:

1. A `semantic-annotator-calibration-design/v1` file contains the workflow hash,
   case set, and agreement thresholds. It is frozen before either submission.
2. An auditable registration receipt binds the exact design SHA-256 and states
   that registration preceded the first submission.
3. A completed round manifest is created only after both independent submissions
   and deterministic disagreement reports are frozen by hash.

Putting thresholds and observed submission hashes in one file is prohibited:
such a file cannot prove that the thresholds preceded the outcomes. The local
validator proves content identity but cannot independently prove an external
timestamp; the registration system and receipt remain an explicit human/external
trust boundary.

## Fixed minimum gate policy

The design may choose stricter values, but cannot go below:

| Check | Protocol floor |
| --- | ---: |
| Calibration cases | 9 |
| Overall exact state/value agreement | 0.80 |
| Applicability agreement | 0.90 |
| Exact state/value agreement per property | 0.70 |
| Exact state/value agreement for every case | 0.50 |

These are conservative operational readiness floors, not universal claims that
0.80 is a scientifically privileged reliability constant. The paper must report
the full observed rates and disagreement taxonomy, not only pass/fail.

Exact evidence-ID agreement is descriptive. Two valid annotators may cite
different approved evidence for the same label, so evidence identity cannot
automatically decide label correctness or consensus.

## Executable checks

`semantic_annotator_calibration.py` verifies that:

- all nine workflow cases appear exactly once and in frozen order;
- every packet, source bundle, vocabulary, handbook, implementation, annotation,
  disagreement report, design, receipt, and prior-round summary matches its hash;
- every independent artifact passes the model-visibility, developer-participation,
  vocabulary, applicability, rationale, and evidence constraints;
- every disagreement report is exactly regenerated from the two originals;
- the same two annotator IDs complete every case;
- the receipt binds the exact preregistered design hash;
- every threshold meets the protocol floor;
- a later round follows a failed immediately prior round and reuses none of its
  revealed case IDs.

The program computes agreement and gate status only. It does not resolve a label,
choose evidence, modify an annotation, or create consensus.

Before requesting an external registration or giving packets to annotators, run
the receipt-free design preflight:

```bash
python -m high_fidelity_schema_study.semantic_annotator_calibration preflight-design \
  --design path/to/annotator-calibration-design.json
```

The command validates the design schema, protocol floors, workflow and file hash
chain, case identity/count, and any prior-round no-reuse rule. Its
`ready_for_external_registration` status is not a registration receipt and does
not authorize submissions; it only prevents discovering a malformed design after
human work has begun.

```bash
python -m high_fidelity_schema_study.semantic_annotator_calibration build \
  --round-manifest path/to/completed-calibration-round.json \
  --output path/to/calibration-summary.json

python -m high_fidelity_schema_study.semantic_annotator_calibration validate \
  --artifact path/to/calibration-summary.json
```

## Pass and failure behavior

A passing summary qualifies exactly the two recorded annotator IDs, handbook hash,
and vocabulary hash. Blind preflight requires all three identities to match the
blind annotation artifacts. Changing any of them invalidates the gate.

If a round fails, the team may revise the handbook or vocabulary, but confirmation
requires a newly preregistered workflow with entirely new calibration cases. The
revealed failed cases may be used diagnostically but cannot be recycled as an
unbiased confirmation gate. No model, LLM judge, or automatic adjudication pass is
introduced.
