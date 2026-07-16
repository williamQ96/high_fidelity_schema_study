# Minimal Architecture Compression Experiment

Benchmark roles: `synthetic_development`

**Claim boundary:** development/regression scores do not establish external generalization.

| Variant | Comparable | Coverage | Selective risk | End-to-end value accuracy | Unsupported proposed model claims | Generated calls | Reused upstream calls | Effective calls | Effective model latency ms | Effective run latency ms | Cost USD | Failed cases |
| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | yes | 0.9883 | 0.0118 | 0.9766 | N/A | 0 | 0 | 0 | 0.000 | 2.876 | 0.00000000 | 0 |
| B | no | 0.9883 | 0.0118 | 0.9766 | 0.0000 | 2 | 0 | 2 | 4128.415 | 4131.397 | 0.00000000 | 1 |
| C | no | 0.9883 | 0.0118 | 0.9766 | 0.0000 | 0 | 2 | 2 | 4128.415 | 4131.164 | 0.00000000 | 1 |
| D | no | 1.0000 | 0.0117 | 0.9883 | 0.0000 | 6 | 0 | 6 | 22171.453 | 22176.958 | 0.00000000 | 0 |

## Interpretation constraints

- Confidence is used for risk/coverage ordering only; it is not verification.
- N/A properties are excluded from value-accuracy denominators and reported as a separate false-positive rate.
- C validates evidence identity, field scope, and deterministic conflicts. It does not claim semantic entailment or truth verification.
- D intentionally preserves the historical non-empty-string evidence acceptance behavior.
- Use a frozen, independently annotated blind manifest before making generalization claims.
