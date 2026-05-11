# Presentation Narrative Plan

## Audience

High-school-level technical audience. The deck should explain the study without assuming prior knowledge of schemas, HDF5, retrieval metrics, or LLM evaluation.

## Objective

Explain the project in plain language: what problem it solves, why the deterministic-first decision matters, how the method works, what has been built, what the current limits are, and how the work converges.

## Narrative Arc

1. Start with the everyday problem: scientific data files often lack clear labels.
2. Explain the risk of asking an LLM to guess the labels.
3. State the core decision: prove structure first, then ask the LLM to explain only with evidence.
4. Show the pipeline as a simple sequence.
5. Define the key terms used throughout the project.
6. Summarize the work completed so far.
7. Show the current result snapshot, especially retrieval performance.
8. Surface the current limits honestly.
9. End with the convergence path and final research goal.

## Slide List

1. Title: Let AI stop guessing data fields
2. The problem: data files can hide their meaning
3. The decision: parser first, LLM second
4. The method: evidence-grounded schema extraction
5. Key terms: pilot, gold, external, distractor
6. What we have built
7. What the results show now
8. Current limits and fixes
9. How the work converges

## Source Plan

Use the existing project sources:

- `README.md`
- `docs/current_state_report_CN.md`
- `docs/current_state_report_EN.md`
- `data/retrieval/external_candidate_pool/retrieval_report.md`
- `data/semantic_merged/semantic_merge_report.md`

No external web sources are needed.

## Visual System

Use a clean classroom-explainer style:

- off-white paper background
- dark ink text
- teal for deterministic evidence
- amber for LLM semantic interpretation
- red only for limits/blockers
- green only for completed or accepted outputs

Typography:

- Chinese-first deck using `Microsoft YaHei`
- compact, readable, low jargon density

## Editability Plan

All slide text, labels, cards, diagrams, and metric values should remain editable PowerPoint objects. The final deck should be a `.pptx` file, not screenshot slides.

