"""Selector Shopee gom một chỗ, dạng CSS. Mỗi field là danh sách ứng viên, thử
lần lượt; class ổn định đặt trước, class bị hash đặt sau. nodriver không chạy
XPath ổn định trên Brave nên toàn bộ dùng CSS, các mốc theo text tách riêng."""

from __future__ import annotations

Selector = str

SEARCH_RESULT_LIST: list[Selector] = [
    "ul.shopee-search-item-result__items",
]

SEARCH_RESULT_ITEM: list[Selector] = [
    "li.shopee-search-item-result__item",
    "div[data-sqe='item']",
]

SHOP_PRODUCT_LINK: list[Selector] = [
    "a[data-sqe='link']",
    ".shop-search-result-view__item a",
]

SHOP_HEADER: list[Selector] = [
    ".shopee-shop-header",
    "div[class*='shop-page-header']",
]

LISTING_LINK: list[Selector] = ["a.contents", "a"]
LISTING_NAME: list[Selector] = ["div[class*='line-clamp-2']"]
LISTING_PRICE: list[Selector] = [
    "div.truncate.flex.items-baseline",
    "div[class*='truncate'][class*='items-baseline']",
    "div[class*='truncate']",
]
LISTING_RATING: list[Selector] = ["div.text-shopee-black87.flex-none"]
LISTING_LOCATION: list[Selector] = ["div.text-shopee-black54.truncate"]
LISTING_IMAGE: list[Selector] = ["img[class*='object-contain']", "img"]

PRODUCT_NAME: list[Selector] = ["h1", "div[class*='product-brief-name']", "span[aria-label]"]
PRODUCT_PRICE: list[Selector] = [
    "section[aria-live='polite'] div[class*='pqTWkA']",
    "div[class*='pqTWkA']",
]
PRODUCT_IMAGE: list[Selector] = ["picture img", "div[class*='airUxs'] img"]

DESCRIPTION_CONTAINER: list[Selector] = ["div[class*='product-detail']"]

REVIEW_LIST: list[Selector] = [
    "div.shopee-product-comment-list",
    "div.product-ratings__list",
    "div.product-ratings",
]
REVIEW_ITEM: list[Selector] = [
    "[data-cmtid]",
    "div.shopee-product-rating",
]
REVIEW_AUTHOR: list[Selector] = [".shopee-product-rating__author-name", "a[href*='/shop/']"]
REVIEW_SOLID_STAR: list[Selector] = ["svg.icon-rating-solid--active", "svg.icon-rating-solid"]
REVIEW_NEXT_PAGE: list[Selector] = [
    "button.shopee-icon-button--right",
    ".shopee-svg-icon.icon-arrow-right",
]
RATING_FILTER: list[Selector] = ["div.product-rating-overview__filter"]

CATEGORY_ROW: list[Selector] = ["tr.shopee-table__row"]
CATEGORY_NEXT_PAGE: list[Selector] = ["button.shopee-pager__button-next"]

# Mốc tìm theo text (dùng tab.find), bền hơn class khi Shopee đổi giao diện.
DESCRIPTION_ANCHOR_TEXT = ["MÔ TẢ SẢN PHẨM", "CHI TIẾT SẢN PHẨM"]
REVIEW_ANCHOR_TEXT = ["ĐÁNH GIÁ SẢN PHẨM"]
NO_REVIEW_TEXT = "chưa có đánh giá"

CHALLENGE_URL_MARKERS = [
    "captcha",
    "/buyer/login",
    "/user/login",
    "/account/login",
    "/verify",
    "security",
]
