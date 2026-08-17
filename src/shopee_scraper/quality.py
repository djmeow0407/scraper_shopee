"""Kiểm tra chéo bản ghi đã dựng: bắt bất thường mà tầng bóc từng field không thấy,
ví dụ giá 0 trong khi có hàng nghìn đánh giá thì gần như chắc selector giá hỏng."""

from __future__ import annotations

from .models import ProductRecord


def validate(record: ProductRecord) -> list[str]:
    warnings: list[str] = []
    product = record.product
    breakdown = record.rating_breakdown

    if product.name in ("", "Unknown"):
        warnings.append("name-missing")

    if product.price.value == 0:
        if breakdown.total or record.reviews:
            warnings.append("price-zero-suspicious")
        else:
            warnings.append("price-missing")

    # Có lượt bình luận nhưng bóc ra 0 review -> nghi selector đánh giá hỏng.
    expected_reviews = breakdown.with_comment or breakdown.total
    if expected_reviews and not record.reviews:
        warnings.append("reviews-empty-despite-ratings")

    if not product.category:
        warnings.append("category-missing")

    return warnings
