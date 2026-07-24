"""Selector của Shopee gom một chỗ. Mỗi hằng là danh sách ứng viên, thử lần lượt;
cái ổn định (text tiếng Việt, data-*) đặt trước, class bị hash đặt sau."""

from __future__ import annotations

from selenium.webdriver.common.by import By

Selector = tuple[str, str]

SEARCH_RESULT_LIST: list[Selector] = [
    (By.CSS_SELECTOR, "ul.shopee-search-item-result__items"),
    (By.XPATH, '//*[@id="main"]/div/div[2]/div/div/div/div/div/div[2]/section/ul'),
]

SEARCH_RESULT_ITEM: list[Selector] = [
    (By.CSS_SELECTOR, "li.shopee-search-item-result__item"),
    (By.CSS_SELECTOR, "div[data-sqe='item']"),
    (By.XPATH, ".//li"),
]

SHOP_HEADER: list[Selector] = [
    (By.CLASS_NAME, "shopee-shop-header"),
    (By.CSS_SELECTOR, "div.shop-page-header"),
]

SHOP_PRODUCT_LINK: list[Selector] = [
    (By.CSS_SELECTOR, "a[data-sqe='link']"),
    (By.CSS_SELECTOR, ".shop-search-result-view__item a"),
]

LISTING_LINK: list[Selector] = [
    (By.CSS_SELECTOR, "a.contents"),
    (By.TAG_NAME, "a"),
]

LISTING_NAME: list[Selector] = [
    (By.CSS_SELECTOR, "div.line-clamp-2"),
    (By.XPATH, './/div[contains(@class, "line-clamp-2")]'),
]

LISTING_PRICE: list[Selector] = [
    (By.XPATH, './/div[@class="truncate flex items-baseline"]'),
    (By.XPATH, './/div[contains(@class, "truncate") and contains(@class, "items-baseline")]'),
    (By.XPATH, './/div[contains(@class, "truncate")]'),
]

LISTING_RATING: list[Selector] = [
    (By.XPATH, './/div[@class="text-shopee-black87 text-xs/sp14 flex-none"]'),
    (By.CSS_SELECTOR, "div.text-shopee-black87.flex-none"),
]

LISTING_LOCATION: list[Selector] = [
    (
        By.XPATH,
        './/div[@class="flex-shrink min-w-0 truncate text-shopee-black54 font-extralight text-sp10"]',
    ),
    (By.CSS_SELECTOR, "div.text-shopee-black54.truncate"),
]

LISTING_IMAGE: list[Selector] = [
    (By.CSS_SELECTOR, "img.object-contain"),
    (By.TAG_NAME, "img"),
]

PRODUCT_NAME: list[Selector] = [
    (By.CSS_SELECTOR, "h1"),
    (By.CSS_SELECTOR, "._44qnta span"),
    (By.XPATH, '//div[contains(@class, "product-brief-name")]'),
]

PRODUCT_PRICE: list[Selector] = [
    (By.CSS_SELECTOR, "section[aria-live='polite'] div.pqTWkA"),
    (By.CSS_SELECTOR, ".pqTWkA"),
    (By.XPATH, '//div[contains(text(), "₫")][1]'),
]

PRODUCT_IMAGE: list[Selector] = [
    (By.CSS_SELECTOR, "picture img"),
    (By.CSS_SELECTOR, "div.airUxs img"),
]

DESCRIPTION_ANCHOR: list[Selector] = [
    (By.XPATH, '//div[contains(text(), "MÔ TẢ SẢN PHẨM")]'),
    (By.XPATH, '//div[contains(text(), "CHI TIẾT SẢN PHẨM")]'),
]

DESCRIPTION_CONTAINER: list[Selector] = [
    (By.XPATH, '//div[div[contains(text(), "MÔ TẢ SẢN PHẨM")]]'),
    (By.XPATH, '//div[contains(@class, "product-detail")]'),
]

REVIEW_ANCHOR: list[Selector] = [
    (By.XPATH, '//div[contains(text(), "ĐÁNH GIÁ SẢN PHẨM")]'),
]

REVIEW_LIST: list[Selector] = [
    (By.CLASS_NAME, "shopee-product-comment-list"),
    (By.CLASS_NAME, "product-ratings__list"),
    (By.CSS_SELECTOR, "div.product-ratings"),
]

REVIEW_ITEM: list[Selector] = [
    (By.CSS_SELECTOR, ".shopee-product-rating"),
    (By.XPATH, './/div[contains(@class,"shopee-product-rating__main")]'),
    (By.XPATH, "./div"),
]

REVIEW_AUTHOR: list[Selector] = [
    (By.CLASS_NAME, "shopee-product-rating__author-name"),
    (By.CSS_SELECTOR, "a[href*='/shop/']"),
]

REVIEW_SOLID_STAR: list[Selector] = [
    (By.CSS_SELECTOR, "svg.icon-rating-solid--active"),
    (By.CSS_SELECTOR, "svg.icon-rating-solid"),
]

REVIEW_NEXT_PAGE: list[Selector] = [
    (By.CSS_SELECTOR, "button.shopee-icon-button--right"),
    (By.CSS_SELECTOR, ".shopee-svg-icon.icon-arrow-right"),
]

# Nút "5 Sao (1,2k)", "Có Bình Luận (300)", ...
RATING_FILTER: list[Selector] = [
    (By.CSS_SELECTOR, "div.product-rating-overview__filter"),
    (By.XPATH, '//div[contains(@class,"product-rating-overview__filter")]'),
]

CATEGORY_ROW: list[Selector] = [(By.CSS_SELECTOR, "tr.shopee-table__row")]
CATEGORY_NEXT_PAGE: list[Selector] = [(By.CSS_SELECTOR, "button.shopee-pager__button-next")]

CHALLENGE_URL_MARKERS = [
    "captcha",
    "/buyer/login",
    "/user/login",
    "/account/login",
    "/verify",
    "security",
]
