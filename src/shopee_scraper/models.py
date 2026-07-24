from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

from . import __version__


class Price(BaseModel):
    value: int = 0
    currency: str = "VND"
    raw: str = ""


class Weight(BaseModel):
    value: int = 0
    unit: str = ""


class CategoryInfo(BaseModel):
    code: str = ""
    path: list[str] = Field(default_factory=list)
    example: str = ""


class SellerResponse(BaseModel):
    responded: bool = False
    content: str = ""


class Review(BaseModel):
    username: str = ""
    rating: int = 0
    review_time: str = ""
    variation: str = ""
    attributes: dict[str, str] = Field(default_factory=dict)
    content: str = ""
    seller_response: SellerResponse = Field(default_factory=SellerResponse)
    helpful_votes: int = 0
    star_bucket: int | None = None


class RatingBreakdown(BaseModel):
    total: int = 0
    by_star: dict[int, int] = Field(default_factory=dict)
    with_comment: int = 0
    with_media: int = 0


class ProductInfo(BaseModel):
    id: str = "0_0"
    url: str = ""
    name: str = "Unknown"
    price: Price = Field(default_factory=Price)
    image: str = ""
    stock_status: str = "Unknown"
    category: list[str] = Field(default_factory=list)
    category_info: CategoryInfo | None = None
    brand: str = "No Brand"
    weight: Weight = Field(default_factory=Weight)
    origin: str = "Unknown"
    shelf_life_months: int = 0
    ship_from: str = "Unknown"
    rating: str = ""
    location: str = ""


class Description(BaseModel):
    summary: str = ""
    manufacturer: str = ""
    hashtags: list[str] = Field(default_factory=list)
    specs: dict[str, str] = Field(default_factory=dict)
    raw_text: str = ""


class ShopInfo(BaseModel):
    name: str = "Unknown"
    url: str = ""
    platform: str = "Shopee"


class ScrapeMeta(BaseModel):
    scraped_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    source: str = "Shopee"
    language: str = "vi"
    scraper_version: str = __version__
    warnings: list[str] = Field(default_factory=list)


class ProductRecord(BaseModel):
    product: ProductInfo
    description: Description = Field(default_factory=Description)
    rating_breakdown: RatingBreakdown = Field(default_factory=RatingBreakdown)
    reviews: list[Review] = Field(default_factory=list)
    shop: ShopInfo = Field(default_factory=ShopInfo)
    meta: ScrapeMeta = Field(default_factory=ScrapeMeta)

    @property
    def url(self) -> str:
        return self.product.url

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ProductListing(BaseModel):
    """Sản phẩm ở trang danh sách, trước khi vào trang chi tiết."""

    url: str
    name: str = "Unknown"
    price: str = "0"
    image: str = ""
    rating: str = ""
    location: str = ""
