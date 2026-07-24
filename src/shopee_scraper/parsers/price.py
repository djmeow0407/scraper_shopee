from __future__ import annotations

import re

from ..models import Price

_DIGITS = re.compile(r"\d[\d.,]*")


def parse_price(text: str | None) -> Price:
    """"58.000 ₫" -> 58000. Khoảng giá thì lấy cận dưới."""
    raw = (text or "").strip()
    match = _DIGITS.search(raw)
    if not match:
        return Price(value=0, raw=raw)

    digits = re.sub(r"[^\d]", "", match.group(0))
    return Price(value=int(digits) if digits else 0, raw=raw)


def parse_star_count(text: str | None) -> int:
    """"1,2k" -> 1200, "1.200" -> 1200."""
    s = (text or "").strip().lower().replace(" ", "")
    if not s:
        return 0

    multiplier = 1
    if s.endswith("k"):
        multiplier, s = 1_000, s[:-1]
    elif s.endswith("m"):
        multiplier, s = 1_000_000, s[:-1]

    if multiplier > 1:
        # Dạng rút gọn thì dấu phẩy lẫn dấu chấm đều là dấu thập phân,
        # khác với dạng đầy đủ nơi dấu chấm phân cách hàng nghìn.
        try:
            return int(float(s.replace(",", ".")) * multiplier)
        except ValueError:
            return 0

    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0
