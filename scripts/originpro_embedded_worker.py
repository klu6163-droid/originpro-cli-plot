#!/usr/bin/env python3
"""Origin-embedded worker launched by Origin64.exe; do not run directly."""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path


def write_result(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    job_value = os.environ.get("ORIGINPRO_JOB_RUNTIME")
    result_value = os.environ.get("ORIGINPRO_RESULT_RUNTIME")
    mode = os.environ.get("ORIGINPRO_WORKER_MODE", "build")
    if not job_value or not result_value:
        raise RuntimeError("Origin CLI worker environment is incomplete")

    job_path = Path(job_value)
    result_path = Path(result_value)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import originpro_build as build

    try:
        if mode == "build":
            result = build.embedded_build(job_path)
        elif mode == "verify":
            result = build.embedded_verify(job_path)
        else:
            raise RuntimeError(f"Unsupported worker mode: {mode}")
        write_result(result_path, {"ok": True, "result": result})
    except Exception as exc:
        write_result(
            result_path,
            {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )


if __name__ == "__main__":
    main()
