# OriginPro build job schema

The build script accepts UTF-8 JSON. Prepare a numeric CSV with one header row and equal-length
columns; independent grids occupy separate X/Y pairs and absent tail rows stay missing.
For new figures use the two presets in [curve-defaults-workflow.md](curve-defaults-workflow.md).
The example below documents the retained legacy format.

```json
{
  "data_csv": "E:/work/prepared.csv",
  "output_opju": "E:/work/output/sample.opju",
  "template_opju": null,
  "qa_png": "E:/work/output/sample.png",
  "overwrite": false,
  "worksheet": {
    "long_name": "XPS Data",
    "sheet_name": "Sheet1",
    "columns": [
      {"field": "Binding Energy", "long_name": "Binding Energy", "units": "eV", "axis": "X"},
      {"field": "Raw", "long_name": "Intensity", "units": "a.u.", "axis": "Y"},
      {"field": "Fit", "long_name": "Fit envelope", "units": "a.u.", "axis": "Y"}
    ]
  },
  "graph": {
    "long_name": "XPS",
    "x_column": 0,
    "series": [
      {"y_column": 1, "role": "raw"},
      {"y_column": 2, "role": "fit"}
    ],
    "x_label": "Binding Energy (eV)",
    "y_label": "Intensity (a.u.)",
    "reverse_x": true,
    "x_from": null,
    "x_to": null,
    "y_from": null,
    "y_to": null,
    "legend": false,
    "style_file": "C:/Users/Admin/.codex/skills/originpro-cli-plot/assets/default_xps_style.json"
  }
}
```

## Rules

- `template_opju` is either `null` or a user-confirmed `.opju`/`.opj` path.
- Column and series indexes are zero-based.
- Each series can supply `x_column`; otherwise it uses `graph.x_column`. The new presets preserve
  each pair's acquisition order. Their peak background-mode and fill-target fields are documented
  in the linked workflow.
- Blank CSV cells become missing values, not zeros.
- With a template, legacy jobs preserve existing plot styling unless a series entry includes
  `color` or `line_width`. Selecting one of the new preset style files explicitly applies that
  preset's presentation to the single graph/layer.
- Without a template, `style_file` is required. Series styles are selected by `role`; supported roles are `raw`, `fit`, `component1` through `component6`, `background`, and `other`.
- `x_from`/`x_to` and `y_from`/`y_to` may be `null` for data-driven ranges. For reversed XPS axes, the automatic X range is maximum to minimum.
- The output must not be the source CSV or template. Existing output requires `overwrite: true` and user authorization.
