import pytest

from shopee_scraper.parsers import (
    parse_description,
    parse_price,
    parse_rating_filter,
    parse_review_block,
    parse_star_count,
)
from shopee_scraper.parsers.description import category_path, shelf_life_months


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("58.000 ₫", 58_000),
        ("₫58.000", 58_000),
        ("₫58.000 - ₫72.000", 58_000),
        ("1.250.000₫", 1_250_000),
        ("", 0),
        ("Liên hệ", 0),
        (None, 0),
    ],
)
def test_parse_price(text, expected):
    assert parse_price(text).value == expected


def test_parse_price_keeps_raw():
    price = parse_price("  58.000 ₫ ")
    assert price.raw == "58.000 ₫"
    assert price.currency == "VND"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("345", 345),
        ("1,2k", 1_200),
        ("1.2k", 1_200),
        ("12k", 12_000),
        ("1.200", 1_200),
        ("2m", 2_000_000),
        ("", 0),
    ],
)
def test_parse_star_count(text, expected):
    assert parse_star_count(text) == expected


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("5 Sao (1,2k)", ("5", 1_200)),
        ("1 Sao (12)", ("1", 12)),
        ("Tất Cả (3,4k)", ("all", 3_400)),
        ("Có Bình Luận (300)", ("commented", 300)),
        ("Có Hình Ảnh / Video (45)", ("media", 45)),
        ("Không có ngoặc", None),
    ],
)
def test_parse_rating_filter(label, expected):
    assert parse_rating_filter(label) == expected


DESCRIPTION_TEXT = """CHI TIẾT SẢN PHẨM
Danh Mục
Shopee
Bách Hóa Online
Đồ ăn vặt
Kẹo
Thương hiệu
Bảo Minh
Trọng lượng
250 g
Xuất xứ
Việt Nam
Hạn sử dụng
6 tháng
Gửi từ
Hà Nội
Kho
CÒN HÀNG
MÔ TẢ SẢN PHẨM
Kẹo vừng Bảo Minh được làm từ vừng, đường kính, mạch nha. Ít ngọt, bùi, xốp.
Công ty CP Bánh mứt kẹo Bảo Minh
#banhkeobaominh #keovung
"""


def test_parse_description_specs():
    desc = parse_description(DESCRIPTION_TEXT)
    assert desc.specs["Thương hiệu"] == "Bảo Minh"
    assert desc.specs["Kho"] == "CÒN HÀNG"
    assert desc.specs["Trọng lượng"] == "250 g"


def test_parse_description_category_and_shelf_life():
    specs = parse_description(DESCRIPTION_TEXT).specs
    assert category_path(specs) == ["Shopee", "Bách Hóa Online", "Đồ ăn vặt", "Kẹo"]
    assert shelf_life_months(specs) == 6


def test_parse_description_summary_and_hashtags():
    desc = parse_description(DESCRIPTION_TEXT)
    assert desc.summary.startswith("Kẹo vừng Bảo Minh")
    assert desc.hashtags == ["#banhkeobaominh", "#keovung"]
    assert desc.manufacturer == "Công ty CP Bánh mứt kẹo Bảo Minh"


def test_parse_description_empty():
    desc = parse_description("")
    assert desc.specs == {}
    assert desc.summary == ""


@pytest.mark.parametrize(
    ("text", "value", "unit"),
    [("250 g", 250, "g"), ("1,5 kg", 1500, "g"), ("2kg", 2000, "g"), ("", 0, "")],
)
def test_parse_weight(text, value, unit):
    from shopee_scraper.parsers import parse_weight

    weight = parse_weight(text)
    assert (weight.value, weight.unit) == (value, unit)


REVIEW_TEXT = """dung_gin
2025-02-08 09:51 | Phân loại hàng: 250gr
Hương vị: ngon
Chất lượng sản phẩm: tốt
Giao hàng nhanh, bánh rất ngon, chuẩn Hà Nội
Phản Hồi Của Người Bán
Shop cảm ơn bạn đã ủng hộ ạ
3
"""


def test_parse_review_block_fields():
    review = parse_review_block(REVIEW_TEXT, rating=5)
    assert review.username == "dung_gin"
    assert review.rating == 5
    assert review.review_time == "2025-02-08T09:51:00"
    assert review.variation == "250gr"
    assert review.attributes == {"flavor": "ngon", "quality": "tốt"}
    assert review.content == "Giao hàng nhanh, bánh rất ngon, chuẩn Hà Nội"


def test_parse_review_block_seller_response():
    review = parse_review_block(REVIEW_TEXT)
    assert review.seller_response.responded is True
    assert review.seller_response.content == "Shop cảm ơn bạn đã ủng hộ ạ"


def test_parse_review_block_without_seller_response():
    review = parse_review_block("user1\n2025-01-01 10:00\nSản phẩm ổn")
    assert review.seller_response.responded is False
    assert review.content == "Sản phẩm ổn"


def test_parse_review_keeps_colon_inside_sentence():
    review = parse_review_block("user1\nĐánh giá: sản phẩm này rất đáng tiền nhé mọi người")
    assert "đáng tiền" in review.content
    assert review.attributes == {}


def test_parse_review_block_records_star_bucket():
    review = parse_review_block("user1\nTạm được", star_bucket=3)
    assert review.star_bucket == 3
    assert review.rating == 3


def test_parse_review_block_empty():
    review = parse_review_block("")
    assert review.username == ""
    assert review.content == ""
