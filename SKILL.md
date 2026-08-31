---
name: originpro-cli-plot
description: Inspect scientific spreadsheet or spectral data, propose and confirm the appropriate plot and column roles, then create or update verified OriginPro .opju figures through Origin command-line and Python automation without MCP. Use when the user wants editable Origin projects from Excel, CSV, spectra, fitted components, or a reference Origin template.
---

# OriginPro CLI Plot

Create editable Origin projects with the Origin command line and Python. Never use an Origin MCP for this workflow.

## Non-negotiable gates

1. Inspect the source data read-only before deciding how to plot it. Inspect every relevant sheet, including hidden sheets, formulas, charts, named ranges, headers, units, missingness, X ordering, and whether columns are raw data, total fit, components, background, error bars, categories, or metadata.
2. Use scientific judgment to propose the data type, plot type, column mapping, axis direction/range, series treatment, and any uncertainty. Then ask the user to confirm that plot plan. Do not create the final Origin project before confirmation.
3. Explicitly ask whether the user has a reference `.opju`/`.otp` template. Do not infer one from nearby files. If the user supplies a template, use it only as a style source. If the user declines or has none, use `assets/default_xps_style.json` for XPS/spectral line figures; for another data type, propose a compact default style and include it in the same confirmation.
4. Never overwrite source data or a reference template. Hash a reference before and after the task, work from a copy, and save outputs to a new path unless the user explicitly authorizes overwrite.

The confirmation message must state:

- detected data type and evidence;
- proposed figure and column-to-series mapping;
- axis direction/range and any processing assumptions;
- missing or ambiguous information;
- the template question and the exact default that will be used if none is provided.

Wait for the user's answer. A request to create the figure does not waive these two confirmations.

## Execution workflow

1. Run `scripts/check_origin_environment.py`. Require Windows and local Origin 2021 or later. Read `com_backend_ready`, `cli_backend_candidate`, and `recommended_backend` separately; `automation_session_ready` only establishes the Windows user-session boundary and does not prove that Origin's `-RS` embedded-Python route works. Treat `identity_matches_profile: false` as a user-session boundary: do not repeatedly launch Origin from the Codex sandbox. After the user closes Origin, `--probe-cli` may be used for one temporary no-project probe when backend-specific evidence is useful.
2. Before execution, ask the user to save and close interactive Origin windows. Do not use `op.attach()` or `Origin.ApplicationSI`; they can block on administrator/session boundaries. The build script must own the independent Origin instance it starts.
3. Prepare a clean CSV plus a job JSON after confirmation. Keep measured values unchanged. Do not reconstruct missing component curves unless the user explicitly chooses parameter-based reconstruction; label reconstructed curves as such.
4. Read `references/job-schema.md`, then run `scripts/originpro_build.py --job <job.json> --validate-only`.
5. If `automation_session_ready` is true, run `scripts/originpro_build.py --job <job.json> --execute --backend auto`. Auto mode tries `Origin64.exe -HS -RS` once with a bounded worker-startup watchdog. It falls back to the official `originpro` COM route only when the CLI worker never starts and only after the controller confirms that its owned CLI process has exited. It must not fall back for a job, data, plotting, saving, or verification error. Use explicit `--backend cli` or `--backend com` only when the user or current backend evidence requires it.
6. If `manual_runner_recommended` is true, run `scripts/make_user_runner.py --job <job.json> --output <run_origin_job.cmd> --backend auto`. Repeat `--job` to create one sequential runner for several confirmed figures. Ask the user to save and close Origin, then open the runner's parent folder in File Explorer and double-click the `.cmd`; a chat file link may open it as text rather than execute it. Resume after the runner creates the projects and `origin_run.log`. Do not claim completion before the files exist.
7. If the user supplied a template, copy it into staging and replace only worksheet data, plot membership, labels, and requested ranges. Preserve its graph/page styling unless the confirmed plan says otherwise.
8. If there is no template, read `assets/default_xps_style.json` and apply those fixed parameters for XPS/spectral line figures.
9. Export a QA PNG after Origin exits, then open that exact final PNG with the available local image-viewing tool. File existence or numeric checks alone do not count as visual QA. Inspect axis direction/range, axis titles and units, fonts, line colors and widths, raw/fit/component membership, legend behavior, clipping, excessive whitespace, overlaps, and whether the visual hierarchy matches the confirmed scientific meaning.
10. If visual QA finds a correctable defect, update the job or style, rebuild the project, export a new QA PNG, and open it again. Allow up to three correction-and-reinspection cycles; if a material defect remains, stop and report it instead of claiming completion.
11. Only after the final image passes visual QA, run `scripts/originpro_build.py --job <job.json> --verify-only` with the same explicit backend used for the build, or `--backend auto` when auto mode built it. The generated manual runner performs both build and structural verification when a user-session boundary exists, but the model must still open and inspect the resulting PNG afterward. Check workbook shape, non-empty series counts, plot count, X direction/range, output existence, and reference hash.
12. Report the actual backend, any automatic fallback and its reason, the final `.opju`, the visually inspected QA PNG, structural verification result, source limitations, and whether the style came from a user template or the built-in default.

## Safety and stopping conditions

- Work in an ASCII staging directory when any source, template, or destination path contains non-ASCII characters; copy the verified artifact to its final path only after Origin exits.
- Never close, reset, or alter an Origin instance that the script did not start.
- Auto fallback may terminate only the exact CLI process owned by the current controller. If any Origin process remains afterward, refuse fallback and ask the user to close it manually.
- Refuse a job whose output resolves to the source data or template path.
- Never mark the task complete without opening the final exported QA image and recording a visual pass or a specific unresolved defect.
- If Origin remains open, the current Windows identity cannot access Origin, a confirmation is absent, or project saving/export cannot be verified, stop and explain the blocker instead of claiming completion.

## Resources

- Read `references/data-and-plot-decision.md` while inspecting unfamiliar data or deciding the figure type.
- Read `references/job-schema.md` before building or validating a job JSON.
- Use `assets/default_xps_style.json` only when the user confirms that no template will be supplied for an XPS/spectral line figure.
