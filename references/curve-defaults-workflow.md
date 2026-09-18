# Default curve styles

The user supplied two Markdown specifications on 2026-09-02 to fix the defaults.
Their defaults are already selected; do not ask the user to select Arial, a palette,
or a template again. A later explicit request overrides these defaults.

| Figure | Read | Native `graph.style_file` |
| --- | --- | --- |
| Existing peak-fit curves, including local FTIR and XPS | [Peak specification](peak-deconvolution-style.md) | `assets/peak_deconvolution_style.json` |
| One or multiple ordinary XY curves, including spectra | [Ordinary specification](ordinary-curve-style.md) | `assets/ordinary_curve_style.json` |

Use an absolute path to the selected asset in the job. The ordinary source remains
version 0.2 with provisional entries; the user supplied it as the current default.
Those entries are editable defaults, not unanswered questions. Preserve both supplied
Markdown documents as source references, including their measured/unconfirmed distinctions.

These presets implement one native graph/layer. They do not flatten specialized error-bar,
box, heatmap, ROC, Rietveld or other 40-route structures into a plain curve. Use those
routes' own scientific structures. For complex templates or uncertainty objects, inspect
and implement the required mapping separately; do not silently omit them.

## Job mapping

Continue to use the existing native job schema and shared delivery record. Axis labels
are required and must use the actual units. Set `graph.spectrum_type` to `xps` to default
to decreasing binding energy; explicit `reverse_x`, ranges and scale settings override it.
For FTIR and other curves retain a known source direction or the user's choice; ordinary
XY otherwise increases left to right. No automatic normalization, smoothing, fitting,
offset or sorting occurs. For log10 supply `x_scale`/`y_scale: "log10"`; data must be positive.

Use ordinary scientific caret notation in job text when an exponent is needed, for example
`cm^-1`, `m^2`, `R^2`, `cm^{-2}` or `x^(n+1)`. Before Origin saves or exports the graph, the
renderer converts these expressions to Origin rich text (`cm\+(-1)`, etc.), so the exponent is
visually superscripted. Unicode superscript glyphs such as `⁻¹` are normalized to the same rich
text form to avoid fallback-font problems in PDF export. Existing Origin escape sequences remain
unchanged. Final saved-state readback and visual QA must confirm the formatted title; do not leave
the caret visible in the delivered graph.

Each series accepts `x_column` to override the graph's common X. Keep different grids as
separate columns; pad absent tail rows with missing cells, never interpolate just to align
their lengths. `name` gives the real sample/peak label. Optional `color`, `line_width`
(points) and `line_style` override appearance. `show_y_tick_labels` and `legend` can override
the preset. For other stylistic changes copy the JSON asset into the task and bind that copy.

An ordinary series is `{"y_column": 1, "name": "Sample A", "role": "sample"}`.
Single ordinary curves use dark gray and hide the legend. Multiple curves use the seven
specified colors and a 22 pt Arial legend; no fill. Keep existing batch color mappings.
If the palette is exhausted, provide distinct explicit colors or line styles; no cycling.

For peak curves use `raw`, `fit`, `component` (or `component1`, etc.) and `background` roles.
Keep only real curves. Each component must specify `fill_to_y_column`, pointing to the
target background, and `graph.component_mode` must be declared:

- `includes_background`: plotted components are `P_i = S_i + B`. Include the true target
  background as a scientific `background` series. The numerical relationship is
  `F = sum(P_i) - (N-1)B`.
- `baseline_subtracted`: all curves are explicitly background-subtracted. Supply a
  documented zero display-baseline column as the fill target; it is not a fitted background.

For net components with nonzero background, first create *additional* display columns
`P_i = S_i + B` in a new staging table, preserving the source/net columns, missing cells
and their X grid. Include that formula, column lineage and the actual original files in
the task record. Then select `includes_background`. Never add the background twice.
If processing state is unknown, resolve that scientific ambiguity before final rendering.

The adapter reports the supplied sum residual. An optional `fit_tolerance` object with
`atol` and `rtol` enforces a tolerance justified by the target precision; no reference-file
tolerance is copied. This check does not establish correct chemistry or a successful fit.

Gradient filling currently requires each component and its baseline to share the exact X
column on a monotonic grid. Different raw/fit grids are supported independently. For
independent component/baseline grids, use a separately verified renderer, preserving the
original arrays; the preset rejects this case rather than resampling it.

## Saved style and delivery

The executor applies the shared 279.4 x 215.9 mm canvas, 18/10/68/72 percent layer,
Arial 32/26 pt titles/ticks, 3 pt curves and axes, and outward ticks. All four borders
are actual axes. It explicitly disables connecting across missing values.

Each filled component is followed by an auxiliary *plot referencing the same background
column*. Its line is disabled. Fill-to-next is therefore unambiguous after adding/removing
components; auxiliary plots are counted separately and excluded from legends. All components,
including component 4, have two-color fills to white. Scientific curve order remains
Raw, Fit, Components, Background; helpers are inserted only for fill pairing.

`curve-style-report.json` records curve mappings, required style values, numerical sum
residuals and implementation choices. Saved-state validation checks those values and the
helper/background dataset bindings after reopening. Unknown reference gradient direction
and endpoint opacity are not claimed as measured; new graphs inherit native gradient
defaults and must pass visual review. The first candidate legend position is chosen by
data occupancy, but the final preview remains the authority for overlap and clipping.

Continue the four-format delivery: OPJU, physical-size/DPI PNG and TIFF, and embedded-font
PDF. The 1800 px PNG specified by the documents is also generated as a layout preview;
the final full-resolution PNG remains the authoritative visual review artifact.
The style JSON and supplied Markdown specification hashes are bound to the task record.
Style overrides can reuse unchanged scientific consent; changes to data, mapping, background
mode, display formulas or sources invalidate that consent. Generic delivery-profile overrides
are applied after the preset and are recorded explicitly.

The preset reconstructs the curves from the documented style parameters. A supplied template
can provide its page context, but unmeasured gradient internals are not guaranteed to transfer
when plots are recreated. If exact inheritance of those native internals is required, use a
separately inspected template-preservation mapping rather than claim an exact reconstruction.
Use `--backend com` on hosts where the embedded CLI worker does not start; the existing bounded
`auto` fallback remains available and performs the same saved-state/export verification.

References for the adapter: [line settings and width units](https://docs.originlab.com/labtalk/ref/options_for_lines/),
[fill target modes](https://docs.originlab.com/labtalk/ref/options_for_other_options/),
[two-color gradients](https://docs.originlab.com/labtalk/ref/options_for_bar_and_column_plots/),
[axis properties](https://docs.originlab.com/labtalk/ref/layer-axis-obj/).
