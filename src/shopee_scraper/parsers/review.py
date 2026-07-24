from __future__ import annotations

import re
import unicodedata

from ..models import Review, SellerResponse
from .price import parse_star_count

# Nhãn thuộc tính -> khoá tiếng Anh, đặt tên bám theo khía cạnh của pipeline ABSA.
ATTRIBUTE_KEY_MAP = {
    "hương vị": "flavor",
    "chất lượng sản phẩm": "quality",
    "bao bì/mẫu mã": "packaging",
    "bao bì": "packaging",
    "đúng với mô tả": "as_described",
    "tính năng nổi bật": "features",
    "màu sắc": "color",
    "kích cỡ": "size",
    "chất liệu": "material",
    "độ bền": "durability",
    "thời gian sử dụng": "usage_time",
}

VARIATION_KEYS = {"phân loại hàng", "variation", "phân loại"}

SELLER_RESPONSE_MARKER = re.compile(r"phản hồi của người bán", re.IGNORECASE)

_TIMESTAMP = re.compile(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})")
_ATTR_LINE = re.compile(r"^([^:\n]{2,40}):\s*(.*)$")
_TRAILING_NOISE = re.compile(r"^(hữu ích\??|báo cáo|xem thêm|thu gọn|\d+)$", re.IGNORECASE)
_FILTER_LABEL = re.compile(r"^(.*?)\s*\(([^)]*)\)\s*$", re.DOTALL)


def _normalize_key(label: str) -> str:
    return re.sub(r"\s+", " ", label.replace(":", "").strip().lower())


def _slugify(label: str) -> str:
    decomposed = unicodedata.normalize("NFD", label)
    ascii_only = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    ascii_only = ascii_only.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower() or "unknown"


def parse_rating_filter(text: str | None) -> tuple[str, int] | None:
    """"5 Sao (1,2k)" -> ("5", 1200). Khoá khác: all / commented / media."""
    match = _FILTER_LABEL.match((text or "").strip())
    if not match:
        return None

    label = re.sub(r"\s+", " ", match.group(1)).strip().lower()
    count = parse_star_count(match.group(2))

    star = re.match(r"^(\d)\s*sao", label)
    if star:
        return star.group(1), count
    if "tất cả" in label:
        return "all", count
    if "bình luận" in label:
        return "commented", count
    if "hình ảnh" in label or "video" in label:
        return "media", count
    return _slugify(label), count


def _extract_seller_response(text: str) -> tuple[str, SellerResponse]:
    match = SELLER_RESPONSE_MARKER.search(text)
    if not match:
        return text, SellerResponse()

    body = text[: match.start()]
    lines = [ln.strip() for ln in text[match.end() :].split("\n") if ln.strip()]
    while lines and _TRAILING_NOISE.match(lines[-1]):
        lines.pop()

    return body, SellerResponse(responded=True, content="\n".join(lines))


def parse_review_block(
    text: str,
    *,
    rating: int = 0,
    username: str = "",
    star_bucket: int | None = None,
) -> Review:
    """Bóc `.text` của một khối đánh giá. rating/username lấy từ tầng Selenium,
    bỏ trống thì suy ra từ chính text."""
    # Lọc theo sao thì mọi review trong đó đúng bằng mức sao đang lọc, dùng làm
    # dự phòng khi không đếm được icon sao.
    review = Review(
        rating=rating or (star_bucket or 0), username=username, star_bucket=star_bucket
    )
    text = (text or "").strip()
    if not text:
        return review

    body, review.seller_response = _extract_seller_response(text)
    lines = [ln.strip() for ln in body.split("\n") if ln.strip()]

    if not review.username and lines:
        review.username = lines[0]
        lines = lines[1:]

    if lines and lines[-1].isdigit():
        review.helpful_votes = int(lines.pop())

    content_lines: list[str] = []
    for line in lines:
        # Dòng thời gian hay dính phân loại hàng: "2025-02-08 09:51 | Phân loại: X"
        stamp = _TIMESTAMP.search(line)
        if stamp:
            review.review_time = f"{stamp.group(1)}T{stamp.group(2)}:00"
            line = (line[: stamp.start()] + line[stamp.end() :]).strip(" |·-")
            if not line:
                continue

        for segment in (s.strip() for s in line.split("|")):
            if not segment or _TRAILING_NOISE.match(segment):
                continue

            attr = _ATTR_LINE.match(segment)
            if attr:
                key = _normalize_key(attr.group(1))
                value = attr.group(2).strip()
                if key in VARIATION_KEYS:
                    review.variation = value
                    continue
                if key in ATTRIBUTE_KEY_MAP:
                    review.attributes[ATTRIBUTE_KEY_MAP[key]] = value
                    continue
                # Nhãn lạ thì để nguyên trong content. Đoán bừa theo kiểu "có dấu
                # hai chấm là thuộc tính" sẽ nuốt mất câu như "Đánh giá: ...".

            content_lines.append(segment)

    review.content = "\n".join(content_lines).strip()
    return review
