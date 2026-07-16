# Semantic blind sampling v1

This directory contains pre-outcome corpus-construction artifacts. It contains no
blind gold, model output, or A/B/C/D result.

`known_nonblind_resources.json` is the builder-generated exclusion registry frozen
before candidate-frame construction. It is derived from the complete
`data/semantic_grounding/manifest.json` and validates to:

- 25 system-visible file-level source identities mechanically derived with
  `canonical_source_tuple_sha256/v1`;
- nine byte-level resource SHA-256 values for retained internal resources;
- 16 explicit external-byte absence records, protected by source identity;
- 25 content-hashed grounding tasks retained as provenance, not resource-hash
  substitutes;
- the exact registry-generator implementation hash, so implementation drift
  invalidates the artifact rather than silently changing exclusion semantics.

Artifact SHA-256:
`9c969a7a2aad0cca87613bd510152ef600ac8fc455d804aaa442c844b92edc4e`.

The candidate frame, registered sampling design/receipt, and deterministic
selection artifact do not yet exist. Their absence is a real pending external-data
gate, not a validator failure and not permission to hand-select blind cases.
