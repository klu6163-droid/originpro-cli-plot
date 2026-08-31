#!/usr/bin/env python3
"""Create a one-click CMD runner for executing an Origin job in the desktop user session."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def cmd_quote(value: Path | str) -> str:
    text = str(value)
    return '"' + text.replace('"', '""') + '"'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--job",
        action="append",
        required=True,
        help="Confirmed UTF-8 Origin job JSON; repeat for multiple jobs",
    )
    parser.add_argument("--output", required=True, help="Destination .cmd path")
    parser.add_argument("--python", default=sys.executable, help="Python executable for the controller")
    parser.add_argument("--origin-exe", help="Optional exact Origin executable")
    parser.add_argument(
        "--backend",
        choices=("auto", "cli", "com"),
        default="auto",
        help="Automation backend written to the runner (default: auto)",
    )
    parser.add_argument("--timeout", type=int, default=180, help="Overall CLI timeout in seconds")
    parser.add_argument(
        "--cli-startup-timeout",
        type=int,
        default=60,
        help="CLI worker startup timeout before auto fallback (default: 60)",
    )
    args = parser.parse_args()

    if args.timeout <= 0 or args.cli_startup_timeout <= 0:
        parser.error("--timeout and --cli-startup-timeout must be positive")
    jobs = [Path(value).expanduser().resolve(strict=True) for value in args.job]
    output = Path(args.output).expanduser().resolve(strict=False)
    if output.suffix.lower() != ".cmd":
        parser.error("--output must end with .cmd")
    output.parent.mkdir(parents=True, exist_ok=True)
    controller = Path(__file__).with_name("originpro_build.py").resolve(strict=True)
    python_exe = Path(args.python).expanduser().resolve(strict=True)
    origin_option = (
        f" --origin-exe {cmd_quote(Path(args.origin_exe).expanduser().resolve(strict=True))}"
        if args.origin_exe
        else ""
    )
    common_options = (
        f"--backend {args.backend} --show-origin --timeout {args.timeout} "
        f"--cli-startup-timeout {args.cli_startup_timeout}{origin_option}"
    )

    lines = [
        "@echo off",
        "setlocal",
        "chcp 65001 >nul",
        'set "RUN_LOG=%~dp0origin_run.log"',
        f'>"%RUN_LOG%" echo OriginPro job batch started with backend {args.backend}',
    ]
    for index, job in enumerate(jobs, start=1):
        label = f"Job {index}/{len(jobs)}: {job.name}"
        lines.extend(
            [
                f'>>"%RUN_LOG%" echo.',
                f'>>"%RUN_LOG%" echo ==== {label} build ====',
                (
                    f"{cmd_quote(python_exe)} {cmd_quote(controller)} --job {cmd_quote(job)} "
                    f"--execute {common_options} >>\"%RUN_LOG%\" 2>&1"
                ),
                "if errorlevel 1 goto :failed",
                f'>>"%RUN_LOG%" echo ==== {label} verify ====',
                (
                    f"{cmd_quote(python_exe)} {cmd_quote(controller)} --job {cmd_quote(job)} "
                    f"--verify-only {common_options} >>\"%RUN_LOG%\" 2>&1"
                ),
                "if errorlevel 1 goto :failed",
            ]
        )
    lines.extend(
        [
        "echo.",
        f"echo {len(jobs)} Origin project(s) created and verified.",
        'type "%RUN_LOG%"',
        "pause",
        "exit /b 0",
        ":failed",
        "echo.",
        "echo Origin job failed. Review the log below:",
        'type "%RUN_LOG%"',
        "pause",
        "exit /b 1",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
