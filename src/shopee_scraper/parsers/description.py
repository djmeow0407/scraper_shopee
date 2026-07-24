from __future__ import annotations

import re

from ..models import Description, Weight

# Nhãn trong bảng chi tiết: nhãn nằm riêng một dòng, giá trị ở dòng kế tiếp.
SPEC_KEYS = [
    "Danh Mục",
    "Thương hiệu",
    "Trọng lượng",
    "Xuất xứ",
    "Hạn sử dụng",
    "Gửi từ",
    "Kho",
    "Loại thực phẩm",
    "Thể tích",
    "Kích cỡ",
    "Chất liệu",
    "Số lượng",
    "Phong cách",
    "Mẫu mã",
    "Thành phần",
    "Hướng dẫn sử dụng",
    "Hạn bảo hành",
    "Loại bảo hành",
]

SUMMARY_MAX_CHARS = 200

_HASHTAG = re.compile(r"#\w+", re.UNICODE)
_MANUFACTURER = re.compile(
    r"^(?:công ty|cty|nhà sản xuất|sản xuất bởi|nsx|nhà phân phối)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
_WEIGHT = re.compile(r"(\d+(?:[.,]\d+)?)\s*([a-zA-ZđĐ]+)")

_SECTION_SPECS = "CHI TIẾT SẢN PHẨM"
_SECTION_DESC = "MÔ TẢ SẢN PHẨM"


def parse_weight(text: str | None) -> Weight:
    match = _WEIGHT.search(text or "")
    if not match:
        return Weight()

    number = float(match.group(1).replace(",", "."))
    unit = match.group(2).lower()
    if unit == "kg":
        return Weight(value=int(number * 1000), unit="g")
    return Weight(value=int(number), unit=unit)


def _split_sections(raw_text: str) -> tuple[list[str], list[str]]:
    specs: list[str] = []
    desc: list[str] = []
    bucket = desc

    for line in raw_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        upper = line.upper()
        if _SECTION_SPECS in upper:
            bucket = specs
        elif _SECTION_DESC in upper:
            bucket = desc
        else:
            bucket.append(line)

    return specs, desc


def _parse_specs(lines: list[str]) -> dict[str, str]:
    specs: dict[str, str] = {}
    current: str | None = None

    for item in lines:
        if item in SPEC_KEYS:
            current = item
            specs.setdefault(current, "")
        elif current is not None:
            existing = specs[current]
            # Giá trị nhiều dòng (điển hình là Danh Mục) nối bằng " > ".
            specs[current] = f"{existing} > {item}" if existing else item

    return specs


def _build_summary(desc_lines: list[str]) -> str:
    if not desc_lines:
        return ""

    summary = desc_lines[0]
    if len(summary) < 20 and len(desc_lines) > 1:
        summary = f"{desc_lines[0]}. {desc_lines[1]}"

    if len(summary) > SUMMARY_MAX_CHARS:
        summary = summary[:SUMMARY_MAX_CHARS].rstrip() + "..."
    return summary


def parse_description(raw_text: str | None) -> Description:
    raw_text = raw_text or ""
    if not raw_text.strip():
        return Description(raw_text=raw_text)

    spec_lines, desc_lines = _split_sections(raw_text)
    full_desc = "\n".join(desc_lines)
    manufacturer = _MANUFACTURER.search(full_desc)

    return Description(
        summary=_build_summary(desc_lines),
        manufacturer=manufacturer.group(0).strip() if manufacturer else "",
        hashtags=_HASHTAG.findall(full_desc),
        specs=_parse_specs(spec_lines),
        raw_text=raw_text,
    )


def category_path(specs: dict[str, str]) -> list[str]:
    return [part.strip() for part in specs.get("Danh Mục", "").split(">") if part.strip()]


def shelf_life_months(specs: dict[str, str]) -> int:
    match = re.search(r"\d+", specs.get("Hạn sử dụng", ""))
    return int(match.group(0)) if match else 0
