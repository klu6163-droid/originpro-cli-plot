from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from origin_text import origin_rich_text


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Wavenumber (cm^-1)", r"Wavenumber (cm\+(-1))"),
        ("Area (m^2)", r"Area (m\+(2))"),
        ("R^2", r"R\+(2)"),
        ("Current density (A cm^{-2})", r"Current density (A cm\+(-2))"),
        ("x^(n+1)", r"x\+(n+1)"),
        ("Wavenumber (cm⁻¹)", r"Wavenumber (cm\+(-1))"),
        ("R² and 10⁻³", r"R\+(2) and 10\+(-3)"),
        (r"Already cm\+(-1)", r"Already cm\+(-1)"),
        (r"Legend anchor \^(l)", r"Legend anchor \^(l)"),
        ("No exponent here", "No exponent here"),
    ],
)
def test_origin_rich_text(source: str, expected: str) -> None:
    assert origin_rich_text(source) == expected
