"""Normalize scientific exponent notation for Origin graph text objects."""
from __future__ import annotations

import re


_CARET_EXPONENT = re.compile(
    r"(?<!\\)\^(?:\{([^{}\r\n]+)\}|\(([^()\r\n]+)\)|([+-]?(?:\d+(?:\.\d+)?|[A-Za-z])))"
)
_UNICODE_SUPERSCRIPT = re.compile(r"[⁺⁻⁰¹²³⁴⁵⁶⁷⁸⁹⁽⁾ⁿ]+")
_UNICODE_TO_ASCII = str.maketrans(
    "⁺⁻⁰¹²³⁴⁵⁶⁷⁸⁹⁽⁾ⁿ",
    "+-0123456789()n",
)


def origin_rich_text(text: str) -> str:
    """Render caret or Unicode exponents with Origin's native rich-text syntax.

    Existing Origin escapes such as ``\\+(-1)`` and ``\\^(l)`` are preserved.
    Examples: ``cm^-1`` -> ``cm\\+(-1)`` and ``R²`` -> ``R\\+(2)``.
    """

    value = str(text)

    def replace_caret(match: re.Match[str]) -> str:
        exponent = next(group for group in match.groups() if group is not None)
        return rf"\+({exponent})"

    value = _CARET_EXPONENT.sub(replace_caret, value)

    def replace_unicode(match: re.Match[str]) -> str:
        # Do not nest an already formatted Origin superscript.
        if value[max(0, match.start() - 3) : match.start()] == r"\+(" and value[match.end() : match.end() + 1] == ")":
            return match.group(0)
        return rf"\+({match.group(0).translate(_UNICODE_TO_ASCII)})"

    return _UNICODE_SUPERSCRIPT.sub(replace_unicode, value)
