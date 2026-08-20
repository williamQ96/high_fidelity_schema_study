# Semantic architecture paper artifacts

This directory contains English and Chinese LaTeX manuscripts for the
pre-blind semantic architecture study. The English manuscript is the
authoritative 2026-07-27 feedback-integrated version. The Chinese manuscript is
the earlier translation and is not evidence that the new literature,
NDP-50, or feedback-amendment text has been independently translated or
reviewed.

- `semantic_architecture_study_en.tex`: English manuscript
- `semantic_architecture_study_zh.tex`: earlier Chinese translation
- `results_macros.tex`: shared result values and artifact hashes
- `references.bib`: shared bibliography
- `build_papers.ps1`: deterministic local build entry point
- `build/*.pdf`: rendered manuscripts

Neither manuscript reports blind effects. The English manuscript's boxed
blind-freeze provenance section contains explicit placeholders that must be
bound before independent gold is unsealed. The successful Qwen3.6 qualification
is operational evidence only; it is not an architecture-quality result.

Build with:

```powershell
powershell -ExecutionPolicy Bypass -File .\paper\build_papers.ps1
```

The current PDFs were rendered with Tectonic 0.16.9. The build script expects the
cache location used during this development phase but accepts an alternative
executable via `-Tectonic`.
