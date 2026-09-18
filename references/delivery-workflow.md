# Shared delivery workflow

Both the native template executor and the 40-route engine use this workflow. Resolve the installed
skill path; examples assume it is the working directory. The agent prepares files from the user's
natural-language choices. The user does not need to hand-write JSON.

## Runtime and inputs

Reuse the private environment created by `originpro_routes.py doctor --repair`. Install the extra
PDF inspector once, or after repairing that environment:

```powershell
vendor/editaplot/runtime/.editaplot-venv/Scripts/python.exe -m pip install -r scripts/requirements-delivery.txt
```

No system Python or PATH changes are required. The installed entry points select the private
interpreter. On a machine without a repaired environment, explicitly use a suitable interpreter.
`run` checks dependencies, record hashes and bundled-engine integrity before launching Origin.

Use the existing native [job schema](job-schema.md) or a validated 40-route render plan. Include
column units, selected sheet, errors and processing definitions in that job/plan and, where necessary,
a provenance JSON. When a CSV was exported from XLS/XLSX or acquisition data, bind both with
`--source original.xlsx`; repeat `--source` for additional original files. The primary plotted file
is automatically included. Hashes establish byte identity, not scientific authenticity.

## Prepare and record applicable confirmation

```powershell
python -X utf8 scripts/originpro_delivery.py prepare --backend native --input "D:/work/job.json" --source "D:/data/original.xlsx" --provenance "D:/work/provenance.json" --profile "D:/work/presentation.json" --output "D:/work/task-draft.json"
python -X utf8 scripts/originpro_delivery.py confirm "D:/work/task-draft.json" --statement "ACTUAL APPLICABLE USER CHOICE" --context "Conversation/turn and the reviewed data mapping" --output "D:/work/task-confirmed.json"
python -X utf8 scripts/originpro_delivery.py validate "D:/work/task-confirmed.json"
```

For the route engine use `--backend routes --input render-plan.json`; its upstream semantic
confirmation remains required. Recording that same existing choice in the shared record is not
a second approval request. Do not invent confirmation text or treat a generated payload as consent.
`--kind test_fixture` labels synthetic technical tests explicitly and must not be used for real data.
Do not treat approval of a software update as approval of a future scientific data interpretation.

The record binds source/job/template/style bytes, scientific choices, provenance, presentation,
adapter code and pinned upstream version. Execution rechecks bound files before and after rendering
and after export. Saved worksheet/matrix data and plot bindings are independently hashed/read back.
Draft and confirmed records use separate new paths and are never silently overwritten.

Changes to data, units, mapping, errors, axis/data selection or processing need an applicable updated
scientific confirmation. Pure appearance changes can reuse the previous one:
An OPJU template can retain additional layers and their data, so changing the template file itself
invalidates scientific reuse conservatively. Put font/color/DPI adjustments in presentation settings
to reuse confirmed data without replacing the template. Native execution reads hashed staging copies.

```powershell
python -X utf8 scripts/originpro_delivery.py prepare --backend native --input "D:/work/job-v2.json" --profile "D:/work/presentation-v2.json" --reuse "D:/work/task-confirmed.json" --output "D:/work/task-v2.json"
```

Supply the same original sources and provenance when reusing. A different scientific digest is
rejected. An engine update requires preparing a fresh task record but may reuse unchanged data
confirmation. Review preserves the original engine identity in the delivery record.

## Presentation settings

Optional JSON (omit unspecified settings to retain the renderer/template values):

```json
{
  "dpi": 600,
  "tiff_compression": "LZW",
  "page_width_mm": 160,
  "page_height_mm": 120,
  "font_family": "Arial",
  "font_size_pt": 11,
  "expected": {"g1/layer_count": 2}
}
```

Supported DPI is 300 or 600. TIFF supports LZW, PackBits or None. Both physical page dimensions
must be supplied together. A font override applies to axis ticks, ordinary text and the supported
matrix-cell/color-scale objects; explicit inline font escapes and unusual object classes still need
visual inspection. `expected` adds property assertions using paths from `saved-state.json`, such as
`g1/l2/axis/y2/label.font`. It does not issue arbitrary LabTalk commands.

Required formats are OPJU, PNG, PDF and TIFF. PDF text extraction, embedded fonts and a check against
raster-only output are required by default. For a scientifically justified image-only figure, set
`pdf_text_required: false`, `pdf_embedded_fonts_required: false` and `allow_full_page_raster: true`
explicitly; record that choice. Mixed image/vector figures need visual review even when these checks
pass. A DPI or size change must be reviewed for clipping; it does not change scientific data consent.

## Execute, inspect and finish

```powershell
python -X utf8 scripts/originpro_delivery.py run "D:/work/task-confirmed.json" --output-dir "D:/work/new-delivery" --backend auto
python -X utf8 scripts/originpro_delivery.py verify "D:/work/new-delivery"
```

`--backend` chooses the native CLI/COM path only. Use current machine evidence to select COM when
the embedded CLI is unavailable; auto falls back only if its owned CLI worker never starts. The
old entry points also accept `--contract`, so existing job and plan schemas remain usable:

```powershell
python -X utf8 scripts/originpro_build.py --job "D:/work/job.json" --execute --contract "D:/work/task-confirmed.json" --delivery-dir "D:/work/new-delivery" --backend com
python -X utf8 scripts/originpro_routes.py render "D:/work/render-plan.json" --contract "D:/work/route-confirmed.json" --output-dir "D:/work/new-route-delivery"
```

The delivery directory must be new. Rendering creates `before-save.json`; an independent owned
Origin session reopens the saved OPJU and compares actual state with that snapshot. Presentation
overrides have their own expected/actual checks, and the final saved copy is reopened again before
export. Native templates additionally preserve unrequested font and layer geometry. All graph pages
are read and exported; native data replacement still targets only the first worksheet/graph/layer.

Files include `result.opju`, `result.png/.pdf/.tif` (additional pages use `result_graph2.*`),
`saved-state.json`, `readback-report.json`, `export-report.json`, `task-record.json` and
`delivery-manifest.json`. Native output paths and `qa_png` are compatibility copies written after
programmatic checks pass. Original data/template and previously created evidence remain untouched.
Upstream initial exports, when present in `engine/`, precede common presentation adjustments; final
deliverables are the root `result*` files listed in the manifest.

Readback reports have per-property expected, actual, tolerance and pass. They cover fonts/sizes,
axes, graph/layer counts, geometry, plot data bindings and supported line/fill properties; unsupported
optional properties are listed explicitly. PDF inspection parses page size, fonts and text; raster
inspection reads actual pixels, DPI and TIFF compression. A missing/changed required artifact fails
verification. The original `--verify-only` remains a limited legacy structural probe, not final delivery.

Open every final graph's exact PNG with the image-viewing tool. Check axes/units, labels, legends,
color scales, raw/fit membership, clipping and overlaps. After inspection:

```powershell
python -X utf8 scripts/originpro_delivery.py record-visual "D:/work/new-delivery" --reviewer "Codex, actual image inspection" --notes "Record actual observations for every graph here" --result pass
```

Use `--result fail` for defects and revise the presentation before regenerating a new delivery.
Visual acceptance is bound to the hashed manifest, so changed outputs cannot reuse it. Until visual
acceptance, `programmatic_pass: true` is possible but `complete` remains false. Hash verification
does not replace viewing the image or evaluating the science.

If execution must run in the desktop session, `make_user_runner.py` accepts one `--contract` per
`--job`, in matching order. It builds sequentially and keeps the same confirmation gates. A platform
approval may also run the exact command when authorized; never change identity/COM security checks.

## API references

Origin's documented [axis label properties](https://docs.originlab.com/labtalk/ref/layer-axis-label-obj/),
[dataset range substitutions](https://docs.originlab.com/labtalk/ref/options-substitution-notation/),
and [export tree parameters](https://docs.originlab.com/x-function/ref/details-of-treenodes-in-export-graph/)
underlie these checks. Local Origin 2025 behavior is tested separately from upstream route availability.
