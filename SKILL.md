---
name: originpro-cli-plot
description: Create or update editable Origin/OriginPro figures from scientific tables, spectra, existing fit curves, or an Origin template. Includes 40 executable graph routes for spectroscopy, XRD, electrochemistry, error bars, distributions, heatmaps and model evaluation, plus native OPJU style reuse, saved-project font/layer readback, four-format export and source-bound confirmation through local Python and Origin.
---

# OriginPro CLI Plot

Create editable Origin projects with the Origin command line and Python. Never use an Origin MCP for this workflow.

## Choose the execution route

- **Ordinary XY curves or existing peak-fit curves:** use the user's two default styles in
  [references/curve-defaults-workflow.md](references/curve-defaults-workflow.md). Select
  `assets/ordinary_curve_style.json` for unsplit single/multiple curves and
  `assets/peak_deconvolution_style.json` for local FTIR/XPS and other peak-fit displays.
  These defaults are already chosen; do not ask the user to reconfirm fonts/colors or supply
  a template. The presets use the native executor and preserve the scientific data mapping.

- **Existing OPJU template or legacy line job:** use the native `scripts/originpro_build.py`
  workflow below. It retains the original CLI/COM fallback and existing job schema.
- **New figure from a scientific table:** consult [references/plot-routes.md](references/plot-routes.md),
  select one of the 40 bundled public routes, then follow
  [references/multi-route-workflow.md](references/multi-route-workflow.md) using
  `scripts/originpro_routes.py`. This extension includes its executable engine; no separate Skill
  installation is needed. Prefer it for new bar/error, scatter, box/violin/raincloud, heatmap,
  XRD/Rietveld, electrochemistry and ROC/PR figures.
- XPS can use either route: use native mode to preserve a supplied OPJU style; use `xps` or
  `xps_compare` for a new figure with the bundled graph contracts.
- Never send a non-line chart to the legacy executor merely because the model can describe that
  chart. It creates new line plots and targets the first worksheet/graph/layer. Arbitrary complex
  OPJU templates require separate inspection and explicit implementation.
- The 40 routes describe available code. Upstream verification on Origin 2024b is separate from
  current-host smoke, per-figure object readback and visual QA. Do not claim all routes have passed
  locally after only listing the catalog.

## Shared data and confirmation gates

1. Inspect the source data read-only before deciding how to plot it. Inspect every relevant sheet, including hidden sheets, formulas, charts, named ranges, headers, units, missingness, X ordering, and whether columns are raw data, total fit, components, background, error bars, categories, or metadata.
2. Use scientific judgment to propose the data type, plot type, column mapping, axis direction/range, series treatment, and any uncertainty. Then ask the user to confirm that plot plan. Do not create the final Origin project before confirmation.
3. For ordinary and peak-fit curves, apply the user's selected default preset unless this task supplies another style. An additional template question is unnecessary. If a template is supplied, use it as a style source and honor explicit overrides; never infer a template from nearby files. Other chart types use their selected route's documented style. `assets/default_xps_style.json` is retained only for existing legacy jobs.
4. Never overwrite source data or a reference template. Hash a reference before and after the task, work from a copy, and save outputs to a new path unless the user explicitly authorizes overwrite.
5. Render scientific exponents as true Origin rich-text superscripts. Jobs may use readable caret notation such as `cm^-1`, `m^2` or `R^2`; the executor must convert it to Origin `\+(...)` formatting before saving and exporting. Normalize Unicode superscript glyphs to the same form so PDF delivery does not depend on a fallback font. Treat a visible caret in the final graph as a visual-QA failure.

The confirmation message must state:

- detected data type and evidence;
- proposed figure and column-to-series mapping;
- axis direction/range and any processing assumptions;
- missing or ambiguous information;
- the selected preset or supplied template; ask only about unresolved material choices.

Ask for the remaining scientific and style choices. Reuse an explicit choice already given for the same data and scope; do not repeatedly reconfirm it. Resolve missing or ambiguous choices before final rendering.

## Shared execution and delivery

Read [references/delivery-workflow.md](references/delivery-workflow.md) for both backends. Legacy
job JSON and 40-route render plans retain their own schemas. Both render entry points require
`--contract`, a shared task record bound to the actual files and scientific choices.

1. Validate the legacy job or the 40-route plan without launching Origin. Prepare the shared draft,
   including original acquisition files when the plotted table is an export, and record sheet,
   column, unit, error and processing lineage. Keep raw files unchanged.
2. Record the actual applicable user choice with `confirm`; existing consent can be reused. The
   script records evidence, it cannot establish that a person gave consent. Never turn a generated
   confirmation template into a claim of user approval. `test_fixture` is only for synthetic tests.
3. Run the confirmed record through `originpro_delivery.py run`. It uses the chosen backend,
   captures state before saving, opens the saved OPJU in a new owned Origin instance, applies
   explicit presentation overrides, saves a final copy, reopens it, and exports all graph pages.
4. Require `programmatic_pass` for source hashes, saved data, fonts, axis ranges, graph/layer
   membership, geometry, readback of available curve style properties, PDF fonts/text/page size,
   PNG/TIFF physical size and DPI, and TIFF compression. Unsupported optional properties are
   listed; do not describe them as verified. Preserve unrequested template font and geometry.
5. Open every final graph's exact exported PNG and inspect scientific meaning, labels, clipping,
   colorbars, legends, overlaps and whitespace. Only then record the observations with
   `record-visual`. A successful render leaves `complete: false` until this step.
6. Report the editable project, requested exports and delivery manifest. Re-run `verify` if files
   move or change. Never claim all 40 routes were visually tested from representative tests.

Native backend still replaces only the first worksheet/graph/layer. It retains additional layers
and checks their saved state; this does not implement arbitrary multi-layer data remapping. For
new figures use the supported route that matches the data. CLI/COM auto fallback remains bounded
and occurs only if the embedded CLI worker never starts. Run jobs sequentially. Use a platform
approval for the exact command when the desktop user-session boundary requires it; never modify
identity checks or DCOM settings. Owned verification instances close automatically after export.

The additional PDF inspector is installed from `scripts/requirements-delivery.txt` in the private
engine environment, after normal `doctor --repair`. See the linked workflow for commands and
manual desktop-runner support.

## Native backend safety and stopping conditions

- Work in an ASCII staging directory when any source, template, or destination path contains non-ASCII characters; copy the verified artifact to its final path only after Origin exits.
- Never close, reset, or alter an Origin instance that the script did not start.
- Auto fallback may terminate only the exact CLI process owned by the current controller. If any Origin process remains afterward, refuse fallback and ask the user to close it manually.
- Refuse a job whose output resolves to the source data or template path.
- Never mark the task complete without opening each final exported QA image and recording a visual pass. Record specific unresolved defects as failed visual QA.
- If Origin remains open, the current Windows identity cannot access Origin, a confirmation is absent, or project saving/export cannot be verified, stop and explain the blocker instead of claiming completion.

## Resources

- Read `references/data-and-plot-decision.md` while inspecting unfamiliar data or deciding the figure type.
- Read `references/job-schema.md` before building or validating a job JSON.
- Use the two curve presets for new ordinary/peak-fit jobs; `assets/default_xps_style.json` remains a legacy compatibility asset.

- Read `references/plot-routes.md` to select among the 40 bundled graph routes.
- Read `references/multi-route-workflow.md` before using `scripts/originpro_routes.py`.
- Preserve `THIRD_PARTY_NOTICES.md` and the bundled Apache-2.0 license when distributing this extension.
