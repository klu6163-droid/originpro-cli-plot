#!/usr/bin/env python3
"""Build and verify an editable OriginPro project from a confirmed JSON job."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


class JobError(RuntimeError):
    """Raised when a job is unsafe or internally inconsistent."""


class BackendUnavailable(JobError):
    """Raised when an automation backend never starts the requested worker."""


def progress(stage: str) -> None:
    print(json.dumps({"stage": stage}, ensure_ascii=False), file=sys.stderr, flush=True)


def resolved_path(value: str | None, base: Path) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve(strict=False)


def same_path(left: Path | None, right: Path | None) -> bool:
    if left is None or right is None:
        return False
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def running_origin_processes() -> list[str]:
    if os.name != "nt":
        return []
    completed = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Origin64.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    rows = []
    for line in completed.stdout.splitlines():
        if "Origin64.exe" in line:
            rows.append(line.strip())
    return rows


def find_origin_executable(explicit: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(Path(r"D:\Program Files\OriginLab\Origin2025\Origin64.exe"))
    for env_name in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        root = os.environ.get(env_name)
        if root:
            candidates.extend((Path(root) / "OriginLab").glob("Origin*/Origin64.exe"))
            candidates.extend((Path(root) / "OriginLab").glob("Origin*/Origin.exe"))
    existing = [candidate.resolve() for candidate in candidates if candidate.is_file()]
    if not existing:
        raise JobError("Cannot find Origin executable; pass --origin-exe with the exact path")
    return sorted(set(existing), key=lambda item: str(item), reverse=True)[0]


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise JobError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise JobError("The job JSON root must be an object")
    return value


def parse_float(cell: str, row_number: int, field: str) -> float:
    text = cell.strip()
    if text == "":
        return math.nan
    try:
        return float(text)
    except ValueError as exc:
        raise JobError(f"Non-numeric value at CSV row {row_number}, column {field!r}: {text!r}") from exc


def read_numeric_csv(path: Path, fields: list[str]) -> tuple[dict[str, list[float]], int]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise JobError("CSV has no header row")
            missing = [field for field in fields if field not in reader.fieldnames]
            if missing:
                raise JobError(f"CSV is missing fields: {missing}")
            columns = {field: [] for field in fields}
            count = 0
            for row_number, row in enumerate(reader, start=2):
                count += 1
                for field in fields:
                    columns[field].append(parse_float(row.get(field, ""), row_number, field))
    except OSError as exc:
        raise JobError(f"Cannot read CSV {path}: {exc}") from exc
    if count == 0:
        raise JobError("CSV contains no data rows")
    return columns, count


def validate_job(job_path: Path, require_output: bool = False) -> dict[str, Any]:
    raw = load_json(job_path)
    base = job_path.parent
    for key in ("data_csv", "output_opju", "worksheet", "graph"):
        if key not in raw:
            raise JobError(f"Missing required job key: {key}")

    data_csv = resolved_path(raw["data_csv"], base)
    output_opju = resolved_path(raw["output_opju"], base)
    template_opju = resolved_path(raw.get("template_opju"), base)
    qa_png = resolved_path(raw.get("qa_png"), base)
    if data_csv is None or output_opju is None:
        raise JobError("data_csv and output_opju must be paths")
    if not data_csv.is_file():
        raise JobError(f"Source CSV does not exist: {data_csv}")
    if template_opju is not None and not template_opju.is_file():
        raise JobError(f"Reference template does not exist: {template_opju}")
    if output_opju.suffix.lower() not in {".opju", ".opj"}:
        raise JobError("output_opju must end with .opju or .opj")
    if qa_png is not None and qa_png.suffix.lower() != ".png":
        raise JobError("qa_png must end with .png")
    if same_path(output_opju, data_csv) or same_path(output_opju, template_opju):
        raise JobError("Output must not be the source CSV or reference template")
    if require_output and not output_opju.is_file():
        raise JobError(f"Output project does not exist: {output_opju}")
    if not require_output and output_opju.exists() and not bool(raw.get("overwrite", False)):
        raise JobError("Output already exists; overwrite must be explicitly true")

    worksheet = raw["worksheet"]
    graph = raw["graph"]
    if not isinstance(worksheet, dict) or not isinstance(graph, dict):
        raise JobError("worksheet and graph must be objects")
    descriptors = worksheet.get("columns")
    if not isinstance(descriptors, list) or len(descriptors) < 2:
        raise JobError("worksheet.columns must contain at least two columns")
    fields: list[str] = []
    for index, descriptor in enumerate(descriptors):
        if not isinstance(descriptor, dict) or not descriptor.get("field"):
            raise JobError(f"worksheet.columns[{index}] must define field")
        fields.append(str(descriptor["field"]))
    if len(set(fields)) != len(fields):
        raise JobError("worksheet column fields must be unique")

    x_column = graph.get("x_column")
    series = graph.get("series")
    if not isinstance(x_column, int) or not 0 <= x_column < len(fields):
        raise JobError("graph.x_column is outside worksheet.columns")
    if not isinstance(series, list) or not series:
        raise JobError("graph.series must contain at least one plotted series")
    for index, entry in enumerate(series):
        if not isinstance(entry, dict) or not isinstance(entry.get("y_column"), int):
            raise JobError(f"graph.series[{index}].y_column must be an integer")
        if not 0 <= entry["y_column"] < len(fields):
            raise JobError(f"graph.series[{index}].y_column is outside worksheet.columns")
        if entry["y_column"] == x_column:
            raise JobError(f"graph.series[{index}] cannot use the X column as Y")

    style_file = resolved_path(graph.get("style_file"), base)
    if template_opju is None:
        if style_file is None or not style_file.is_file():
            raise JobError("A valid graph.style_file is required when no template is supplied")

    columns, row_count = read_numeric_csv(data_csv, fields)
    x_values = [value for value in columns[fields[x_column]] if math.isfinite(value)]
    if len(x_values) < 2:
        raise JobError("X column has fewer than two finite values")
    for index, entry in enumerate(series):
        values = [value for value in columns[fields[entry["y_column"]]] if math.isfinite(value)]
        if not values:
            raise JobError(f"graph.series[{index}] has no finite Y values")

    normalized = dict(raw)
    normalized.update(
        {
            "_job_path": str(job_path),
            "_data_csv": data_csv,
            "_output_opju": output_opju,
            "_template_opju": template_opju,
            "_qa_png": qa_png,
            "_style_file": style_file,
            "_fields": fields,
            "_columns": columns,
            "_row_count": row_count,
        }
    )
    return normalized


def finite_extent(values: list[float]) -> tuple[float, float]:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        raise JobError("Cannot calculate axis range from an empty series")
    return min(finite), max(finite)


def axis_range(
    supplied_from: Any,
    supplied_to: Any,
    values: list[float],
    reverse: bool = False,
    padding_fraction: float = 0.0,
) -> tuple[float, float]:
    minimum, maximum = finite_extent(values)
    span = maximum - minimum
    if span == 0:
        span = max(abs(maximum), 1.0)
    minimum -= span * padding_fraction
    maximum += span * padding_fraction
    begin = float(supplied_from) if supplied_from is not None else (maximum if reverse else minimum)
    end = float(supplied_to) if supplied_to is not None else (minimum if reverse else maximum)
    return begin, end


def clean_for_json(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: clean_for_json(item) for key, item in value.items() if not key.startswith("_columns")}
    if isinstance(value, list):
        return [clean_for_json(item) for item in value]
    return value


def select_pages(op: Any, kind: str) -> list[Any]:
    return list(op.pages(kind))


def prepare_project(op: Any, job: dict[str, Any], staged_project: Path) -> tuple[Any, Any, Any]:
    template = job["_template_opju"]
    if template is not None:
        shutil.copy2(template, staged_project)
        op.open(str(staged_project), readonly=False, asksave=False)
    else:
        op.new()

    books = select_pages(op, "w")
    if books:
        sheet = books[0][0]
    else:
        sheet = op.new_sheet("w", job["worksheet"].get("long_name", "Data"))
    descriptors = job["worksheet"]["columns"]
    sheet.clear()
    sheet.cols = len(descriptors)
    for index, descriptor in enumerate(descriptors):
        field = descriptor["field"]
        sheet.from_list(
            index,
            job["_columns"][field],
            lname=descriptor.get("long_name", field),
            units=descriptor.get("units", ""),
            comments=descriptor.get("comments", ""),
            axis=descriptor.get("axis", ""),
        )

    graphs = select_pages(op, "g")
    if graphs:
        graph_page = graphs[0]
    else:
        style = load_json(job["_style_file"])
        graph_page = op.new_graph(
            job["graph"].get("long_name", "Graph"),
            template=style.get("graph_template", "origin"),
        )
    layer = graph_page[0]
    return sheet, graph_page, layer


def configure_graph(op: Any, job: dict[str, Any], sheet: Any, graph_page: Any, layer: Any) -> dict[str, Any]:
    graph_job = job["graph"]
    series = graph_job["series"]
    plots = list(layer.plot_list())
    while len(plots) > len(series):
        plots[-1].remove()
        plots = list(layer.plot_list())

    template_mode = job["_template_opju"] is not None
    style = {} if template_mode else load_json(job["_style_file"])
    x_column = graph_job["x_column"]
    for index, entry in enumerate(series):
        if index < len(plots):
            plot = plots[index]
            plot.change_data(sheet, x=x_column, y=entry["y_column"])
        else:
            plot = layer.add_plot(sheet, coly=entry["y_column"], colx=x_column, type="l")
            plots.append(plot)

        role_style = style.get("series", {}).get(entry.get("role", "other"), {})
        color = entry.get("color", role_style.get("color"))
        line_width = entry.get("line_width", role_style.get("line_width"))
        if color is not None:
            plot.color = color
        if line_width is not None:
            plot.set_cmd(f"-w {float(line_width)}")

    x_label = graph_job.get("x_label", style.get("x_label", "X"))
    y_label = graph_job.get("y_label", style.get("y_label", "Y"))
    layer.axis("x").title = x_label
    layer.axis("y").title = y_label

    reverse_x = bool(graph_job.get("reverse_x", style.get("reverse_x", False)))
    x_values = job["_columns"][job["_fields"][x_column]]
    x_begin, x_end = axis_range(
        graph_job.get("x_from"), graph_job.get("x_to"), x_values, reverse=reverse_x
    )
    y_values: list[float] = []
    for entry in series:
        y_values.extend(job["_columns"][job["_fields"][entry["y_column"]]])
    y_padding = float(style.get("y_padding_fraction", 0.0))
    y_begin, y_end = axis_range(
        graph_job.get("y_from"), graph_job.get("y_to"), y_values, padding_fraction=y_padding
    )
    layer.set_xlim(x_begin, x_end)
    layer.set_ylim(y_begin, y_end)

    legend = bool(graph_job.get("legend", style.get("legend", True)))
    if not legend:
        try:
            layer.remove_label("legend")
        except Exception:
            pass
    if not bool(style.get("show_y_tick_labels", True)):
        try:
            layer.lt_exec("layer.y.showLabels=0")
        except Exception:
            pass

    return {
        "worksheet_rows": int(sheet.rows),
        "worksheet_columns": int(sheet.cols),
        "plot_count": len(layer.plot_list()),
        "x_range": [x_begin, x_end],
        "y_range": [y_begin, y_end],
        "template_mode": template_mode,
    }


def assert_no_running_origin() -> None:
    processes = running_origin_processes()
    if processes:
        raise JobError(
            "Origin is already running. Save and close every interactive Origin window before execution. "
            f"Detected: {processes}"
        )


def stop_owned_process(process: subprocess.Popen[Any]) -> None:
    """Stop only the Origin process started by this controller."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def execute_job_com(job: dict[str, Any], show_origin: bool) -> dict[str, Any]:
    assert_no_running_origin()
    output = job["_output_opju"]
    qa_png = job["_qa_png"]
    template = job["_template_opju"]
    template_hash_before = sha256(template) if template is not None else None
    output.parent.mkdir(parents=True, exist_ok=True)
    if qa_png is not None:
        qa_png.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="originpro_cli_") as temporary:
        stage = Path(temporary)
        staged_project = stage / "output.opju"
        staged_png = stage / "qa.png"
        import originpro as op

        started = False
        try:
            progress("launching_origin")
            op.set_show(show_origin)
            started = True
            progress("origin_launched")
            sheet, graph_page, layer = prepare_project(op, job, staged_project)
            progress("project_prepared")
            manifest = configure_graph(op, job, sheet, graph_page, layer)
            progress("graph_configured")
            op.save(str(staged_project))
            progress("project_saved")
            graph_page.save_fig(str(staged_png), type="png", replace=True, width=1600)
            progress("qa_png_exported")
        finally:
            if started:
                progress("closing_owned_origin")
                op.exit()
                progress("owned_origin_closed")

        if not staged_project.is_file() or staged_project.stat().st_size == 0:
            raise JobError("Origin did not create a non-empty staged project")
        if not staged_png.is_file() or staged_png.stat().st_size == 0:
            raise JobError("Origin did not create a non-empty QA PNG")
        shutil.copy2(staged_project, output)
        if qa_png is not None:
            shutil.copy2(staged_png, qa_png)

    template_hash_after = sha256(template) if template is not None else None
    if template_hash_before != template_hash_after:
        raise JobError("Reference template hash changed during execution")
    manifest.update(
        {
            "backend": "originpro-com-python",
            "output_opju": str(output),
            "output_sha256": sha256(output),
            "qa_png": str(qa_png) if qa_png is not None else None,
            "template_sha256_before": template_hash_before,
            "template_sha256_after": template_hash_after,
        }
    )
    return manifest


def verify_output_com(job: dict[str, Any], show_origin: bool) -> dict[str, Any]:
    assert_no_running_origin()
    output = job["_output_opju"]
    import originpro as op

    started = False
    try:
        progress("launching_origin_for_verification")
        op.set_show(show_origin)
        started = True
        progress("opening_output_readonly")
        op.open(str(output), readonly=True, asksave=False)
        books = select_pages(op, "w")
        graphs = select_pages(op, "g")
        if not books or not graphs:
            raise JobError("Output does not contain both a workbook and graph page")
        sheet = books[0][0]
        layer = graphs[0][0]
        report = {
            "backend": "originpro-com-python",
            "output_opju": str(output),
            "output_sha256": sha256(output),
            "worksheet_rows": int(sheet.rows),
            "worksheet_columns": int(sheet.cols),
            "graph_pages": len(graphs),
            "plot_count": len(layer.plot_list()),
        }
        if report["worksheet_rows"] < job["_row_count"]:
            raise JobError("Saved worksheet has fewer rows than the source CSV")
        if report["worksheet_columns"] < len(job["_fields"]):
            raise JobError("Saved worksheet has fewer columns than requested")
        if report["plot_count"] != len(job["graph"]["series"]):
            raise JobError("Saved plot count does not match the confirmed job")
        return report
    finally:
        if started:
            progress("closing_owned_origin")
            op.exit()
            progress("owned_origin_closed")


def embedded_build(job_path: Path) -> dict[str, Any]:
    """Build inside Origin's embedded Python; never call op.exit() here."""
    job = validate_job(job_path, require_output=False)
    import originpro as op

    output = job["_output_opju"]
    qa_png = job["_qa_png"]
    sheet, graph_page, layer = prepare_project(op, job, output)
    manifest = configure_graph(op, job, sheet, graph_page, layer)
    op.save(str(output))
    if qa_png is not None:
        graph_page.save_fig(str(qa_png), type="png", replace=True, width=1600)
    manifest.update(
        {
            "output_opju": str(output),
            "qa_png": str(qa_png) if qa_png is not None else None,
        }
    )
    return manifest


def embedded_verify(job_path: Path) -> dict[str, Any]:
    """Verify inside Origin's embedded Python; never call op.exit() here."""
    job = validate_job(job_path, require_output=True)
    import originpro as op

    op.open(str(job["_output_opju"]), readonly=True, asksave=False)
    books = select_pages(op, "w")
    graphs = select_pages(op, "g")
    if not books or not graphs:
        raise JobError("Output does not contain both a workbook and graph page")
    sheet = books[0][0]
    layer = graphs[0][0]
    report = {
        "output_opju": str(job["_output_opju"]),
        "worksheet_rows": int(sheet.rows),
        "worksheet_columns": int(sheet.cols),
        "graph_pages": len(graphs),
        "plot_count": len(layer.plot_list()),
    }
    if report["worksheet_rows"] < job["_row_count"]:
        raise JobError("Saved worksheet has fewer rows than the source CSV")
    if report["worksheet_columns"] < len(job["_fields"]):
        raise JobError("Saved worksheet has fewer columns than requested")
    if report["plot_count"] != len(job["graph"]["series"]):
        raise JobError("Saved plot count does not match the confirmed job")
    return report


def write_runtime_job(job: dict[str, Any], stage: Path, mode: str) -> Path:
    staged_csv = stage / "data.csv"
    staged_output = stage / "output.opju"
    staged_png = stage / "qa.png"
    staged_style = stage / "style.json"
    shutil.copy2(job["_data_csv"], staged_csv)
    template = job["_template_opju"]
    staged_template = None
    if template is not None:
        staged_template = stage / "template.opju"
        shutil.copy2(template, staged_template)
    if job["_style_file"] is not None:
        shutil.copy2(job["_style_file"], staged_style)
    if mode == "verify":
        shutil.copy2(job["_output_opju"], staged_output)

    runtime = {
        key: value
        for key, value in job.items()
        if not key.startswith("_")
    }
    runtime.update(
        {
            "data_csv": str(staged_csv),
            "output_opju": str(staged_output),
            "template_opju": str(staged_template) if staged_template is not None else None,
            "qa_png": str(staged_png),
            "overwrite": mode == "build",
        }
    )
    runtime["graph"] = dict(job["graph"])
    if job["_style_file"] is not None:
        runtime["graph"]["style_file"] = str(staged_style)
    runtime_path = stage / "job.json"
    runtime_path.write_text(json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8")
    return runtime_path


def run_origin_cli_worker(
    job: dict[str, Any],
    mode: str,
    origin_exe: str | None,
    timeout_seconds: int,
    startup_timeout_seconds: int,
    show_origin: bool,
) -> dict[str, Any]:
    assert_no_running_origin()
    executable = find_origin_executable(origin_exe)
    worker = Path(__file__).with_name("originpro_embedded_worker.py").resolve()
    if not worker.is_file():
        raise JobError(f"Embedded worker is missing: {worker}")

    template = job["_template_opju"]
    template_hash_before = sha256(template) if template is not None else None
    output = job["_output_opju"]
    qa_png = job["_qa_png"]
    if mode == "build":
        output.parent.mkdir(parents=True, exist_ok=True)
        if qa_png is not None:
            qa_png.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="origin_cli_") as temporary:
        stage = Path(temporary)
        runtime_job = write_runtime_job(job, stage, mode)
        result_path = stage / "result.json"
        log_path = stage / "origin_script.log"
        environment = os.environ.copy()
        environment["ORIGINPRO_JOB_RUNTIME"] = str(runtime_job)
        environment["ORIGINPRO_RESULT_RUNTIME"] = str(result_path)
        environment["ORIGINPRO_WORKER_MODE"] = mode
        labtalk = f'run -pyf "{worker}";exit;'
        command = [str(executable)]
        if not show_origin:
            command.append("-HS")
        command.extend(["-SLOG", str(log_path), "-RS", labtalk])
        progress("launching_origin_cli")
        process = subprocess.Popen(
            command,
            cwd=str(stage),
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        started_at = time.monotonic()
        overall_deadline = started_at + timeout_seconds
        startup_deadline = started_at + min(startup_timeout_seconds, timeout_seconds)
        worker_activity_seen = False
        while process.poll() is None:
            if result_path.exists() or (log_path.exists() and log_path.stat().st_size > 0):
                worker_activity_seen = True
            now = time.monotonic()
            if not worker_activity_seen and now >= startup_deadline:
                stop_owned_process(process)
                log_text = (
                    log_path.read_text(encoding="utf-8", errors="replace")
                    if log_path.exists()
                    else ""
                )
                raise BackendUnavailable(
                    "Origin CLI did not start the embedded Python worker within "
                    f"{startup_timeout_seconds} seconds; the owned process was stopped. "
                    f"Script log: {log_text[-1000:]}"
                )
            if now >= overall_deadline:
                stop_owned_process(process)
                log_text = (
                    log_path.read_text(encoding="utf-8", errors="replace")
                    if log_path.exists()
                    else ""
                )
                raise JobError(
                    f"Origin CLI exceeded {timeout_seconds} seconds after worker activity; "
                    f"the owned process was stopped. Script log: {log_text[-1000:]}"
                )
            time.sleep(0.2)

        deadline = time.monotonic() + 5
        while not result_path.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        if not result_path.is_file():
            log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            error_type = JobError if log_text else BackendUnavailable
            raise error_type(f"Origin CLI produced no worker result. Script log: {log_text[-1000:]}")
        result = load_json(result_path)
        if not result.get("ok"):
            raise JobError(str(result.get("error", "Origin embedded worker failed")))

        staged_output = stage / "output.opju"
        staged_png = stage / "qa.png"
        if mode == "build":
            if not staged_output.is_file() or staged_output.stat().st_size == 0:
                raise JobError("Origin CLI did not create a non-empty staged project")
            if qa_png is not None and (not staged_png.is_file() or staged_png.stat().st_size == 0):
                raise JobError("Origin CLI did not create a non-empty QA PNG")
            shutil.copy2(staged_output, output)
            if qa_png is not None:
                shutil.copy2(staged_png, qa_png)

    template_hash_after = sha256(template) if template is not None else None
    if template_hash_before != template_hash_after:
        raise JobError("Reference template hash changed during execution")
    report = dict(result.get("result", {}))
    report.update(
        {
            "backend": "origin-cli-embedded-python",
            "output_opju": str(output),
            "output_sha256": sha256(output),
            "qa_png": str(qa_png) if qa_png is not None else None,
            "template_sha256_before": template_hash_before,
            "template_sha256_after": template_hash_after,
        }
    )
    return report


def run_selected_backend(
    job: dict[str, Any],
    mode: str,
    backend: str,
    origin_exe: str | None,
    timeout_seconds: int,
    startup_timeout_seconds: int,
    show_origin: bool,
) -> dict[str, Any]:
    def run_cli() -> dict[str, Any]:
        return run_origin_cli_worker(
            job,
            mode,
            origin_exe,
            timeout_seconds,
            startup_timeout_seconds,
            show_origin,
        )

    def run_com() -> dict[str, Any]:
        if mode == "build":
            return execute_job_com(job, show_origin)
        return verify_output_com(job, show_origin)

    if backend == "cli":
        return run_cli()
    if backend == "com":
        return run_com()

    try:
        result = run_cli()
        result["backend_requested"] = "auto"
        result["fallback_used"] = False
        return result
    except BackendUnavailable as exc:
        progress("origin_cli_unavailable")
        if running_origin_processes():
            raise JobError(
                "Automatic COM fallback refused because an Origin process remains after the "
                "owned CLI process was stopped"
            ) from exc
        progress("falling_back_to_originpro_com")
        result = run_com()
        result.update(
            {
                "backend_requested": "auto",
                "fallback_used": True,
                "fallback_from": "cli",
                "fallback_reason": str(exc),
            }
        )
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, help="UTF-8 job JSON")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true", help="Validate inputs without launching Origin")
    mode.add_argument("--execute", action="store_true", help="Build the OPJU and QA PNG")
    mode.add_argument("--verify-only", action="store_true", help="Open and verify the existing output OPJU")
    parser.add_argument("--show-origin", action="store_true", help="Show the independent Origin instance")
    parser.add_argument(
        "--backend",
        choices=("auto", "cli", "com"),
        default="auto",
        help="Automation backend; auto tries CLI once, then falls back to COM only if the CLI worker never starts",
    )
    parser.add_argument("--origin-exe", help="Exact Origin executable for the cli or auto backend")
    parser.add_argument("--timeout", type=int, default=180, help="Origin CLI timeout in seconds")
    parser.add_argument(
        "--cli-startup-timeout",
        type=int,
        default=60,
        help="Seconds to wait for CLI worker activity before auto fallback (default: 60)",
    )
    args = parser.parse_args()

    try:
        job_path = Path(args.job).expanduser().resolve(strict=True)
        if args.timeout <= 0 or args.cli_startup_timeout <= 0:
            raise JobError("--timeout and --cli-startup-timeout must be positive")
        job = validate_job(job_path, require_output=args.verify_only)
        if args.validate_only:
            result = {
                "valid": True,
                "data_csv": str(job["_data_csv"]),
                "output_opju": str(job["_output_opju"]),
                "template_opju": str(job["_template_opju"]) if job["_template_opju"] else None,
                "row_count": job["_row_count"],
                "column_count": len(job["_fields"]),
                "series_count": len(job["graph"]["series"]),
            }
        else:
            result = run_selected_backend(
                job,
                "build" if args.execute else "verify",
                args.backend,
                args.origin_exe,
                args.timeout,
                args.cli_startup_timeout,
                args.show_origin,
            )
        print(json.dumps(clean_for_json(result), ensure_ascii=False, indent=2))
        return 0
    except (JobError, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
