#!/usr/bin/env python3
"""Read-only preflight checks for external OriginPro automation on Windows."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def com_registered(progid: str) -> bool:
    if os.name != "nt":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{progid}\CLSID"):
            return True
    except OSError:
        return False


def candidate_origin_executables(explicit: str | None) -> list[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))

    for env_name in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        root = os.environ.get(env_name)
        if not root:
            continue
        originlab = Path(root) / "OriginLab"
        if not originlab.exists():
            continue
        candidates.extend(originlab.glob("Origin*/Origin64.exe"))
        candidates.extend(originlab.glob("Origin*/Origin.exe"))

    known = Path(r"D:\Program Files\OriginLab\Origin2025\Origin64.exe")
    candidates.append(known)

    unique: dict[str, Path] = {}
    for candidate in candidates:
        unique[str(candidate.resolve(strict=False)).lower()] = candidate
    return sorted(unique.values(), key=lambda item: str(item), reverse=True)


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
    return [line.strip() for line in completed.stdout.splitlines() if "Origin64.exe" in line]


def stop_owned_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def probe_origin_cli(executable: Path, timeout_seconds: int) -> tuple[bool, str | None]:
    processes = running_origin_processes()
    if processes:
        return False, f"Origin is already running; CLI probe was not started: {processes}"

    with tempfile.TemporaryDirectory(prefix="origin_cli_probe_") as temporary:
        stage = Path(temporary)
        marker = stage / "probe_ok.txt"
        script = stage / "probe.py"
        log = stage / "origin_script.log"
        script.write_text(
            "import os\n"
            "from pathlib import Path\n"
            "import originpro\n"
            "Path(os.environ['ORIGINPRO_PROBE_RESULT']).write_text('ok', encoding='utf-8')\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["ORIGINPRO_PROBE_RESULT"] = str(marker)
        labtalk = f'run -pyf "{script}";exit;'
        command = [str(executable), "-HS", "-SLOG", str(log), "-RS", labtalk]
        process = subprocess.Popen(
            command,
            cwd=str(stage),
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            stop_owned_process(process)
            log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
            return False, (
                f"CLI probe exceeded {timeout_seconds} seconds; the owned process was stopped. "
                f"Script log: {log_text[-1000:]}"
            )
        if marker.is_file() and marker.read_text(encoding="utf-8", errors="replace").strip() == "ok":
            return True, None
        log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        return False, f"CLI probe produced no success marker. Script log: {log_text[-1000:]}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check whether this Python can automate a local OriginPro installation."
    )
    parser.add_argument("--origin-exe", help="Optional exact Origin executable path")
    parser.add_argument(
        "--probe-cli",
        action="store_true",
        help="Launch one temporary no-project CLI probe; Origin must be closed",
    )
    parser.add_argument(
        "--probe-timeout",
        type=int,
        default=45,
        help="CLI probe timeout in seconds (default: 45)",
    )
    args = parser.parse_args()
    if args.probe_timeout <= 0:
        parser.error("--probe-timeout must be positive")

    executables = [path for path in candidate_origin_executables(args.origin_exe) if path.is_file()]
    identity = subprocess.run(
        ["whoami"], capture_output=True, text=True, errors="replace", check=False
    ).stdout.strip()
    profile_user = os.environ.get("USERNAME", "")
    identity_user = identity.rsplit("\\", 1)[-1] if identity else ""
    identity_matches_profile = bool(
        identity_user and profile_user and identity_user.casefold() == profile_user.casefold()
    )
    report = {
        "platform": platform.platform(),
        "python": sys.executable,
        "windows": os.name == "nt",
        "origin_executables": [str(path.resolve()) for path in executables],
        "packages": {
            "originpro": package_version("originpro"),
            "OriginExt": package_version("OriginExt"),
        },
        "com": {
            "Origin.Application": com_registered("Origin.Application"),
            "Origin.ApplicationSI": com_registered("Origin.ApplicationSI"),
        },
        "execution_identity": identity,
        "profile_user": profile_user,
        "identity_matches_profile": identity_matches_profile,
    }
    report["ready"] = bool(
        report["windows"]
        and executables
        and report["packages"]["originpro"]
        and report["packages"]["OriginExt"]
        and report["com"]["Origin.Application"]
    )
    report["com_backend_ready"] = bool(report["ready"] and identity_matches_profile)
    report["cli_backend_candidate"] = bool(
        report["windows"] and executables and identity_matches_profile
    )
    report["cli_backend_ready"] = None
    report["cli_probe_error"] = None
    if args.probe_cli:
        if not identity_matches_profile:
            report["cli_backend_ready"] = False
            report["cli_probe_error"] = "CLI probe refused across the Windows user-session boundary"
        elif not executables:
            report["cli_backend_ready"] = False
            report["cli_probe_error"] = "No Origin executable is available for the CLI probe"
        else:
            cli_ready, cli_error = probe_origin_cli(executables[0].resolve(), args.probe_timeout)
            report["cli_backend_ready"] = cli_ready
            report["cli_probe_error"] = cli_error
    report["automation_session_ready"] = bool(report["ready"] and identity_matches_profile)
    report["manual_runner_recommended"] = bool(report["ready"] and not identity_matches_profile)
    if report["automation_session_ready"]:
        report["recommended_backend"] = "auto"
    elif report["manual_runner_recommended"]:
        report["recommended_backend"] = "manual-runner-auto"
    else:
        report["recommended_backend"] = "unavailable"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
