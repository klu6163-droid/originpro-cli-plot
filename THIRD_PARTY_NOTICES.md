# Third-party components

The 40-route extension includes source code, templates, synthetic examples and selected
reference documentation from **EditaPlot**, https://github.com/hang-jin/editaplot, pinned to commit
`4aa986f3f84da9cb2a2297159a8f20e42b7e527c` (imported 2026-09-02).

Copyright 2026 EditaPlot contributors. Distributed under the Apache License, Version 2.0.
The complete license and upstream notices are preserved in `vendor/editaplot/LICENSE`,
`vendor/editaplot/NOTICE`, and `vendor/editaplot/THIRD_PARTY_NOTICES.md`.

`vendor/editaplot/runtime/` is the upstream runtime. The command-line Python files and the
dependency constraints under `vendor/editaplot/cli/` are relocated from upstream
`skill/editaplot/scripts/`. `references/editaplot/` contains unchanged selected upstream references.
`references/plot-routes.md` is generated from upstream manifests with integration-specific guidance.
`scripts/originpro_routes.py` is the integration adapter; it is separate from the vendored source.

This integration does not distribute OriginLab software or imply affiliation with OriginLab.
The existing native template scripts retain their previous authorship and behavior. The upstream
Apache license covers the imported component and does not purport to relicense the entire original
Skill. Preserve this notice and the upstream license when sharing the updated Skill.

Local modifications (2026-09-02): `runtime/src/origin_sciplot/scientific_workflow.py` freezes the calibration bin-count display scale, and `runtime/src/origin_sciplot/semantic_analysis.py` declares its helper lineage and separates the auxiliary bars from the observed calibration curve. Existing semantic confirmation checks are retained. Original and integration hashes are recorded in `UPSTREAM.json`.

Local environment compatibility fix (2026-09-02): `cli/editaplot_core.py` reads the actual OS architecture using the documented Windows `IsWow64Process2` API when Python reports an empty machine name. Unknown and unsupported architectures are still rejected; Windows token and execution-permission checks are unchanged.

Local Origin 2025 compatibility fix (2026-09-02): `origin_backend/scientific_renderer.py` explicitly sets column border colors to the declared series color before the existing color readback. All verification gates remain enabled.
