# Data and plot decision

Use this guide during the read-only inspection phase. The model, not a filename heuristic, decides the scientific data type and suitable figure.

## Inspection checklist

- Enumerate every sheet and used range; note hidden sheets, formulas, charts, named ranges, units, and acquisition metadata.
- Determine whether rows are observations, ordered measurements, spectra, time points, categories, replicates, or fit results.
- Determine each column role: X, measured Y, fitted envelope, component, background, error, label, group, or metadata.
- Check numeric coverage, missing values, duplicate X values, monotonic direction, sampling interval, outliers, and whether endpoints are sentinels rather than measurements.
- Separate exported per-point curves from peak-parameter tables. A center/FWHM/area table does not prove that original component arrays exist.

## Plot selection cues

- Ordered spectrum or time series: line plot; use a descending X axis only when scientifically conventional, such as XPS binding energy.
- Independent paired observations: scatter plot; add a fitted line only when requested or scientifically justified.
- Replicates or uncertainty: show points plus error bars or intervals; do not collapse replicates silently.
- Multiple comparable spectra: overlay when amplitudes are directly comparable; otherwise propose normalized or vertically offset views and disclose the transformation.
- Peak fits: measured spectrum, total fit, each exported component, and background. Never generate missing components without explicit permission.

## Required confirmation

Present one recommended plan with the detected evidence, series mapping, axes, processing, and unresolved issues. Ask the user whether to proceed with it. In the same message, ask for a reference Origin template path or explicit confirmation to use the named built-in/default style. Wait for the answer before creating the final project.
