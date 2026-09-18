# Workflow for the 40-route extension

Use this workflow for a new figure covered by [plot-routes.md](plot-routes.md).
Use the original `originpro_build.py` workflow for an existing OPJU style template.
The two entry points use different JSON schemas; do not pass a legacy job to the new renderer.

## Implementation and environment

The executable engine, templates, blank data tables and synthetic examples are bundled in
`vendor/editaplot`. No second Skill or separate EditaPlot installation is required. The pinned
upstream commit and per-file hashes are in `vendor/editaplot/UPSTREAM.json`; preserve its Apache-2.0
LICENSE and NOTICE. Do not replace this snapshot with a moving GitHub branch during a plotting task.

Use Windows x64 and a compatible Python 3.10–3.12. Resolve the installed Skill's absolute path
before running its scripts. The following commands assume the Skill is the working directory:

```powershell
python -X utf8 scripts/originpro_routes.py check-install
python -X utf8 scripts/originpro_routes.py catalog
python -X utf8 scripts/originpro_routes.py doctor
```

`doctor` does read-only discovery. Reuse an already suitable local Python; if dependencies are missing,
`doctor --repair` creates an isolated engine environment with the bundled constraints. This is an
explicit dependency operation, not part of every plot. The wrapper subsequently selects that
environment. Do not use the upstream bootstrap installer, which installs a separate EditaPlot Skill.
Do not install or modify Origin as part of this Skill. Origin 2024b is the upstream full validation
baseline; other versions require their current host capability checks. Code availability and upstream
`verified` metadata do not establish a successful render on this computer.

## Inspect, map and confirm

1. Inspect the source read-only, including all relevant workbook sheets. The engine selects the first
   valid table; if that is not the intended sheet, prepare a separate lossless export of the confirmed
   sheet and record its relationship to the source. Never silently substitute another sheet.
2. Run `start` to inspect and recommend candidates. Read the matching section of
   [data-contracts.md](editaplot/data-contracts.md) for the selected route. Use
   [chart-selection.md](editaplot/chart-selection.md) if the evidence needs a different graph.
3. Run `understand` with the chosen template ID. Resolve uncertain columns and pass the same
   `--mapping-json` to both `understand` and `plan` when a mapping is needed.
4. Present the visible elements, retained columns, axes/units, error definitions, permitted display
   calculations and style choice for confirmation. Reuse an already explicit, applicable user choice;
   ask only for remaining scientific ambiguity. A renderer's machine-readable confirmation must
   reflect that actual choice, never fabricated consent.
5. Save the exact `confirmation_payload_template` from the latest understanding response, setting
   `confirmed` to true only after the matching user confirmation. Do not invent proposal hashes or
   manually construct a render plan. New source values or mappings require a fresh understanding.

```powershell
python -X utf8 scripts/originpro_routes.py start "D:/data/table.csv" --output "D:/work/start.json"
python -X utf8 scripts/originpro_routes.py understand "D:/data/table.csv" --template-id bar --output "D:/work/understanding.json"
python -X utf8 scripts/originpro_routes.py plan "D:/data/table.csv" --template-id bar --claim "Compare the supplied groups" --semantic-confirmation-json "D:/work/confirmation.json" --output "D:/work/render-plan.json"
python -X utf8 scripts/originpro_routes.py validate-plan "D:/work/render-plan.json"
```

ROC/PR uses supplied coordinates; it does not calculate AUC from labels and scores. Fitting,
baseline correction, peak assignment and inferential statistics are separate scientific tasks.
Box/violin/histogram and related routes may use explicitly disclosed display summaries or density
objects; confirm those as part of the plot, and preserve original observations. XRD Rietveld reads
existing refinement results; XPS reads supplied curves. Neither route performs a scientific refit.

## Render and verify

Use [delivery-workflow.md](delivery-workflow.md) after plan validation. Both engines now share
source-bound confirmation, saved-project readback, export inspection and visual acceptance.

```powershell
python -X utf8 scripts/originpro_routes.py render "D:/work/render-plan.json" --contract "D:/work/task-confirmed.json" --output-dir "D:/work/new-delivery"
python -X utf8 scripts/originpro_routes.py verify "D:/work/new-delivery"
```

The contract must refer to that exact plan and its current data hash. The upstream renderer still
performs its graph-specific checks; the common worker additionally reopens the saved project and
exports the final verified copy. It always closes its owned instances. Open the final OPJU separately
if the user wants to continue editing. The standard output folder contains `result.opju`, one PNG,
PDF and TIFF per graph page, readback reports, source/confirmation records and hashed manifests.

On `origin_codex_sandbox_context`, request narrowly scoped platform execution approval for the same
command. Do not change user identity, registry, DCOM or runtime checks. All underlying upstream
licenses and pinned-source validation remain in place. The retained upstream references describe
graph-specific semantics; their older render examples must use this shared delivery workflow.

`origin-smoke` remains a synthetic capability probe, not a final scientific-data delivery.
`panel-plan` is a layout plan, not a merged multi-panel OPJU renderer, and is not counted among the
40 routes. A programmatic pass does not replace viewing every final graph.
