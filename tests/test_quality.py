from shopee_scraper import quality
from shopee_scraper.models import (
    Price,
    ProductInfo,
    ProductRecord,
    RatingBreakdown,
    Review,
)


def _record(**product_kwargs) -> ProductRecord:
    product_kwargs.setdefault("name", "Bánh quy")
    product_kwargs.setdefault("price", Price(value=15000))
    product_kwargs.setdefault("category", ["Thực phẩm"])
    return ProductRecord(product=ProductInfo(**product_kwargs))


def test_clean_record_has_no_warnings():
    assert quality.validate(_record()) == []


def test_missing_name():
    assert "name-missing" in quality.validate(_record(name="Unknown"))


def test_price_zero_with_reviews_is_suspicious():
    record = _record(price=Price(value=0))
    record.reviews = [Review(content="ngon")]
    assert "price-zero-suspicious" in quality.validate(record)


def test_price_zero_without_signal_is_missing():
    warnings = quality.validate(_record(price=Price(value=0)))
    assert "price-missing" in warnings
    assert "price-zero-suspicious" not in warnings


def test_reviews_empty_despite_ratings():
    record = _record()
    record.rating_breakdown = RatingBreakdown(total=120, with_comment=40)
    assert "reviews-empty-despite-ratings" in quality.validate(record)


def test_category_missing():
    assert "category-missing" in quality.validate(_record(category=[]))
